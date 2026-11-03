"""Lectura del Data Warehouse como DataFrames (compartido por el pipeline y la API)."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from dss.db import engine
from dss.models import DimRegulaciones, FactComercioMundial, FactExportaciones


def exportaciones() -> pd.DataFrame:
    return pd.read_sql(select(FactExportaciones), engine)


def comercio() -> pd.DataFrame:
    return pd.read_sql(select(FactComercioMundial), engine)


def acceso() -> pd.DataFrame:
    return pd.read_sql(select(DimRegulaciones), engine)
