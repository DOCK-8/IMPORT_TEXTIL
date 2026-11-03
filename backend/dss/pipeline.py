"""Orquestador ETL + analítica (RF-01 a RF-04, RF-06).

Uso:
    python -m dss.pipeline                 # ETL completo + índice + modelo
    python -m dss.pipeline --sin-api       # usa solo la caché de UN Comtrade (sin red)
    python -m dss.pipeline --productos todos

Cada ejecución queda registrada en etl_ejecucion (pasos, duración, registros) y sus métricas
de calidad en calidad_datos. La recarga es completa e idempotente.
"""

from __future__ import annotations

import argparse
import logging
import time
import traceback
from datetime import date, datetime

import pandas as pd
from sqlalchemy import delete, insert, update

from dss import catalog, config, repositorio
from dss.analytics import indicadores, indice
from dss.countries import ISO3_A_NOMBRE_ES, ISO3_A_REGION, nombre_es, region
from dss.db import crear_esquema, sesion
from dss.etl import comtrade, promperu
from dss.ml import entrenamiento
from dss.models import (
    CalidadDatos, DimEmpresa, DimPais, DimPrenda, DimProducto, DimRegion, DimRegulaciones,
    DimSubpartidaNacional, DimTiempo, EtlEjecucion, FactComercioMundial, FactExportaciones,
    IndiceViabilidad, ModeloMetricas, RiesgoAbandono, Sensibilidad,
)

log = logging.getLogger("dss.pipeline")

TABLAS_RECARGA = [
    IndiceViabilidad, RiesgoAbandono, Sensibilidad, FactExportaciones, FactComercioMundial,
    DimRegulaciones, DimSubpartidaNacional, DimEmpresa, DimProducto, DimPrenda, DimPais, DimRegion,
    DimTiempo,
]


class Ejecucion:
    """Bitácora de una corrida del pipeline (gestión de servicio)."""

    def __init__(self) -> None:
        with sesion() as s:
            # Una corrida anterior que no llegó a cerrarse (caída del proceso) se marca como interrumpida
            s.execute(update(EtlEjecucion).where(EtlEjecucion.estado == "en_curso")
                      .values(estado="interrumpido", fin=datetime.now()))
            reg = EtlEjecucion(inicio=datetime.now(), estado="en_curso", pasos=[])
            s.add(reg)
            s.flush()
            self.id = reg.id
        self.pasos: list[dict] = []
        self.calidad: list[dict] = []

    def paso(self, nombre: str, funcion, *args, **kwargs):
        t0 = time.perf_counter()
        log.info("-> %s", nombre)
        resultado = funcion(*args, **kwargs)
        info = {"paso": nombre, "segundos": round(time.perf_counter() - t0, 2)}
        if isinstance(resultado, pd.DataFrame):
            info["registros"] = len(resultado)
        self.pasos.append(info)
        self._guardar("en_curso")
        return resultado

    def _guardar(self, estado: str, mensaje: str | None = None) -> None:
        with sesion() as s:
            reg = s.get(EtlEjecucion, self.id)
            reg.pasos, reg.estado, reg.mensaje = list(self.pasos), estado, mensaje
            if estado != "en_curso":
                reg.fin = datetime.now()
                if self.calidad:
                    s.execute(insert(CalidadDatos), [_json({"ejecucion_id": self.id, **c}) for c in self.calidad])

    def cerrar(self, estado: str, mensaje: str | None = None) -> None:
        self._guardar(estado, mensaje)


def _registros(df: pd.DataFrame, columnas: list[str]) -> list[dict]:
    """Filas con tipos nativos de Python (psycopg2 no adapta escalares de NumPy)."""
    return [_json(r) for r in df[columnas].to_dict("records")]


def cargar_dimensiones(nombres_en: dict[str, str], paises_extra: set[str]) -> None:
    regiones = sorted(set(ISO3_A_REGION.values()) | {"Otras regiones"})
    id_region = {r: i + 1 for i, r in enumerate(regiones)}
    paises = (set(ISO3_A_NOMBRE_ES) | set(nombres_en) | paises_extra) - {"WLD"}
    meses = pd.period_range(f"{config.ANIO_INICIO}-01", f"{config.ANIO_FIN}-12", freq="M")
    acceso = pd.read_csv(config.REFERENCE_DIR / "acceso_mercado.csv", dtype={"sa6": str})
    filas_acceso = []
    for r in acceso.to_dict("records"):
        for sa6 in ([s.sa6 for s in catalog.SUBPARTIDAS] if r["sa6"] == "*" else [r["sa6"]]):
            filas_acceso.append({
                "iso3": r["iso3"], "sa6": sa6, "tlc_vigente": bool(r["tlc_vigente"]), "acuerdo": r["acuerdo"],
                "arancel_nmf": r["arancel_nmf"], "arancel_preferencial": r["arancel_preferencial"],
                "n_ntm": r["n_ntm"], "requisitos": r["requisitos"], "fuente_url": r["fuente_url"],
                "fecha_consulta": pd.to_datetime(r["fecha_consulta"]).date() if pd.notna(r["fecha_consulta"]) else None,
                "verificado": bool(r["verificado"]), "elegible": bool(r["elegible"]),
            })
    filas_acceso = [{k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in f.items()} for f in filas_acceso]

    with sesion() as s:
        for tabla in TABLAS_RECARGA:
            s.execute(delete(tabla))
        s.execute(insert(DimRegion), [{"id": i, "nombre": r} for r, i in id_region.items()])
        s.execute(insert(DimPais), [
            {"iso3": iso, "nombre": nombre_es(iso, nombres_en.get(iso)), "nombre_en": nombres_en.get(iso),
             "codigo_m49": None, "region_id": id_region[region(iso)]}
            for iso in sorted(paises)
        ])
        s.execute(insert(DimPrenda), [{"codigo": p.codigo, "nombre": p.nombre} for p in catalog.PRENDAS])
        s.execute(insert(DimProducto), [
            {"sa6": sp.sa6, "descripcion": sp.descripcion, "prenda_codigo": sp.prenda,
             "nota_agregacion": sp.nota_agregacion or None} for sp in catalog.SUBPARTIDAS
        ])
        s.execute(insert(DimSubpartidaNacional), [
            {"codigo10": n, "sa6": sp.sa6, "descripcion": sp.descripcion}
            for sp in catalog.SUBPARTIDAS for n in sp.nacionales
        ])
        s.execute(insert(DimTiempo), [
            {"id": m.year * 100 + m.month, "anio": m.year, "mes": m.month, "trimestre": (m.month - 1) // 3 + 1}
            for m in meses
        ])
        s.execute(insert(DimRegulaciones), [f for f in filas_acceso if f["iso3"] in paises])


def cargar_exportaciones(df: pd.DataFrame) -> pd.DataFrame:
    empresas = df.sort_values("fecha_embarque").groupby("ruc").agg(
        razon_social=("razon_social", "last"), region_origen=("region_origen", "last")).reset_index()
    nacionales = set(n for sp in catalog.SUBPARTIDAS for n in sp.nacionales)
    nuevos = sorted(set(df["codigo10"]) - nacionales)
    with sesion() as s:
        s.execute(insert(DimEmpresa), _registros(empresas, ["ruc", "razon_social", "region_origen"]))
        if nuevos:  # códigos homologados por prefijo: se registran en la matriz
            s.execute(insert(DimSubpartidaNacional), [
                {"codigo10": c, "sa6": catalog.homologar(c), "descripcion": None} for c in nuevos
            ])
        df = df.assign(fuente="PROMPERU", fecha_embarque=pd.to_datetime(df["fecha_embarque"]).dt.date)
        s.execute(insert(FactExportaciones), _registros(df, [
            "hash_registro", "fecha_embarque", "tiempo_id", "ruc", "iso3", "codigo10", "sa6", "fob_usd",
            "cantidad", "peso_neto_kg", "peso_bruto_kg", "descripcion_comercial", "fob_recuperado",
            "peso_corregido", "fuente",
        ]))
    return df


def cargar_comercio(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["sa6"].isin([s.sa6 for s in catalog.SUBPARTIDAS])]
    df = df.drop_duplicates(["sa6", "anio", "flujo", "declarante_iso3", "socio_iso3"])
    with sesion() as s:
        if len(df):
            s.execute(insert(FactComercioMundial), _registros(df, [
                "sa6", "anio", "flujo", "declarante_iso3", "socio_iso3", "valor_usd", "cantidad",
                "unidad", "peso_kg", "fuente",
            ]))
    return df


def contrastar_fuentes(exp: pd.DataFrame, com: pd.DataFrame) -> list[dict]:
    """Exportaciones PROMPERÚ vs exportaciones declaradas por Perú a Comtrade (sin sumarlas)."""
    salida = []
    x = com[(com["flujo"] == "X") & (com["declarante_iso3"] == "PER") & (com["socio_iso3"] == "WLD")]
    for (sa6, anio), v in x.groupby(["sa6", "anio"])["valor_usd"].sum().items():
        fob = exp[(exp["sa6"] == sa6) & (pd.to_datetime(exp["fecha_embarque"]).dt.year == anio)]["fob_usd"].sum()
        if fob:
            salida.append({"fuente": "CONTRASTE", "metrica": f"discrepancia_pct_{sa6}_{anio}",
                           "valor": round(100 * (fob - v) / v, 2),
                           "detalle": f"PROMPERU {fob:,.0f} vs Comtrade {v:,.0f} USD"})
    return salida


def calcular_resultados(sa6: str) -> dict:
    exp, com, acc = repositorio.exportaciones(), repositorio.comercio(), repositorio.acceso()
    inicio = pd.Period(f"{config.ANIO_INICIO}-01", "M")
    corte = pd.Period(f"{config.ANIO_FIN}-12", "M")
    ind = indicadores.calcular(sa6, exp, com, acc, inicio, corte)
    if ind.empty:
        return {"sa6": sa6, "mercados": 0}
    ahora = datetime.now()
    filas = []
    for escenario, pesos in config.ESCENARIOS_PESOS.items():
        res = indice.puntuar(ind, pesos)
        for i, r in res.iterrows():
            dims = {d: (None if pd.isna(r[d]) else round(float(r[d]), 4)) for d in indice.DIMENSIONES}
            subs = {c: (None if pd.isna(r[c]) else round(float(r[c]), 4)) for c in res.columns if c.startswith("z_")}
            filas.append({
                "sa6": sa6, "iso3": r["iso3"], "escenario": escenario,
                "score": None if pd.isna(r["score"]) else float(r["score"]),
                "ranking": None if pd.isna(r["ranking"]) else int(r["ranking"]),
                "estado": r["estado"], "tipo_mercado": ind.at[i, "tipo_mercado"],
                "dimensiones": {**dims, "subindicadores": subs, "faltantes": r["dimensiones_faltantes"]},
                "indicadores": _json(ind.loc[i].to_dict()), "calculado_en": ahora,
            })
    sens = indice.sensibilidad(ind)
    with sesion() as s:
        s.execute(delete(IndiceViabilidad).where(IndiceViabilidad.sa6 == sa6))
        s.execute(insert(IndiceViabilidad), filas)
        s.execute(delete(Sensibilidad).where(Sensibilidad.sa6 == sa6))
        s.add(Sensibilidad(sa6=sa6, resumen=sens, calculado_en=ahora))
    return {"sa6": sa6, "mercados": len(ind), "sensibilidad": sens["variantes"]}


def _json(d: dict) -> dict:
    def limpio(v):
        if isinstance(v, dict):
            return {str(k): limpio(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [limpio(x) for x in v]
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if hasattr(v, "item"):
            return v.item()
        return v
    return limpio(d)


def entrenar_modelo(sa6: str) -> dict:
    exp, com = repositorio.exportaciones(), repositorio.comercio()
    mundo = com[(com["sa6"] == sa6) & (com["flujo"] == "M") & (com["socio_iso3"] == "WLD")]
    reporte = entrenamiento.entrenar(exp, mundo, sa6)
    with sesion() as s:
        s.add(ModeloMetricas(entrenado_en=datetime.now(), modelo=f"abandono_{sa6}",
                             metricas=_json({k: v for k, v in reporte.items() if k != "predicciones_relaciones"})))
        riesgo = entrenamiento.riesgo_por_mercado(reporte.get("predicciones_relaciones", []))
        if len(riesgo):
            s.execute(insert(RiesgoAbandono), [
                {"sa6": sa6, "iso3": r["iso3"], "probabilidad": float(r["probabilidad"]), "clase": r["clase"],
                 "n_relaciones": int(r["n_relaciones"]), "modelo": reporte["modelo_produccion"]["nombre"],
                 "fecha_corte": date(config.ANIO_FIN, 12, 31)}
                for r in riesgo.to_dict("records")
            ])
    return reporte


def ejecutar(usar_api: bool = True, productos: str = "con_datos") -> int:
    crear_esquema()
    ej = Ejecucion()
    try:
        crudo = ej.paso("extraer_promperu", promperu.leer_hojas, config.EXPORTACIONES_XLSX)
        exp, cal = ej.paso("limpiar_promperu", promperu.limpiar, crudo)
        ej.calidad += cal
        com_excel, cal = ej.paso("extraer_comtrade_excel", comtrade.leer_hoja_excel, config.EXPORTACIONES_XLSX)
        ej.calidad += cal

        sa6_objetivo = (
            [s.sa6 for s in catalog.SUBPARTIDAS] if productos == "todos"
            else sorted(set(exp["sa6"])) if productos == "con_datos"
            else productos.split(",")
        )
        marcos, nombres_en = [com_excel], {}
        try:
            iso, nombres = comtrade.referencias()
            nombres_en = {iso[k]: v for k, v in nombres.items() if k in iso}
            for sa6 in sa6_objetivo:
                if usar_api:
                    marcos.append(ej.paso(f"extraer_comtrade_api_{sa6}", comtrade.descargar_importaciones,
                                          sa6, sorted(set(exp.loc[exp["sa6"] == sa6, "iso3"]))))
                else:
                    marcos.append(ej.paso(f"leer_cache_comtrade_{sa6}", comtrade.leer_cache, sa6, iso))
        except Exception as e:  # la caída de la fuente externa no detiene el servicio
            log.warning("UN Comtrade no disponible: %s", e)
            ej.calidad.append({"fuente": "UNCOMTRADE_API", "metrica": "fuente_no_disponible", "valor": 1.0, "detalle": str(e)[:500]})
        com = pd.concat([m for m in marcos if len(m)], ignore_index=True)
        ej.calidad.append({"fuente": "UNCOMTRADE_API", "metrica": "registros_importacion",
                           "valor": float((com["flujo"] == "M").sum()), "detalle": ", ".join(sa6_objetivo)})

        paises_extra = set(exp["iso3"]) | set(com["declarante_iso3"])
        ej.paso("cargar_dimensiones", cargar_dimensiones, nombres_en, paises_extra)
        ej.paso("cargar_fact_exportaciones", cargar_exportaciones, exp)
        ej.paso("cargar_fact_comercio_mundial", cargar_comercio, com)
        ej.calidad += contrastar_fuentes(exp, com)

        for sa6 in sa6_objetivo:
            ej.paso(f"indice_viabilidad_{sa6}", calcular_resultados, sa6)
        for sa6 in sorted(set(exp["sa6"])):
            ej.paso(f"modelo_abandono_{sa6}", entrenar_modelo, sa6)
        ej.cerrar("exitoso")
        log.info("Pipeline terminado (ejecución %s)", ej.id)
        return 0
    except Exception as e:
        log.error("Pipeline fallido: %s", e)
        ej.cerrar("fallido", f"{e}\n{traceback.format_exc()[-2000:]}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline ETL y analítica del DSS textil")
    parser.add_argument("--sin-api", action="store_true", help="no consultar UN Comtrade; usar solo la caché")
    parser.add_argument("--productos", default="con_datos", help="con_datos | todos | lista SA6 separada por comas")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    raise SystemExit(ejecutar(usar_api=not args.sin_api, productos=args.productos))


if __name__ == "__main__":
    main()
