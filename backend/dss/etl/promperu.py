"""Extracción y limpieza de los embarques PROMPERÚ (hojas PROMPERU_Exportaciones_AAAA).

Problemas detectados en la fuente y regla aplicada (cada registro conserva su bandera):

1. Fechas mezcladas: ene-jun como texto 'dd/mm/aaaa', jul-dic como fecha de Excel.
   -> se normalizan ambas a fecha.
2. Montos convertidos en fechas por la configuración regional de Excel:
   '2125.4' -> 01/04/2125 (forma año.mes) y '26.5' -> 26/05/<año de carga> (forma día.mes).
   -> se reconstruye el número a partir de las partes de la fecha (fob_recuperado / peso).
   Validado: la distribución USD/unidad de los montos recuperados coincide con la de los
   montos íntegros (mediana 55 vs 62 USD/unidad).
3. Pesos con tres decimales leídos con separador de miles ('15.351' -> 15351):
   la relación kg/unidad resulta bimodal (0.1-1 kg vs 100-1000 kg por prenda).
   -> si kg/unidad > 20 se divide entre 1000; si sigue siendo inverosímil se deja nulo.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from dss.catalog import homologar
from dss.countries import iso3_desde_nombre

COLUMNAS = {
    "Fecha embarque": "fecha_embarque",
    "RUC": "ruc",
    "Razón social": "razon_social",
    "Región": "region_origen",
    "Partida": "codigo10",
    "Descripción arancelaria": "descripcion_arancelaria",
    "Descripción comercial": "descripcion_comercial",
    "Mercado destino": "mercado_destino",
    "Monto FOB (USD)": "fob_usd",
    "Peso neto (kg)": "peso_neto_kg",
    "Peso bruto (kg)": "peso_bruto_kg",
    "Cantidad": "cantidad",
}
MAX_KG_POR_UNIDAD = 20.0


def _es_fecha(v) -> bool:
    return isinstance(v, (datetime, pd.Timestamp, date))


def anio_de_carga(columnas: list[pd.Series]) -> int | None:
    """Año que Excel asignó a los números leídos como 'día.mes' (el más repetido)."""
    anios = Counter(v.year for s in columnas for v in s if _es_fecha(v) and v.day != 1)
    return anios.most_common(1)[0][0] if anios else None


def recuperar_numero(v, anio_carga: int | None) -> tuple[float | None, bool]:
    """Devuelve (valor numérico, fue_recuperado_de_fecha)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None, False
    if _es_fecha(v):
        entero, decimal = (v.day, v.month) if v.year == anio_carga else (v.year, v.month)
        return entero + decimal / (10 if decimal < 10 else 100), True
    num = pd.to_numeric(str(v).strip().replace(",", ""), errors="coerce")
    return (None if pd.isna(num) else float(num)), False


def _corregir_peso(peso: float | None, cantidad: float | None) -> tuple[float | None, bool]:
    if peso is None or not cantidad:
        return peso, False
    if peso / cantidad <= MAX_KG_POR_UNIDAD:
        return peso, False
    corregido = peso / 1000
    return (corregido if corregido / cantidad <= MAX_KG_POR_UNIDAD else None), True


def _parsear_fecha(v) -> date | None:
    if _es_fecha(v):
        return pd.Timestamp(v).date()
    ts = pd.to_datetime(str(v).strip(), dayfirst=True, errors="coerce")
    return None if pd.isna(ts) else ts.date()


def leer_hojas(ruta: Path) -> pd.DataFrame:
    libro = pd.ExcelFile(ruta)
    marcos = []
    for hoja in libro.sheet_names:
        if not hoja.upper().startswith("PROMPERU"):
            continue
        crudo = pd.read_excel(libro, hoja, header=None, dtype=object)
        fila = crudo.index[crudo.iloc[:, 0].astype(str).str.strip() == "Fecha embarque"]
        if len(fila) == 0:
            raise ValueError(f"No se encontró la cabecera 'Fecha embarque' en la hoja {hoja}")
        df = pd.read_excel(libro, hoja, header=int(fila[0]), dtype=object).dropna(axis=1, how="all")
        df = df.rename(columns=COLUMNAS)[list(COLUMNAS.values())]
        df["hoja"] = hoja
        marcos.append(df)
    return pd.concat(marcos, ignore_index=True)


def limpiar(crudo: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Normaliza, recupera valores corruptos, homologa y deduplica. Devuelve (datos, calidad)."""
    df = crudo.copy()
    calidad: list[dict] = []

    def medir(metrica: str, valor: float, detalle: str | None = None) -> None:
        calidad.append({"fuente": "PROMPERU", "metrica": metrica, "valor": float(valor), "detalle": detalle})

    medir("registros_leidos", len(df), f"{df['hoja'].nunique()} hojas")

    df["fecha_era_texto"] = df["fecha_embarque"].map(lambda v: not _es_fecha(v))
    df["fecha_embarque"] = df["fecha_embarque"].map(_parsear_fecha)
    medir("fechas_texto_normalizadas", df["fecha_era_texto"].sum())

    anio = anio_de_carga([df["fob_usd"], df["peso_neto_kg"], df["peso_bruto_kg"]])
    for col in ("fob_usd", "peso_neto_kg", "peso_bruto_kg", "cantidad"):
        pares = df[col].map(lambda v: recuperar_numero(v, anio))
        df[col] = pares.map(lambda p: p[0]).astype(float)
        df[f"{col}_rec"] = pares.map(lambda p: p[1])
    df["fob_recuperado"] = df["fob_usd_rec"]
    medir("fob_recuperados_de_fecha", df["fob_usd_rec"].sum(), f"año de carga detectado: {anio}")
    medir("pesos_recuperados_de_fecha", (df["peso_neto_kg_rec"] | df["peso_bruto_kg_rec"]).sum())

    df.loc[df["cantidad"] <= 0, "cantidad"] = None
    neto = [_corregir_peso(p, q) for p, q in zip(df["peso_neto_kg"], df["cantidad"])]
    bruto = [_corregir_peso(p, q) for p, q in zip(df["peso_bruto_kg"], df["cantidad"])]
    df["peso_neto_kg"] = [p for p, _ in neto]
    df["peso_bruto_kg"] = [p for p, _ in bruto]
    df["peso_corregido"] = [a or b for (_, a), (_, b) in zip(neto, bruto)]
    medir("pesos_escala_miles_corregidos", df["peso_corregido"].sum(), f"umbral {MAX_KG_POR_UNIDAD} kg/unidad")

    df["ruc"] = df["ruc"].astype(str).str.strip().str.zfill(11)
    df["codigo10"] = df["codigo10"].astype(str).str.replace(r"\D", "", regex=True)
    df["sa6"] = df["codigo10"].map(homologar)
    df["iso3"] = df["mercado_destino"].astype(str).map(iso3_desde_nombre)
    sin_pais = sorted(df.loc[df["iso3"].isna(), "mercado_destino"].astype(str).unique())
    medir("paises_no_mapeados", len(sin_pais), ", ".join(sin_pais) or None)
    medir("partidas_no_homologadas", df["sa6"].isna().sum())

    df["hash_registro"] = [
        hashlib.sha1("|".join(map(str, fila)).encode()).hexdigest()
        for fila in crudo[list(COLUMNAS.values())].itertuples(index=False)
    ]
    duplicados = df["hash_registro"].duplicated()
    medir("duplicados_eliminados", duplicados.sum())
    df = df[~duplicados]

    esenciales = ["fecha_embarque", "ruc", "iso3", "sa6", "fob_usd"]
    incompletos = df[esenciales].isna().any(axis=1) | (df["fob_usd"] <= 0)
    medir("excluidos_campos_esenciales", incompletos.sum(), ", ".join(esenciales))
    df = df[~incompletos].copy()

    medir("registros_validos", len(df))
    medir("completitud_peso_neto_pct", 100 * df["peso_neto_kg"].notna().mean())
    medir("completitud_cantidad_pct", 100 * df["cantidad"].notna().mean())
    meses = pd.to_datetime(df["fecha_embarque"]).dt.to_period("M").nunique()
    medir("cobertura_meses", meses, f"{df['fecha_embarque'].min()} a {df['fecha_embarque'].max()}")

    df["tiempo_id"] = pd.to_datetime(df["fecha_embarque"]).dt.strftime("%Y%m").astype(int)
    return df, calidad
