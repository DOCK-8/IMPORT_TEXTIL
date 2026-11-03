"""Índice de Atractivo Comercial I(p,c) = 100 * Σ w_i z_i(p,c), con Σ w_i = 1 (SRS, sección 3).

- z_i: normalización min-max (0-1) entre todos los mercados del producto, orientada de modo
  que un valor mayor sea más favorable. Los indicadores continuos se acotan a los percentiles
  5-95 antes de normalizar para que los atípicos no dominen (RNF-04); el valor importado se
  normaliza en escala log10.
- Mercados potenciales (sin exportaciones peruanas): la trayectoria no aplica y los pesos se
  renormalizan entre las dimensiones restantes (artículo III.K).
- Sin demanda (información crítica) -> estado 'incompleta' sin puntaje.
- Requisito obligatorio no cumplible (elegible = False) -> estado 'no_elegible'.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from dss.config import ESCENARIOS_PESOS, PESOS_SRS

DIMENSIONES = list(PESOS_SRS)


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype(float)


def minmax(s: pd.Series) -> pd.Series:
    s = _num(s)
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or hi == lo:
        return s.where(s.isna(), 0.5)
    return (s - lo) / (hi - lo)


def percentil(s: pd.Series) -> pd.Series:
    """Normalización alternativa por rango percentil (para el análisis de sensibilidad)."""
    return _num(s).rank(pct=True)


def _winsor(s: pd.Series, q: float = 0.05) -> pd.Series:
    s = _num(s)
    return s.clip(s.quantile(q), s.quantile(1 - q))


def _media(*cols: pd.Series) -> pd.Series:
    return pd.concat(cols, axis=1).mean(axis=1, skipna=True)


def dimensiones(ind: pd.DataFrame, norm=minmax) -> pd.DataFrame:
    z = pd.DataFrame(index=ind.index)
    z["z_v_imp"] = norm(_winsor(np.log10(_num(ind["v_imp"]) + 1)))
    z["z_cagr"] = norm(_winsor(ind["cagr"]))
    z["z_s_peru"] = norm(_winsor(ind["s_peru"]))
    z["demanda"] = _media(z["z_v_imp"], z["z_cagr"], z["z_s_peru"]).where(_num(ind["v_imp"]).notna())

    z["z_hhi"] = 1 - norm(_winsor(ind["hhi"]))
    z["competencia"] = z["z_hhi"]

    z["z_tlc"] = _num(ind["tlc"])
    z["z_margen_pref"] = norm(_winsor(ind["margen_preferencial"]))
    z["z_ntm"] = 1 - norm(_winsor(ind["n_ntm"]))
    z["acceso"] = _media(z["z_tlc"], z["z_margen_pref"], z["z_ntm"])

    presencia = ind["tipo_mercado"] == "con_presencia"
    z["z_actividad"] = norm(ind["actividad_pct"].where(presencia))
    z["z_recencia"] = 1 - norm(ind["recencia_meses"].where(presencia))
    z["z_continuidad"] = 1 - _num(ind["abandono"]).where(presencia)
    z["trayectoria"] = _media(z["z_actividad"], z["z_recencia"], z["z_continuidad"]).where(presencia)

    z["economico"] = norm(_winsor(ind["margen_pct"]))
    return z


def puntuar(ind: pd.DataFrame, pesos: dict[str, float] = PESOS_SRS, norm=minmax) -> pd.DataFrame:
    z = dimensiones(ind, norm)
    w = pd.Series(pesos)
    disponibles = z[DIMENSIONES].notna()
    suma_pesos = disponibles.mul(w).sum(axis=1)
    score = 100 * z[DIMENSIONES].fillna(0).mul(w).sum(axis=1) / suma_pesos.replace(0, np.nan)

    presencia = ind["tipo_mercado"] == "con_presencia"
    esperadas = pd.DataFrame({d: True for d in DIMENSIONES}, index=ind.index)
    esperadas.loc[~presencia, "trayectoria"] = False
    faltantes = (esperadas & ~disponibles).sum(axis=1)

    estado = np.where(faltantes == 0, "completa", "parcial")
    estado = np.where(z["demanda"].isna(), "incompleta", estado)
    estado = np.where(~ind["elegible"].astype(bool), "no_elegible", estado)
    estado = pd.Series(estado, index=ind.index)

    out = pd.DataFrame({
        "iso3": ind["iso3"],
        "score": score.where(estado.isin(["completa", "parcial"])).round(2),
        "estado": estado,
        "dimensiones_faltantes": [
            [d for d in DIMENSIONES if esperadas.at[i, d] and not disponibles.at[i, d]] for i in ind.index
        ],
    })
    out["ranking"] = out["score"].rank(ascending=False, method="min")
    return pd.concat([out, z], axis=1)


def sensibilidad(ind: pd.DataFrame, top_n: int = 10) -> dict:
    """Estabilidad del ordenamiento ante cambios de ponderación y de normalización."""
    base = puntuar(ind).set_index("iso3")
    base = base[base["score"].notna()]
    top_base = set(base.nsmallest(top_n, "ranking").index)
    variantes = {f"pesos_{k}": puntuar(ind, p) for k, p in ESCENARIOS_PESOS.items() if k != "srs"}
    variantes["normalizacion_percentil"] = puntuar(ind, PESOS_SRS, percentil)

    resumen, rangos = {}, pd.DataFrame({"srs": base["ranking"]})
    for nombre, v in variantes.items():
        v = v.set_index("iso3").loc[base.index]
        rangos[nombre] = v["ranking"]
        delta = (v["ranking"] - base["ranking"]).abs()
        top_v = set(v.nsmallest(top_n, "ranking").index)
        resumen[nombre] = {
            "spearman": round(float(spearmanr(base["score"], v["score"]).statistic), 4),
            "cambio_medio_posiciones": round(float(delta.mean()), 2),
            "cambio_max_posiciones": int(delta.max()),
            f"permanencia_top{top_n}_pct": round(100 * len(top_base & top_v) / max(len(top_base), 1), 1),
        }
    estables = rangos.max(axis=1) <= top_n
    return {
        "n_mercados": int(len(base)),
        "top_n": top_n,
        "variantes": resumen,
        "mercados_siempre_en_top": sorted(base.index[estables].tolist(), key=lambda i: base.at[i, "ranking"]),
        "rango_posiciones": {
            iso: {"min": int(r.min()), "max": int(r.max())} for iso, r in rangos.iterrows()
        },
    }
