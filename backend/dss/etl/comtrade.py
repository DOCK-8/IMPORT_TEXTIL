"""Conector UN Comtrade (RF-01).

- API pública de vista previa: 1 periodo y hasta 500 filas por consulta, sin clave.
- Cada respuesta se guarda tal cual en data/raw/comtrade/ (trazabilidad); si el archivo ya
  existe no se vuelve a consultar, de modo que las ejecuciones siguientes son incrementales.
- Se conservan solo los agregados (customsCode C00, motCode 0, partner2Code 0).
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pandas as pd
import requests

from dss import config
from dss.analytics.indicadores import anio_referencia
from dss.etl.promperu import anio_de_carga, recuperar_numero

log = logging.getLogger(__name__)

DIR_COMTRADE = config.RAW_DIR / "comtrade"
UNIDADES = {5: "u", 8: "kg", 1: "sin", -1: None}
# Comtrade publica a Taiwán como "Other Asia, nes" (S19)
ISO_CORRECCIONES = {"S19": "TWN"}
FACTOR_ATIPICO = 50


class ComtradeError(RuntimeError):
    pass


def _get_json(url: str, params: dict | None = None, intentos: int = 4) -> dict:
    espera = config.COMTRADE_PAUSA_SEG
    for intento in range(intentos):
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code == 429 or (resp.ok and "rate limit" in resp.text.lower()):
            time.sleep(espera * (2 ** (intento + 1)))
            continue
        resp.raise_for_status()
        cuerpo = resp.json()
        if cuerpo.get("error"):
            raise ComtradeError(cuerpo["error"])
        return cuerpo
    raise ComtradeError(f"Límite de consultas excedido: {url} {params}")


def _cache(nombre: str, url: str, params: dict | None = None) -> dict:
    ruta = DIR_COMTRADE / nombre
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = _get_json(url, params)
    ruta.write_text(json.dumps(cuerpo, ensure_ascii=False), encoding="utf-8")
    time.sleep(config.COMTRADE_PAUSA_SEG)
    return cuerpo


def referencias() -> tuple[dict[int, str], dict[int, str]]:
    """Códigos Comtrade -> ISO3 y -> nombre en inglés (declarantes y socios)."""
    rep = _cache("ref/Reporters.json", f"{config.COMTRADE_REFERENCE_URL}/Reporters.json")["results"]
    par = _cache("ref/partnerAreas.json", f"{config.COMTRADE_REFERENCE_URL}/partnerAreas.json")["results"]
    iso, nombres = {0: "WLD"}, {0: "World"}
    for r in rep:
        if r.get("reporterCodeIsoAlpha3") and not r.get("isGroup"):
            iso[r["reporterCode"]] = ISO_CORRECCIONES.get(r["reporterCodeIsoAlpha3"], r["reporterCodeIsoAlpha3"])
            nombres[r["reporterCode"]] = r["reporterDesc"]
    for p in par:
        if p.get("PartnerCodeIsoAlpha3") and not p.get("isGroup") and p["PartnerCode"] not in iso:
            iso[p["PartnerCode"]] = ISO_CORRECCIONES.get(p["PartnerCodeIsoAlpha3"], p["PartnerCodeIsoAlpha3"])
            nombres[p["PartnerCode"]] = p["PartnerDesc"].strip()
    return iso, nombres


def _consultar(sa6: str, flujo: str, anio: int, declarante: int | None, socio: int | None) -> list[dict]:
    params = {"period": anio, "cmdCode": sa6, "flowCode": flujo}
    if declarante is not None:
        params["reporterCode"] = declarante
    if socio is not None:
        params["partnerCode"] = socio
    nombre = f"{flujo}_{sa6}_{anio}_r{declarante if declarante is not None else 'all'}_p{socio if socio is not None else 'all'}.json"
    return _agregados(_cache(nombre, f"{config.COMTRADE_BASE_URL}/C/A/HS", params).get("data", []))


def _agregados(datos: list[dict]) -> list[dict]:
    return [
        d for d in datos
        if d.get("customsCode") == "C00" and d.get("motCode") == 0 and d.get("partner2Code") == 0
    ]


def leer_cache(sa6: str, iso: dict[int, str]) -> pd.DataFrame:
    """Reconstruye las importaciones solo desde los JSON ya descargados (modo sin red)."""
    filas = []
    for ruta in sorted(DIR_COMTRADE.glob(f"M_{sa6}_*.json")):
        datos = json.loads(ruta.read_text(encoding="utf-8")).get("data", [])
        filas += _a_filas(_agregados(datos), sa6, iso)
    df = pd.DataFrame(filas)
    return df.drop_duplicates(["sa6", "anio", "flujo", "declarante_iso3", "socio_iso3"]) if len(df) else df


def _a_filas(datos: list[dict], sa6: str, iso: dict[int, str]) -> list[dict]:
    filas = []
    for d in datos:
        declarante, socio = iso.get(d["reporterCode"]), iso.get(d["partnerCode"])
        if not declarante or not socio or d.get("primaryValue") is None:
            continue
        filas.append({
            "sa6": sa6, "anio": int(d["refYear"]), "flujo": d["flowCode"],
            "declarante_iso3": declarante, "socio_iso3": socio,
            "valor_usd": float(d["primaryValue"]),
            "cantidad": d.get("qty"), "unidad": UNIDADES.get(d.get("qtyUnitCode")),
            "peso_kg": d.get("netWgt"), "fuente": "UN Comtrade API",
        })
    return filas


def descargar_importaciones(sa6: str, mercados_prioritarios: list[str]) -> pd.DataFrame:
    """Importaciones desde el mundo (todos los años) y desglose por proveedor (año de referencia)."""
    iso, _ = referencias()
    # La tabla de referencia contiene códigos históricos con el mismo ISO3 (p. ej. EE. UU. 840 y 842);
    # se usa el código que efectivamente declara datos.
    codigo_de: dict[str, int] = {}
    filas = []
    # El año previo al periodo alimenta solo la variable de demanda rezagada del modelo predictivo
    for anio in range(config.ANIO_INICIO - 1, config.ANIO_FIN + 1):
        try:
            datos = _consultar(sa6, "M", anio, None, 0)
            codigo_de.update({iso[d["reporterCode"]]: d["reporterCode"] for d in datos if d["reporterCode"] in iso})
            filas += _a_filas(datos, sa6, iso)
        except ComtradeError as e:
            log.warning("Comtrade %s %s sin datos mundiales: %s", sa6, anio, e)
    mundo = pd.DataFrame(filas)
    if mundo.empty:
        return mundo

    anio_ref = anio_referencia(mundo)
    ultimos = mundo[mundo["anio"] == anio_ref].sort_values("valor_usd", ascending=False)
    objetivo = list(dict.fromkeys(
        ultimos["declarante_iso3"].head(config.COMTRADE_TOP_MERCADOS).tolist()
        + [m for m in mercados_prioritarios if m in set(ultimos["declarante_iso3"])]
    ))
    for iso3 in objetivo:
        try:
            filas += _a_filas(_consultar(sa6, "M", anio_ref, codigo_de[iso3], None), sa6, iso)
        except (ComtradeError, requests.RequestException) as e:
            log.warning("Comtrade %s %s proveedores de %s: %s", sa6, anio_ref, iso3, e)
    return pd.DataFrame(filas).drop_duplicates(["sa6", "anio", "flujo", "declarante_iso3", "socio_iso3"])


def leer_hoja_excel(ruta: Path) -> tuple[pd.DataFrame, list[dict]]:
    """Hoja UNCONTRADE_Exportaciones del Excel del equipo (exportaciones de Perú por destino)."""
    crudo = pd.read_excel(ruta, "UNCONTRADE_Exportaciones", header=None, dtype=object)
    fila = crudo.index[crudo.iloc[:, 0].astype(str).str.strip() == "typeCode"]
    if len(fila) == 0:
        return pd.DataFrame(), []
    df = pd.read_excel(ruta, "UNCONTRADE_Exportaciones", header=int(fila[0]), dtype=object)
    anio = anio_de_carga([df["primaryValue"], df["netWgt"]])
    pares = df["primaryValue"].map(lambda v: recuperar_numero(v, anio))
    df["valor"] = pares.map(lambda p: p[0])
    recuperados = int(pares.map(lambda p: p[1]).sum())
    df["peso"] = df["netWgt"].map(lambda v: recuperar_numero(v, anio)[0])
    df = df[df["valor"].notna() & (df["partner2Code"] == 0)].copy()

    # Separador de miles mal interpretado (x1000) en valor o peso: se detecta por USD/kg atípico.
    # Se itera porque los pesos inflados contaminan la mediana de referencia.
    valor_inflado = pd.Series(False, index=df.index)
    peso_inflado = pd.Series(False, index=df.index)
    for _ in range(5):
        usd_kg = df["valor"] / df["peso"]
        mediana = usd_kg[(usd_kg > 0) & usd_kg.notna()].median()
        v = (usd_kg > FACTOR_ATIPICO * mediana) & ~valor_inflado
        p = (usd_kg < mediana / FACTOR_ATIPICO) & ~peso_inflado
        if not (v.any() or p.any()):
            break
        df.loc[v, "valor"] /= 1000
        df.loc[p, "peso"] /= 1000
        valor_inflado |= v
        peso_inflado |= p
    # Valor y peso inflados a la vez (USD/kg normal): salto de x1000 frente a los otros años del socio
    for _, serie in df[df["partnerCode"] != 0].groupby("partnerCode"):
        for i in serie.index:
            otros = serie["valor"].drop(i)
            ref = otros.median() if len(otros) else None
            if ref and df.at[i, "valor"] / ref > 200:
                df.at[i, "valor"] /= 1000
                df.at[i, "peso"] = df.at[i, "peso"] / 1000 if pd.notna(df.at[i, "peso"]) else None
                valor_inflado.at[i] = True
    # Consistencia contable: el total mundial debe igualar la suma de los socios del mismo año
    socios = df[df["partnerCode"] != 0].groupby("refYear")["valor"].sum()
    for i in df.index[df["partnerCode"] == 0]:
        suma = socios.get(df.at[i, "refYear"])
        if suma and 900 <= df.at[i, "valor"] / suma <= 1100:
            df.at[i, "valor"] /= 1000
            valor_inflado.at[i] = True
    salida = pd.DataFrame({
        "sa6": df["cmdCode"].astype(str).str.zfill(6),
        "anio": df["refYear"].astype(int),
        "flujo": df["flowCode"].astype(str),
        "declarante_iso3": df["reporterISO"].astype(str),
        "socio_iso3": df["partnerISO"].astype(str).replace({"W00": "WLD"}),
        "valor_usd": df["valor"].astype(float),
        "cantidad": pd.to_numeric(df["qty"], errors="coerce"),
        "unidad": df["qtyUnitAbbr"].astype(str),
        "peso_kg": df["peso"],
        "fuente": "UN Comtrade (Excel equipo)",
    })
    calidad = [
        {"fuente": "UNCOMTRADE_EXCEL", "metrica": "registros_validos", "valor": float(len(salida)), "detalle": None},
        {"fuente": "UNCOMTRADE_EXCEL", "metrica": "valores_recuperados_de_fecha", "valor": float(recuperados), "detalle": None},
        {"fuente": "UNCOMTRADE_EXCEL", "metrica": "valores_escala_miles_corregidos", "valor": float(valor_inflado.sum()),
         "detalle": f"USD/kg > {FACTOR_ATIPICO}x mediana ({mediana:.1f}), salto x1000 entre años o total mundial = 1000 x suma de socios"},
        {"fuente": "UNCOMTRADE_EXCEL", "metrica": "pesos_escala_miles_corregidos", "valor": float(peso_inflado.sum()), "detalle": None},
    ]
    return salida, calidad
