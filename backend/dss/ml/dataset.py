"""Panel de relaciones empresa-mercado para predecir el abandono ('exportación golondrina').

Unidad: relación (RUC, país) activa en la fecha de corte c (al menos un envío en los 12 meses
previos). Las variables usan solo información disponible hasta c. Etiqueta: 1 si la relación
no registra ningún envío en los MESES_ABANDONO meses posteriores a c.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from dss.config import MESES_ABANDONO

VENTANA = 12

VARIABLES = [
    "meses_activos_12", "envios_12", "log_fob_12", "tendencia_fob", "recencia",
    "antiguedad", "actividad_historica", "log_valor_unitario",
    "empresa_n_mercados_12", "empresa_log_fob_12", "cuota_mercado_en_empresa",
    "mercado_n_empresas_12", "mercado_log_fob_12", "mercado_log_imp_mundo",
]


def _indice_mes(p: pd.Period) -> int:
    return p.year * 12 + p.month - 1


def preparar(exportaciones: pd.DataFrame) -> pd.DataFrame:
    e = exportaciones[["ruc", "iso3", "tiempo_id", "fob_usd", "cantidad"]].copy()
    e["m"] = (e["tiempo_id"] // 100) * 12 + (e["tiempo_id"] % 100) - 1
    return e


def construir(e: pd.DataFrame, corte: pd.Period, importaciones_mundo: pd.DataFrame | None = None,
              etiquetar: bool = True) -> pd.DataFrame:
    """Variables (y etiqueta si hay seguimiento completo) de las relaciones activas en `corte`."""
    c = _indice_mes(corte)
    hist = e[e["m"] <= c]
    ventana = hist[hist["m"] > c - VENTANA]
    previa = hist[(hist["m"] > c - 2 * VENTANA) & (hist["m"] <= c - VENTANA)]
    if ventana.empty:
        return pd.DataFrame(columns=["ruc", "iso3", *VARIABLES])

    g = ventana.groupby(["ruc", "iso3"])
    df = pd.DataFrame({
        "meses_activos_12": g["m"].nunique(),
        "envios_12": g.size(),
        "fob_12": g["fob_usd"].sum(),
        "fob_ult6": ventana[ventana["m"] > c - 6].groupby(["ruc", "iso3"])["fob_usd"].sum(),
        "cantidad_12": g["cantidad"].sum(min_count=1),
        "ultimo": g["m"].max(),
    }).fillna({"fob_ult6": 0.0})
    gh = hist.groupby(["ruc", "iso3"])
    df["primero"] = gh["m"].min()
    df["meses_hist"] = gh["m"].nunique()
    df["fob_previo"] = previa.groupby(["ruc", "iso3"])["fob_usd"].sum()
    df = df.reset_index()

    df["log_fob_12"] = np.log10(df["fob_12"] + 1)
    df["tendencia_fob"] = (2 * df["fob_ult6"] - df["fob_12"]) / df["fob_12"].replace(0, np.nan)
    df["recencia"] = c - df["ultimo"]
    df["antiguedad"] = c - df["primero"]
    df["actividad_historica"] = df["meses_hist"] / (df["antiguedad"] + 1)
    df["log_valor_unitario"] = np.log10(df["fob_12"] / df["cantidad_12"].replace(0, np.nan))

    emp = ventana.groupby("ruc").agg(empresa_n_mercados_12=("iso3", "nunique"), empresa_fob_12=("fob_usd", "sum"))
    mer = ventana.groupby("iso3").agg(mercado_n_empresas_12=("ruc", "nunique"), mercado_fob_12=("fob_usd", "sum"))
    df = df.merge(emp, on="ruc").merge(mer, on="iso3")
    df["empresa_log_fob_12"] = np.log10(df["empresa_fob_12"] + 1)
    df["cuota_mercado_en_empresa"] = df["fob_12"] / df["empresa_fob_12"]
    df["mercado_log_fob_12"] = np.log10(df["mercado_fob_12"] + 1)

    # Demanda del importador del año anterior al corte (dato publicado a esa fecha)
    if importaciones_mundo is not None and len(importaciones_mundo):
        im = importaciones_mundo[importaciones_mundo["anio"] == corte.year - 1]
        df = df.merge(im[["declarante_iso3", "valor_usd"]].rename(columns={"declarante_iso3": "iso3"}),
                      on="iso3", how="left")
        df["mercado_log_imp_mundo"] = np.log10(df["valor_usd"] + 1)
    else:
        df["mercado_log_imp_mundo"] = np.nan

    df["corte"] = str(corte)
    if etiquetar:
        futuro = e[(e["m"] > c) & (e["m"] <= c + MESES_ABANDONO)]
        siguen = set(map(tuple, futuro[["ruc", "iso3"]].drop_duplicates().to_numpy()))
        df["abandono"] = [int((r, i) not in siguen) for r, i in zip(df["ruc"], df["iso3"])]
    return df[["corte", "ruc", "iso3", "fob_12", *VARIABLES] + (["abandono"] if etiquetar else [])]


def cortes_etiquetables(ultimo_mes: pd.Period, primero: pd.Period, paso: int = 6) -> list[pd.Period]:
    """Cortes con al menos VENTANA meses de historia y MESES_ABANDONO de seguimiento observado."""
    cortes, c = [], primero + (VENTANA - 1)
    while c + MESES_ABANDONO <= ultimo_mes:
        cortes.append(c)
        c += paso
    return cortes
