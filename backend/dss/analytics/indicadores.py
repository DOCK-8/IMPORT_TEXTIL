"""Indicadores crudos por relación producto (SA6) - país de destino (artículo III.F)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from dss.analytics import economico
from dss.analytics.trayectoria import periodo, resumen_continuidad
from dss.countries import region

KG_POR_UNIDAD_DEFECTO = 0.5
MIN_ENVIOS_PRECIO = 3
# Valor unitario del importador aceptado como precio si cae entre 0.5x y 3x el valor unitario FOB peruano
RANGO_PRECIO_COMPARABLE = (0.5, 3.0)


def _cagr(serie: pd.Series) -> float | None:
    """Tasa de crecimiento anual compuesta entre extremos con valor inicial positivo."""
    s = serie[serie > 0].sort_index()
    if len(s) < 2 or s.index[-1] == s.index[0]:
        return None
    return float((s.iloc[-1] / s.iloc[0]) ** (1 / (s.index[-1] - s.index[0])) - 1)


def anio_referencia(importaciones_mundo: pd.DataFrame) -> int | None:
    """Último año con cobertura de declarantes >= 70% del máximo observado (evita años parciales)."""
    if importaciones_mundo.empty:
        return None
    cobertura = importaciones_mundo.groupby("anio")["declarante_iso3"].nunique()
    return int(cobertura[cobertura >= 0.7 * cobertura.max()].index.max())


def calcular(sa6: str, exportaciones: pd.DataFrame, comercio: pd.DataFrame,
             acceso: pd.DataFrame, inicio: pd.Period, corte: pd.Period) -> pd.DataFrame:
    exp = exportaciones[exportaciones["sa6"] == sa6]
    com = comercio[comercio["sa6"] == sa6]
    imp = com[com["flujo"] == "M"]
    mundo = imp[(imp["socio_iso3"] == "WLD") & (imp["anio"] >= inicio.year)]
    proveedores = imp[imp["socio_iso3"] != "WLD"]
    anio_ref = anio_referencia(mundo)

    con_cantidad = exp[exp["cantidad"].notna() & exp["peso_neto_kg"].notna()]
    kg_unidad = (
        float((con_cantidad["peso_neto_kg"] / con_cantidad["cantidad"]).median())
        if len(con_cantidad) else KG_POR_UNIDAD_DEFECTO
    )
    con_unidades = exp[exp["cantidad"].notna()]
    precio_peru = float(con_unidades["fob_usd"].sum() / con_unidades["cantidad"].sum()) if len(con_unidades) else None
    fletes = economico.cargar_fletes()
    supuestos_base = economico.cargar_supuestos()["base"]

    mercados = sorted((set(mundo["declarante_iso3"]) | set(exp["iso3"])) - {"PER"})
    exp_meses = exp.assign(mes=exp["tiempo_id"].map(periodo))
    inicio_precio = corte - 23

    filas = []
    for iso3 in mercados:
        f: dict = {"sa6": sa6, "iso3": iso3, "region": region(iso3), "anio_ref": anio_ref}

        # 1. Demanda internacional
        anual = mundo[mundo["declarante_iso3"] == iso3].set_index("anio")["valor_usd"].sort_index()
        f["imp_anual"] = {int(k): float(v) for k, v in anual.items()}
        f["v_imp"] = float(anual.get(anio_ref)) if anio_ref in anual.index else None
        hasta_ref = anual[anual.index <= (anio_ref or 0)]
        f["cagr"] = _cagr(hasta_ref)
        f["yoy"] = (
            float(hasta_ref.iloc[-1] / hasta_ref.iloc[-2] - 1)
            if len(hasta_ref) >= 2 and hasta_ref.iloc[-2] > 0 else None
        )
        f["cv_imp"] = float(hasta_ref.std() / hasta_ref.mean()) if len(hasta_ref) >= 3 and hasta_ref.mean() > 0 else None

        # 4. Competencia (desglose por proveedor del año de referencia)
        prov = proveedores[(proveedores["declarante_iso3"] == iso3) & (proveedores["anio"] == anio_ref)]
        prov = prov[prov["valor_usd"] > 0]
        if len(prov):
            cuotas = prov.set_index("socio_iso3")["valor_usd"] / prov["valor_usd"].sum()
            f["n_proveedores"] = int(len(cuotas))
            f["hhi"] = float((cuotas ** 2).sum())
            f["principal_proveedor"] = str(cuotas.idxmax())
            f["principal_cuota"] = float(cuotas.max())
            f["top_proveedores"] = {k: round(float(v), 4) for k, v in cuotas.nlargest(5).items()}
            f["s_peru"] = float(cuotas.get("PER", 0.0))
            f["fuente_s_peru"] = "espejo_importador"
        else:
            f.update(n_proveedores=None, hhi=None, principal_proveedor=None,
                     principal_cuota=None, top_proveedores={}, s_peru=None, fuente_s_peru=None)

        # 5. Trayectoria exportadora (PROMPERÚ)
        e = exp_meses[exp_meses["iso3"] == iso3]
        f.update(resumen_continuidad(e["mes"].tolist(), inicio, corte))
        f["fob_peru_total"] = float(e["fob_usd"].sum())
        f["fob_peru_anual"] = {int(k): float(v) for k, v in e.groupby(e["mes"].map(lambda m: m.year))["fob_usd"].sum().items()}
        f["n_empresas"] = int(e["ruc"].nunique())
        f["tipo_mercado"] = "con_presencia" if len(e) else "potencial"
        if f["s_peru"] is None and f["v_imp"] and anio_ref:
            fob_ref = f["fob_peru_anual"].get(anio_ref, 0.0)
            f["s_peru"] = min(fob_ref / f["v_imp"], 1.0)
            f["fuente_s_peru"] = "fob_promperu"

        # 3. Acceso al mercado
        a = acceso[(acceso["iso3"] == iso3) & acceso["sa6"].isin([sa6, "*"])]
        a = a.sort_values("sa6", key=lambda s: s.eq("*")).head(1)  # la fila específica gana a '*'
        if len(a):
            r = a.iloc[0]
            f.update(tlc=1.0 if r["tlc_vigente"] else 0.0, acuerdo=r["acuerdo"],
                     arancel_nmf=r["arancel_nmf"], arancel_preferencial=r["arancel_preferencial"],
                     n_ntm=r["n_ntm"], requisitos=r["requisitos"], fuente_acceso=r["fuente_url"],
                     acceso_verificado=bool(r["verificado"]), elegible=bool(r["elegible"]))
        else:
            f.update(tlc=0.0, acuerdo=None, arancel_nmf=None, arancel_preferencial=None, n_ntm=None,
                     requisitos=None, fuente_acceso=None, acceso_verificado=False, elegible=True)
        nmf, pref = f["arancel_nmf"], f["arancel_preferencial"]
        f["margen_preferencial"] = (
            float(nmf) - float(pref) if pd.notna(nmf) and pd.notna(pref) else None
        )

        # 4bis. Resultado económico: precio = valor unitario FOB peruano reciente o del importador
        reciente = e[(e["mes"] >= inicio_precio) & e["cantidad"].notna()]
        f["precio_unitario"], f["fuente_precio"] = None, None
        if len(reciente) >= MIN_ENVIOS_PRECIO:
            f["precio_unitario"] = float(reciente["fob_usd"].sum() / reciente["cantidad"].sum())
            f["fuente_precio"] = "valor_unitario_fob_peru_24m"
        else:
            fila_ref = imp[(imp["declarante_iso3"] == iso3) & (imp["socio_iso3"] == "WLD")
                           & (imp["anio"] == anio_ref) & (imp["unidad"] == "u")]
            if len(fila_ref) and (fila_ref["cantidad"].fillna(0) > 0).all():
                vu = float(fila_ref["valor_usd"].sum() / fila_ref["cantidad"].sum())
                # Solo comparable si está en el rango de calidad del producto peruano
                if precio_peru and RANGO_PRECIO_COMPARABLE[0] * precio_peru <= vu <= RANGO_PRECIO_COMPARABLE[1] * precio_peru:
                    f["precio_unitario"], f["fuente_precio"] = vu, "valor_unitario_importador"
                else:
                    f["fuente_precio"] = "valor_unitario_importador_no_comparable"
        f["kg_por_unidad"] = kg_unidad
        f["flete_usd_kg"] = fletes.get(f["region"], fletes.get("Otras regiones"))
        if f["precio_unitario"]:
            m = economico.margen(f["precio_unitario"], kg_unidad, f["flete_usd_kg"], supuestos_base, "CIF")
            f["margen_pct"] = m["margen_pct"]
            f["margen_usd_unidad"] = m["margen_usd_unidad"]
        else:
            f["margen_pct"] = f["margen_usd_unidad"] = None
        filas.append(f)

    return pd.DataFrame(filas).replace({np.nan: None})
