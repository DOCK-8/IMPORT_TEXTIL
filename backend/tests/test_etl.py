from datetime import datetime

import pandas as pd
import pytest

from dss.catalog import homologar
from dss.countries import iso3_desde_nombre
from dss.etl.promperu import _corregir_peso, limpiar, recuperar_numero


@pytest.mark.parametrize("valor, anio_carga, esperado", [
    (datetime(2125, 4, 1), 2026, 2125.4),     # '2125.4' leído como año.mes
    (datetime(2086, 11, 1), 2026, 2086.11),   # dos dígitos decimales
    (datetime(2026, 4, 29), 2026, 29.4),      # '29.4' leído como día.mes del año de carga
    (datetime(2026, 12, 5), 2026, 5.12),
    ("66.88", 2026, 66.88),
    (1007, 2026, 1007.0),
])
def test_recuperar_numero(valor, anio_carga, esperado):
    numero, recuperado = recuperar_numero(valor, anio_carga)
    assert numero == pytest.approx(esperado)
    assert recuperado == isinstance(valor, datetime)


def test_corregir_peso_escala_miles():
    assert _corregir_peso(7274.0, 20) == (pytest.approx(7.274), True)
    assert _corregir_peso(5.2, 10) == (5.2, False)
    assert _corregir_peso(None, 10) == (None, False)


def test_homologacion_10_a_6_digitos():
    assert homologar("6110191090") == "611019"
    assert homologar("6110.19.00.10") == "611019"
    assert homologar("6505000090") == "650500"
    assert homologar("6109100031") is None  # t-shirt de algodón: fuera del alcance


def test_paises_con_tildes_y_variantes():
    assert iso3_desde_nombre("Japón") == "JPN"
    assert iso3_desde_nombre("República de Corea (Corea del Sur)") == "KOR"
    assert iso3_desde_nombre("  estados   unidos ") == "USA"


def _crudo(**cambios):
    base = {
        "fecha_embarque": "05/01/2021", "ruc": "20453995241", "razon_social": "X", "region_origen": "Arequipa",
        "codigo10": "6110191090", "descripcion_arancelaria": "d", "descripcion_comercial": "SWEATER ALPACA",
        "mercado_destino": "Alemania", "fob_usd": 500.0, "peso_neto_kg": 4.0, "peso_bruto_kg": 4.5,
        "cantidad": 8, "hoja": "PROMPERU_Exportaciones_2021",
    }
    base.update(cambios)
    return base


def test_limpiar_normaliza_recupera_y_deduplica():
    crudo = pd.DataFrame([
        _crudo(),
        _crudo(),  # duplicado exacto
        _crudo(fecha_embarque=datetime(2021, 7, 1), fob_usd=datetime(2026, 5, 26), peso_neto_kg=4000.0),
        _crudo(mercado_destino="Atlántida"),  # país no identificable -> excluido
    ])
    df, calidad = limpiar(crudo)
    metricas = {c["metrica"]: c["valor"] for c in calidad}
    assert len(df) == 2
    assert metricas["duplicados_eliminados"] == 1
    assert metricas["excluidos_campos_esenciales"] == 1
    fila = df[df["fob_recuperado"]].iloc[0]
    assert fila["fob_usd"] == pytest.approx(26.5)
    assert fila["peso_neto_kg"] == pytest.approx(4.0) and fila["peso_corregido"]
    assert set(df["tiempo_id"]) == {202101, 202107}
    assert set(df["sa6"]) == {"611019"}
