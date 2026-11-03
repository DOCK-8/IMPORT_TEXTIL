"""Trayectoria exportadora: actividad mensual, recencia, intervalos sin exportar y abandono."""

from __future__ import annotations

import pandas as pd

from dss.config import MESES_ABANDONO


def periodo(tiempo_id: int) -> pd.Period:
    return pd.Period(year=tiempo_id // 100, month=tiempo_id % 100, freq="M")


def meses_entre(a: pd.Period, b: pd.Period) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def resumen_continuidad(meses_activos: list[pd.Period], inicio: pd.Period, corte: pd.Period) -> dict:
    """Indicadores de continuidad de una relación (producto-país o empresa-país) hasta `corte`.

    El abandono solo se declara cuando el intervalo completo de MESES_ABANDONO meses sin
    operaciones es observable dentro de la ventana (cero comercial validado, no dato faltante).
    """
    activos = sorted({m for m in meses_activos if inicio <= m <= corte})
    total = meses_entre(inicio, corte) + 1
    if not activos:
        return {"meses_activos": 0, "actividad_pct": 0.0, "recencia_meses": None,
                "max_intervalo_meses": None, "episodios": 0, "estado": "sin_presencia",
                "abandono": None}

    intervalos = [meses_entre(a, b) - 1 for a, b in zip(activos, activos[1:])]
    recencia = meses_entre(activos[-1], corte)
    episodios = 1 + sum(1 for g in intervalos if g > 0)
    hubo_abandono = any(g >= MESES_ABANDONO for g in intervalos)

    if recencia >= MESES_ABANDONO:
        estado, abandono = "abandono", 1
    elif hubo_abandono:
        estado, abandono = "reingreso", 0
    elif recencia >= 12:
        estado, abandono = "en_observacion", 0  # aún no se completa la ventana de 24 meses
    else:
        estado, abandono = "continuo", 0

    return {
        "meses_activos": len(activos),
        "actividad_pct": 100 * len(activos) / total,
        "recencia_meses": recencia,
        "max_intervalo_meses": max(intervalos + [recencia]),
        "episodios": episodios,
        "estado": estado,
        "abandono": abandono,
    }


def serie_mensual(exportaciones: pd.DataFrame, inicio: pd.Period, corte: pd.Period) -> pd.DataFrame:
    """FOB, envíos y empresas por mes, con ceros explícitos en los meses sin operaciones."""
    meses = pd.period_range(inicio, corte, freq="M")
    if exportaciones.empty:
        return pd.DataFrame({"mes": meses.astype(str), "fob_usd": 0.0, "envios": 0, "empresas": 0})
    g = exportaciones.assign(mes=exportaciones["tiempo_id"].map(periodo)).groupby("mes").agg(
        fob_usd=("fob_usd", "sum"), envios=("fob_usd", "size"), empresas=("ruc", "nunique"))
    g = g.reindex(meses, fill_value=0)
    return g.reset_index(names="mes").assign(mes=lambda d: d["mes"].astype(str))
