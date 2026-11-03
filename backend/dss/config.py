"""Configuración central del DSS (rutas, base de datos y parámetros del índice)."""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DSS_DATA_DIR", BACKEND_DIR / "data"))
RAW_DIR = DATA_DIR / "raw"  # archivos originales tal como se descargan (trazabilidad)
REFERENCE_DIR = DATA_DIR / "reference"  # tablas curadas: acceso, costos, países
ARTIFACTS_DIR = Path(os.getenv("DSS_ARTIFACTS_DIR", BACKEND_DIR / "artifacts"))

# Archivo PROMPERÚ consolidado (hojas 2021-2025 + hoja UN Comtrade)
EXPORTACIONES_XLSX = Path(
    os.getenv("DSS_EXPORTACIONES_XLSX", RAW_DIR / "promperu" / "Exportaciones.xlsx")
)

DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'dss_local.db').as_posix()}"
)

# Periodo de análisis (artículo, sección III.C)
ANIO_INICIO = 2021
ANIO_FIN = 2025

# Criterio operativo de posible abandono (meses consecutivos sin exportar)
MESES_ABANDONO = 24

# Ponderaciones del Índice de Atractivo Comercial (SRS, sección 3)
PESOS_SRS = {
    "demanda": 0.35,
    "trayectoria": 0.25,
    "acceso": 0.15,
    "competencia": 0.15,
    "economico": 0.10,
}

# Escenarios alternativos para el análisis de sensibilidad (artículo, III.J)
ESCENARIOS_PESOS = {
    "srs": PESOS_SRS,
    "iguales": {k: 0.20 for k in PESOS_SRS},
    "demanda_alta": {"demanda": 0.50, "trayectoria": 0.20, "acceso": 0.10, "competencia": 0.10, "economico": 0.10},
    "trayectoria_alta": {"demanda": 0.25, "trayectoria": 0.40, "acceso": 0.15, "competencia": 0.10, "economico": 0.10},
    "acceso_alto": {"demanda": 0.30, "trayectoria": 0.20, "acceso": 0.30, "competencia": 0.10, "economico": 0.10},
}

# Conector UN Comtrade (API pública de vista previa: 1 periodo y 500 filas por consulta)
COMTRADE_BASE_URL = os.getenv("COMTRADE_BASE_URL", "https://comtradeapi.un.org/public/v1/preview")
COMTRADE_REFERENCE_URL = "https://comtradeapi.un.org/files/v1/app/reference"
COMTRADE_PAUSA_SEG = float(os.getenv("COMTRADE_PAUSA_SEG", "1.5"))
# Cantidad de mercados (por valor importado) para los que se descarga el desglose de proveedores
COMTRADE_TOP_MERCADOS = int(os.getenv("COMTRADE_TOP_MERCADOS", "60"))

CODIGO_COMTRADE_PERU = 604
