"""API REST del DSS (RNF-03). Documentación interactiva en /docs."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, text

from dss import catalog, config
from dss.analytics import economico, indice
from dss.analytics.trayectoria import serie_mensual
from dss.db import engine, sesion
from dss.models import (
    CalidadDatos, DimPais, DimProducto, DimRegion, EtlEjecucion, FactExportaciones,
    IndiceViabilidad, ModeloMetricas, RiesgoAbandono, Sensibilidad,
)

app = FastAPI(
    title="DSS Viabilidad Comercial Textil",
    version="1.0.0",
    description="Índice de Atractivo Comercial, trayectoria exportadora y riesgo de abandono "
                "para prendas de alpaca y lana (datos abiertos SUNAT/PROMPERÚ y UN Comtrade).",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("DSS_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"], allow_headers=["*"],
)

INICIADO = datetime.now()
LATENCIAS: dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
UMBRAL_LATENCIA_MS = 2500  # RNF-01


@app.middleware("http")
async def medir_latencia(request: Request, call_next):
    t0 = time.perf_counter()
    respuesta = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    ruta = request.scope.get("route")
    LATENCIAS[getattr(ruta, "path", request.url.path)].append(ms)
    respuesta.headers["X-Response-Time-ms"] = f"{ms:.1f}"
    return respuesta


def _paises() -> dict[str, dict]:
    with sesion() as s:
        filas = s.execute(select(DimPais.iso3, DimPais.nombre, DimRegion.nombre).join(DimRegion)).all()
    return {iso: {"nombre": n, "region": r} for iso, n, r in filas}


def _producto(sa6: str) -> DimProducto:
    with sesion() as s:
        p = s.get(DimProducto, sa6)
    if not p:
        raise HTTPException(404, f"Subpartida {sa6} no está en el catálogo")
    return p


def _fila_indice(r: IndiceViabilidad, paises: dict, riesgo: dict) -> dict:
    ind, dims = r.indicadores, r.dimensiones
    return {
        "iso3": r.iso3, **paises.get(r.iso3, {"nombre": r.iso3, "region": None}),
        "score": r.score, "ranking": r.ranking, "estado": r.estado, "tipo_mercado": r.tipo_mercado,
        "dimensiones": {d: dims.get(d) for d in indice.DIMENSIONES},
        "faltantes": dims.get("faltantes", []),
        "v_imp": ind.get("v_imp"), "cagr": ind.get("cagr"), "s_peru": ind.get("s_peru"),
        "hhi": ind.get("hhi"), "tlc": ind.get("tlc"), "acuerdo": ind.get("acuerdo"),
        "fob_peru_total": ind.get("fob_peru_total"), "n_empresas": ind.get("n_empresas"),
        "recencia_meses": ind.get("recencia_meses"), "estado_continuidad": ind.get("estado"),
        "margen_pct": ind.get("margen_pct"),
        "riesgo_abandono": riesgo.get(r.iso3),
    }


def _riesgos(sa6: str) -> dict:
    with sesion() as s:
        filas = s.scalars(select(RiesgoAbandono).where(RiesgoAbandono.sa6 == sa6)).all()
    return {r.iso3: {"probabilidad": round(r.probabilidad, 4), "clase": r.clase,
                     "n_relaciones": r.n_relaciones, "modelo": r.modelo} for r in filas}


@app.get("/api/v1/salud")
def salud():
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        bd = "ok"
    except Exception as e:  # noqa: BLE001
        bd = f"error: {e.__class__.__name__}"
    return {"estado": "ok" if bd == "ok" else "degradado", "base_datos": bd,
            "iniciado": INICIADO.isoformat(timespec="seconds")}


@app.get("/api/v1/productos")
def productos():
    with sesion() as s:
        conteos = dict(s.execute(select(FactExportaciones.sa6, func.count()).group_by(FactExportaciones.sa6)).all())
        con_indice = set(s.scalars(select(IndiceViabilidad.sa6).distinct()).all())
    return [
        {"codigo": p.codigo, "nombre": p.nombre, "subpartidas": [
            {"sa6": sp.sa6, "descripcion": sp.descripcion, "nacionales": list(sp.nacionales),
             "nota_agregacion": sp.nota_agregacion or None, "registros_exportacion": conteos.get(sp.sa6, 0),
             "tiene_indice": sp.sa6 in con_indice}
            for sp in catalog.SUBPARTIDAS if sp.prenda == p.codigo
        ]}
        for p in catalog.PRENDAS
    ]


@app.get("/api/v1/viabilidad")
def viabilidad(sa6: str = Query("611019", pattern=r"^\d{6}$"), escenario: str = "srs"):
    """Exporting Score por país de destino (mapa de calor y ranking)."""
    producto = _producto(sa6)
    if escenario not in config.ESCENARIOS_PESOS:
        raise HTTPException(400, f"Escenario no válido. Opciones: {list(config.ESCENARIOS_PESOS)}")
    with sesion() as s:
        filas = s.scalars(select(IndiceViabilidad).where(
            IndiceViabilidad.sa6 == sa6, IndiceViabilidad.escenario == escenario)).all()
    paises, riesgo = _paises(), _riesgos(sa6)
    mercados = sorted((_fila_indice(r, paises, riesgo) for r in filas),
                      key=lambda m: (m["score"] is None, -(m["score"] or 0)))
    anio_ref = filas[0].indicadores.get("anio_ref") if filas else None
    return {
        "sa6": sa6, "descripcion": producto.descripcion, "nota_agregacion": producto.nota_agregacion,
        "escenario": escenario, "pesos": config.ESCENARIOS_PESOS[escenario], "anio_referencia": anio_ref,
        "periodo": f"{config.ANIO_INICIO}-{config.ANIO_FIN}",
        "calculado_en": filas[0].calculado_en.isoformat(timespec="seconds") if filas else None,
        "resumen": {
            "mercados": len(mercados),
            "con_presencia": sum(m["tipo_mercado"] == "con_presencia" for m in mercados),
            "potenciales": sum(m["tipo_mercado"] == "potencial" for m in mercados),
            "por_estado": pd.Series([m["estado"] for m in mercados]).value_counts().to_dict() if mercados else {},
        },
        "mercados": mercados,
    }


class Pesos(BaseModel):
    demanda: float = Field(ge=0, le=1)
    trayectoria: float = Field(ge=0, le=1)
    acceso: float = Field(ge=0, le=1)
    competencia: float = Field(ge=0, le=1)
    economico: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def suma_uno(self):
        if abs(sum(self.model_dump().values()) - 1) > 1e-6:
            raise ValueError("Las ponderaciones deben sumar 1")
        return self


@app.post("/api/v1/viabilidad/{sa6}/simular")
def simular(sa6: str, pesos: Pesos):
    """Recalcula el ranking con ponderaciones definidas por el usuario (análisis what-if)."""
    _producto(sa6)
    with sesion() as s:
        filas = s.scalars(select(IndiceViabilidad).where(
            IndiceViabilidad.sa6 == sa6, IndiceViabilidad.escenario == "srs")).all()
    if not filas:
        raise HTTPException(404, "Sin índice calculado para esta subpartida")
    ind = pd.DataFrame([r.indicadores for r in filas]).replace({None: np.nan})
    ind["elegible"] = ind["elegible"].fillna(True).astype(bool)
    res = indice.puntuar(ind, pesos.model_dump())
    paises = _paises()
    salida = [
        {"iso3": r["iso3"], "nombre": paises.get(r["iso3"], {}).get("nombre", r["iso3"]),
         "score": None if pd.isna(r["score"]) else float(r["score"]),
         "ranking": None if pd.isna(r["ranking"]) else int(r["ranking"]), "estado": r["estado"]}
        for _, r in res.iterrows()
    ]
    return {"sa6": sa6, "pesos": pesos.model_dump(),
            "mercados": sorted(salida, key=lambda m: (m["score"] is None, -(m["score"] or 0)))}


@app.get("/api/v1/viabilidad/{sa6}/{iso3}")
def ficha_mercado(sa6: str, iso3: str):
    """Ficha de mercado: indicadores, trayectoria mensual, acceso, escenarios y riesgo."""
    producto = _producto(sa6)
    iso3 = iso3.upper()
    with sesion() as s:
        r = s.scalar(select(IndiceViabilidad).where(
            IndiceViabilidad.sa6 == sa6, IndiceViabilidad.iso3 == iso3, IndiceViabilidad.escenario == "srs"))
        if not r:
            raise HTTPException(404, f"Sin evaluación para {iso3} en {sa6}")
        exp = pd.read_sql(select(FactExportaciones.tiempo_id, FactExportaciones.fob_usd, FactExportaciones.ruc)
                          .where(FactExportaciones.sa6 == sa6, FactExportaciones.iso3 == iso3), s.connection())
    ind = r.indicadores
    inicio = pd.Period(f"{config.ANIO_INICIO}-01", "M")
    corte = pd.Period(f"{config.ANIO_FIN}-12", "M")
    paises = _paises()
    return {
        "sa6": sa6, "producto": producto.descripcion, "nota_agregacion": producto.nota_agregacion,
        **_fila_indice(r, paises, _riesgos(sa6)),
        "subindicadores": r.dimensiones.get("subindicadores", {}),
        "indicadores": ind,
        "serie_mensual": serie_mensual(exp, inicio, corte).to_dict("records"),
        "escenarios_economicos": economico.escenarios(
            ind.get("precio_unitario"), ind.get("kg_por_unidad") or 0.5, ind.get("flete_usd_kg") or 6.5, "CIF"),
        "fuentes": {
            "exportaciones": "PROMPERÚ / SUNAT (embarques 2021-2025)",
            "importaciones": "UN Comtrade (API pública)",
            "acceso": ind.get("fuente_acceso"),
            "costos": "Supuestos sintéticos de demostración (data/reference/costos_escenarios.csv)",
        },
    }


@app.get("/api/v1/economico/{sa6}/{iso3}")
def simular_economico(sa6: str, iso3: str, incoterm: str = Query("CIF", pattern="^(FOB|CIF)$"),
                      precio: float | None = Query(None, gt=0),
                      costo_produccion: float | None = Query(None, ge=0)):
    """Escenarios económicos con precio y costo de producción propios de la PyME."""
    ficha = ficha_mercado(sa6, iso3)
    ind = ficha["indicadores"]
    precio_base = precio or ind.get("precio_unitario")
    if not precio_base:
        raise HTTPException(422, "No hay precio de referencia; indique 'precio'")
    salida = []
    for s in economico.cargar_supuestos().values():
        if costo_produccion is not None:
            s.costo_produccion_usd_unidad = costo_produccion
        salida.append(economico.margen(precio_base, ind.get("kg_por_unidad") or 0.5,
                                       ind.get("flete_usd_kg") or 6.5, s, incoterm))
    return {"sa6": sa6, "iso3": iso3.upper(), "escenarios": salida}


@app.get("/api/v1/sensibilidad/{sa6}")
def sensibilidad(sa6: str):
    with sesion() as s:
        r = s.scalar(select(Sensibilidad).where(Sensibilidad.sa6 == sa6).order_by(Sensibilidad.id.desc()))
    if not r:
        raise HTTPException(404, "Sin análisis de sensibilidad")
    return {"sa6": sa6, "calculado_en": r.calculado_en.isoformat(timespec="seconds"), **r.resumen}


@app.get("/api/v1/modelo/{sa6}")
def modelo(sa6: str):
    with sesion() as s:
        r = s.scalar(select(ModeloMetricas).where(ModeloMetricas.modelo == f"abandono_{sa6}")
                     .order_by(ModeloMetricas.id.desc()))
    if not r:
        raise HTTPException(404, "Sin modelo entrenado")
    return r.metricas


@app.get("/api/v1/servicio/estado")
def estado_servicio():
    """Indicadores de servicio GSTI: última carga, calidad de datos y latencias (RNF-01/02)."""
    with sesion() as s:
        ejecuciones = s.scalars(select(EtlEjecucion).order_by(EtlEjecucion.id.desc()).limit(10)).all()
        ultima_ok = next((e for e in ejecuciones if e.estado == "exitoso"), None)
        calidad = s.scalars(select(CalidadDatos).where(CalidadDatos.ejecucion_id == ultima_ok.id)).all() if ultima_ok else []
    latencias = {
        ruta: {"n": len(v), "p50_ms": round(float(np.percentile(v, 50)), 1),
               "p95_ms": round(float(np.percentile(v, 95)), 1),
               "cumple_rnf01": float(np.percentile(v, 95)) < UMBRAL_LATENCIA_MS}
        for ruta, v in LATENCIAS.items() if v and ruta.startswith("/api/v1")
    }
    return {
        "salud": salud(),
        "ejecuciones": [
            {"id": e.id, "inicio": e.inicio.isoformat(timespec="seconds"),
             "fin": e.fin.isoformat(timespec="seconds") if e.fin else None,
             "duracion_seg": round((e.fin - e.inicio).total_seconds(), 1) if e.fin else None,
             "estado": e.estado, "pasos": e.pasos, "mensaje": (e.mensaje or "")[:300] or None}
            for e in ejecuciones
        ],
        "calidad": [{"fuente": c.fuente, "metrica": c.metrica, "valor": c.valor, "detalle": c.detalle} for c in calidad],
        "latencias": latencias,
        "umbral_latencia_ms": UMBRAL_LATENCIA_MS,
    }
