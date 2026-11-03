import numpy as np
import pandas as pd
import pytest

from dss.analytics import economico, indice
from dss.analytics.trayectoria import resumen_continuidad
from dss.config import PESOS_SRS
from dss.ml.dataset import construir, cortes_etiquetables, preparar

INICIO, CORTE = pd.Period("2021-01", "M"), pd.Period("2025-12", "M")


def meses(*textos):
    return [pd.Period(t, "M") for t in textos]


def test_abandono_requiere_24_meses_observados():
    r = resumen_continuidad(meses("2021-03", "2023-11"), INICIO, CORTE)
    assert r["recencia_meses"] == 25 and r["estado"] == "abandono" and r["abandono"] == 1


def test_menos_de_24_meses_queda_en_observacion():
    r = resumen_continuidad(meses("2021-03", "2022-06", "2024-06"), INICIO, CORTE)
    assert r["recencia_meses"] == 18 and r["max_intervalo_meses"] == 23
    assert r["estado"] == "en_observacion" and r["abandono"] == 0


def test_reingreso_tras_intervalo_largo():
    r = resumen_continuidad(meses("2021-01", "2023-06", "2025-10"), INICIO, CORTE)
    assert r["estado"] == "reingreso" and r["max_intervalo_meses"] == 28 and r["episodios"] == 3


def test_sin_presencia():
    assert resumen_continuidad([], INICIO, CORTE)["estado"] == "sin_presencia"


def _ind():
    return pd.DataFrame([
        # mercado grande, con TLC y presencia continua
        dict(iso3="AAA", v_imp=1e8, cagr=0.10, s_peru=0.05, hhi=0.2, tlc=1.0, margen_preferencial=None, n_ntm=None,
             tipo_mercado="con_presencia", actividad_pct=90, recencia_meses=0, abandono=0, margen_pct=30, elegible=True),
        # mercado pequeño, concentrado, abandonado
        dict(iso3="BBB", v_imp=1e5, cagr=-0.05, s_peru=0.0, hhi=0.8, tlc=0.0, margen_preferencial=None, n_ntm=None,
             tipo_mercado="con_presencia", actividad_pct=5, recencia_meses=30, abandono=1, margen_pct=5, elegible=True),
        # potencial (sin exportaciones peruanas)
        dict(iso3="CCC", v_imp=1e7, cagr=0.02, s_peru=0.0, hhi=0.4, tlc=1.0, margen_preferencial=None, n_ntm=None,
             tipo_mercado="potencial", actividad_pct=None, recencia_meses=None, abandono=None, margen_pct=20, elegible=True),
        # sin demanda: información crítica ausente
        dict(iso3="DDD", v_imp=None, cagr=None, s_peru=None, hhi=None, tlc=0.0, margen_preferencial=None, n_ntm=None,
             tipo_mercado="con_presencia", actividad_pct=10, recencia_meses=5, abandono=0, margen_pct=None, elegible=True),
    ])


def test_indice_en_rango_y_ordena_correctamente():
    res = indice.puntuar(_ind()).set_index("iso3")
    assert res.loc["AAA", "score"] == pytest.approx(100.0)  # mejor en todas las dimensiones
    assert res.loc["BBB", "score"] < res.loc["CCC", "score"] < res.loc["AAA", "score"]
    assert res["score"].dropna().between(0, 100).all()


def test_mercado_potencial_renormaliza_pesos_sin_trayectoria():
    res = indice.puntuar(_ind()).set_index("iso3")
    z = res.loc["CCC", ["demanda", "acceso", "competencia", "economico"]]
    w = pd.Series(PESOS_SRS)[z.index]
    assert res.loc["CCC", "score"] == pytest.approx(100 * (z * w).sum() / w.sum(), abs=0.01)
    assert res.loc["CCC", "estado"] == "completa"


def test_sin_demanda_es_evaluacion_incompleta():
    res = indice.puntuar(_ind()).set_index("iso3")
    assert res.loc["DDD", "estado"] == "incompleta" and np.isnan(res.loc["DDD", "score"])


def test_no_elegible_no_recibe_puntaje():
    ind = _ind()
    ind.loc[0, "elegible"] = False
    res = indice.puntuar(ind).set_index("iso3")
    assert res.loc["AAA", "estado"] == "no_elegible" and np.isnan(res.loc["AAA", "score"])


def test_margen_cif_suma_flete_y_seguro():
    s = economico.SupuestosCosto("base", 1.0, 36, 1.2, 250, 150, 0.6, 1.0)
    fob = economico.margen(100, 0.5, 5.0, s, "FOB")
    cif = economico.margen(100, 0.5, 5.0, s, "CIF")
    assert fob["costo_total_usd_unidad"] == pytest.approx(36 + 1.2 + 250 / 150, abs=0.01)
    assert cif["costo_total_usd_unidad"] - fob["costo_total_usd_unidad"] == pytest.approx(2.5 + 0.6, abs=0.01)
    assert cif["datos"] == "sintetico_demostracion"


def _panel():
    filas = []
    for m in range(1, 13):  # empresa 1 exporta todo 2021 a USA y continúa en 2023
        filas.append(("1", "USA", 202100 + m, 100.0, 2))
    filas.append(("1", "USA", 202305, 100.0, 2))
    filas.append(("2", "DEU", 202106, 50.0, 1))  # empresa 2: un solo envío -> golondrina
    filas.append(("2", "DEU", 202601, 50.0, 1))  # posterior a la ventana: no debe contarse
    return pd.DataFrame(filas, columns=["ruc", "iso3", "tiempo_id", "fob_usd", "cantidad"])


def test_etiqueta_abandono_y_sin_fuga_temporal():
    e = preparar(_panel())
    df = construir(e, pd.Period("2021-12", "M")).set_index("ruc")
    assert df.loc["1", "abandono"] == 0  # vuelve a exportar dentro de 24 meses
    assert df.loc["2", "abandono"] == 1  # 2026-01 está fuera de la ventana 2022-01..2023-12
    assert df.loc["1", "meses_activos_12"] == 12
    assert df.loc["2", "recencia"] == 6
    # las variables no cambian si se agregan datos posteriores al corte
    futuro = pd.concat([_panel(), pd.DataFrame([("1", "USA", 202202, 1e6, 1)], columns=_panel().columns)])
    df2 = construir(preparar(futuro), pd.Period("2021-12", "M")).set_index("ruc")
    assert df2.loc["1", "log_fob_12"] == df.loc["1", "log_fob_12"]


def test_cortes_con_seguimiento_completo():
    cortes = cortes_etiquetables(CORTE, INICIO)
    assert [str(c) for c in cortes] == ["2021-12", "2022-06", "2022-12", "2023-06", "2023-12"]
