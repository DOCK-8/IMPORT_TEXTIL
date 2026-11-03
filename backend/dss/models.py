"""Data Warehouse en esquema copo de nieve (RF-03).

Hechos:      fact_exportaciones (embarques PROMPERÚ/SUNAT), fact_comercio_mundial (UN Comtrade)
Dimensiones: dim_tiempo, dim_pais -> dim_region, dim_producto -> dim_prenda,
             dim_subpartida_nacional -> dim_producto, dim_empresa, dim_regulaciones
Resultados:  indice_viabilidad, sensibilidad, riesgo_abandono, modelo_metricas
Servicio:    etl_ejecucion, calidad_datos (GSTI, RF-06)
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


# --- Dimensiones -------------------------------------------------------------------------


class DimRegion(Base):
    __tablename__ = "dim_region"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)


class DimPais(Base):
    __tablename__ = "dim_pais"
    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    nombre_en: Mapped[str | None] = mapped_column(String(120))
    codigo_m49: Mapped[int | None] = mapped_column(Integer)
    region_id: Mapped[int] = mapped_column(ForeignKey("dim_region.id"))


class DimPrenda(Base):
    __tablename__ = "dim_prenda"
    codigo: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))


class DimProducto(Base):
    __tablename__ = "dim_producto"
    sa6: Mapped[str] = mapped_column(String(6), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(200))
    prenda_codigo: Mapped[str] = mapped_column(ForeignKey("dim_prenda.codigo"))
    nota_agregacion: Mapped[str | None] = mapped_column(Text)


class DimSubpartidaNacional(Base):
    """Matriz de homologación SUNAT (10 dígitos) -> SA (6 dígitos)."""

    __tablename__ = "dim_subpartida_nacional"
    codigo10: Mapped[str] = mapped_column(String(10), primary_key=True)
    sa6: Mapped[str] = mapped_column(ForeignKey("dim_producto.sa6"))
    descripcion: Mapped[str | None] = mapped_column(Text)


class DimTiempo(Base):
    __tablename__ = "dim_tiempo"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # AAAAMM
    anio: Mapped[int] = mapped_column(Integer)
    mes: Mapped[int] = mapped_column(Integer)
    trimestre: Mapped[int] = mapped_column(Integer)


class DimEmpresa(Base):
    __tablename__ = "dim_empresa"
    ruc: Mapped[str] = mapped_column(String(11), primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(200))
    region_origen: Mapped[str | None] = mapped_column(String(60))


class DimRegulaciones(Base):
    """Condiciones de acceso por mercado y subpartida (TLC, aranceles, NTMs)."""

    __tablename__ = "dim_regulaciones"
    __table_args__ = (UniqueConstraint("iso3", "sa6"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iso3: Mapped[str] = mapped_column(ForeignKey("dim_pais.iso3"))
    sa6: Mapped[str] = mapped_column(ForeignKey("dim_producto.sa6"))
    tlc_vigente: Mapped[bool | None] = mapped_column(Boolean)
    acuerdo: Mapped[str | None] = mapped_column(String(160))
    arancel_nmf: Mapped[float | None] = mapped_column(Float)
    arancel_preferencial: Mapped[float | None] = mapped_column(Float)
    n_ntm: Mapped[int | None] = mapped_column(Integer)
    requisitos: Mapped[str | None] = mapped_column(Text)
    fuente_url: Mapped[str | None] = mapped_column(Text)
    fecha_consulta: Mapped[date | None] = mapped_column(Date)
    verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    elegible: Mapped[bool] = mapped_column(Boolean, default=True)  # requisito obligatorio cumplible


# --- Hechos ------------------------------------------------------------------------------


class FactExportaciones(Base):
    """Un embarque de exportación peruana (grano: DUA/línea)."""

    __tablename__ = "fact_exportaciones"
    __table_args__ = (
        Index("ix_fexp_producto_pais_tiempo", "sa6", "iso3", "tiempo_id"),
        Index("ix_fexp_empresa", "ruc"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hash_registro: Mapped[str] = mapped_column(String(40), unique=True)
    fecha_embarque: Mapped[date] = mapped_column(Date)
    tiempo_id: Mapped[int] = mapped_column(ForeignKey("dim_tiempo.id"))
    ruc: Mapped[str] = mapped_column(ForeignKey("dim_empresa.ruc"))
    iso3: Mapped[str] = mapped_column(ForeignKey("dim_pais.iso3"))
    codigo10: Mapped[str] = mapped_column(ForeignKey("dim_subpartida_nacional.codigo10"))
    sa6: Mapped[str] = mapped_column(ForeignKey("dim_producto.sa6"))
    fob_usd: Mapped[float] = mapped_column(Float)
    cantidad: Mapped[float | None] = mapped_column(Float)
    peso_neto_kg: Mapped[float | None] = mapped_column(Float)
    peso_bruto_kg: Mapped[float | None] = mapped_column(Float)
    descripcion_comercial: Mapped[str | None] = mapped_column(Text)
    fob_recuperado: Mapped[bool] = mapped_column(Boolean, default=False)
    peso_corregido: Mapped[bool] = mapped_column(Boolean, default=False)
    fuente: Mapped[str] = mapped_column(String(40))


class FactComercioMundial(Base):
    """Flujo anual declarado en UN Comtrade (importador <- proveedor)."""

    __tablename__ = "fact_comercio_mundial"
    __table_args__ = (
        UniqueConstraint("sa6", "anio", "flujo", "declarante_iso3", "socio_iso3"),
        Index("ix_fcm_producto_anio", "sa6", "anio"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sa6: Mapped[str] = mapped_column(ForeignKey("dim_producto.sa6"))
    anio: Mapped[int] = mapped_column(Integer)
    flujo: Mapped[str] = mapped_column(String(1))  # M importación, X exportación
    declarante_iso3: Mapped[str] = mapped_column(String(3))
    socio_iso3: Mapped[str] = mapped_column(String(3))  # WLD = mundo
    valor_usd: Mapped[float] = mapped_column(Float)
    cantidad: Mapped[float | None] = mapped_column(Float)
    unidad: Mapped[str | None] = mapped_column(String(10))
    peso_kg: Mapped[float | None] = mapped_column(Float)
    fuente: Mapped[str] = mapped_column(String(40))


# --- Resultados analíticos ---------------------------------------------------------------


class IndiceViabilidad(Base):
    __tablename__ = "indice_viabilidad"
    __table_args__ = (UniqueConstraint("sa6", "iso3", "escenario"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sa6: Mapped[str] = mapped_column(ForeignKey("dim_producto.sa6"))
    iso3: Mapped[str] = mapped_column(ForeignKey("dim_pais.iso3"))
    escenario: Mapped[str] = mapped_column(String(30))
    score: Mapped[float | None] = mapped_column(Float)
    ranking: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(20))  # completa | parcial | incompleta
    tipo_mercado: Mapped[str] = mapped_column(String(20))  # con_presencia | potencial
    dimensiones: Mapped[dict] = mapped_column(JSONType)  # z por dimensión
    indicadores: Mapped[dict] = mapped_column(JSONType)  # valores crudos
    calculado_en: Mapped[datetime] = mapped_column(DateTime)


class RiesgoAbandono(Base):
    __tablename__ = "riesgo_abandono"
    __table_args__ = (UniqueConstraint("sa6", "iso3"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sa6: Mapped[str] = mapped_column(ForeignKey("dim_producto.sa6"))
    iso3: Mapped[str] = mapped_column(ForeignKey("dim_pais.iso3"))
    probabilidad: Mapped[float] = mapped_column(Float)  # media ponderada por FOB de relaciones activas
    clase: Mapped[str] = mapped_column(String(10))  # bajo | medio | alto
    n_relaciones: Mapped[int] = mapped_column(Integer)
    modelo: Mapped[str] = mapped_column(String(40))
    fecha_corte: Mapped[date] = mapped_column(Date)


class ModeloMetricas(Base):
    __tablename__ = "modelo_metricas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entrenado_en: Mapped[datetime] = mapped_column(DateTime)
    modelo: Mapped[str] = mapped_column(String(40))
    metricas: Mapped[dict] = mapped_column(JSONType)


class Sensibilidad(Base):
    __tablename__ = "sensibilidad"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sa6: Mapped[str] = mapped_column(String(6))
    resumen: Mapped[dict] = mapped_column(JSONType)
    calculado_en: Mapped[datetime] = mapped_column(DateTime)


# --- Gestión del servicio (GSTI) ---------------------------------------------------------


class EtlEjecucion(Base):
    __tablename__ = "etl_ejecucion"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inicio: Mapped[datetime] = mapped_column(DateTime)
    fin: Mapped[datetime | None] = mapped_column(DateTime)
    estado: Mapped[str] = mapped_column(String(20))  # en_curso | exitoso | fallido
    pasos: Mapped[list] = mapped_column(JSONType, default=list)
    mensaje: Mapped[str | None] = mapped_column(Text)


class CalidadDatos(Base):
    __tablename__ = "calidad_datos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ejecucion_id: Mapped[int] = mapped_column(ForeignKey("etl_ejecucion.id"))
    fuente: Mapped[str] = mapped_column(String(60))
    metrica: Mapped[str] = mapped_column(String(60))
    valor: Mapped[float] = mapped_column(Float)
    detalle: Mapped[str | None] = mapped_column(Text)
