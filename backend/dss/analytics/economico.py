"""Resultado económico estimado por mercado bajo escenarios conservador / base / favorable.

Los costos provienen de data/reference/costos_escenarios.csv y fletes_region.csv, que son
supuestos SINTÉTICOS de demostración: se reportan siempre con esa etiqueta y deben
reemplazarse por la estructura de costos real de cada PyME.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from dss import config

ETIQUETA_DATOS = "sintetico_demostracion"


@dataclass
class SupuestosCosto:
    escenario: str
    precio_factor: float
    costo_produccion_usd_unidad: float
    logistica_local_usd_unidad: float
    documentarios_usd_envio: float
    unidades_por_envio: float
    seguro_pct: float
    flete_factor: float


def cargar_supuestos() -> dict[str, SupuestosCosto]:
    df = pd.read_csv(config.REFERENCE_DIR / "costos_escenarios.csv")
    return {r["escenario"]: SupuestosCosto(**r) for r in df.to_dict("records")}


def cargar_fletes() -> dict[str, float]:
    df = pd.read_csv(config.REFERENCE_DIR / "fletes_region.csv")
    return dict(zip(df["region"], df["flete_aereo_usd_kg"]))


def margen(precio_unitario: float, kg_por_unidad: float, flete_usd_kg: float,
           s: SupuestosCosto, incoterm: str = "CIF") -> dict:
    """Margen unitario. Con FOB el comprador paga flete y seguro; con CIF los asume el exportador
    (el precio observado es FOB, por lo que CIF es el supuesto conservador)."""
    precio = precio_unitario * s.precio_factor
    costos = {
        "produccion": s.costo_produccion_usd_unidad,
        "logistica_local": s.logistica_local_usd_unidad,
        "documentarios": s.documentarios_usd_envio / s.unidades_por_envio,
        "flete": 0.0,
        "seguro": 0.0,
    }
    if incoterm.upper() == "CIF":
        costos["flete"] = flete_usd_kg * s.flete_factor * kg_por_unidad
        costos["seguro"] = precio * s.seguro_pct / 100
    costo_total = sum(costos.values())
    return {
        "escenario": s.escenario,
        "incoterm": incoterm.upper(),
        "precio_usd_unidad": round(precio, 2),
        "costos_usd_unidad": {k: round(v, 2) for k, v in costos.items()},
        "costo_total_usd_unidad": round(costo_total, 2),
        "margen_usd_unidad": round(precio - costo_total, 2),
        "margen_pct": round(100 * (precio - costo_total) / precio, 2) if precio else None,
        "margen_envio_usd": round((precio - costo_total) * s.unidades_por_envio, 2),
        "supuestos": asdict(s),
        "datos": ETIQUETA_DATOS,
    }


def escenarios(precio_unitario: float | None, kg_por_unidad: float, flete_usd_kg: float,
               incoterm: str = "CIF") -> list[dict]:
    if not precio_unitario:
        return []
    return [margen(precio_unitario, kg_por_unidad, flete_usd_kg, s, incoterm)
            for s in cargar_supuestos().values()]
