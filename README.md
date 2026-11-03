# DSS de Viabilidad Comercial Textil

Sistema de Soporte a la Decisión para seleccionar mercados de exportación de prendas de alpaca y
lana (chompas, chalinas, ponchos, gorros y guantes). Implementa el artículo *Plataforma de Análisis
de Viabilidad Comercial para Proyectos de Exportación en el Sector Textil* y la especificación
`especificaciones_tecnicas_dss.pdf` (SRS).

```
PROMPERÚ/SUNAT (Excel) ─┐                         ┌─> Índice I(p,c) + sensibilidad ─┐
UN Comtrade (API)  ─────┼─> ETL Python ─> PostgreSQL 16 (copo de nieve)             ├─> FastAPI /api/v1 ─> Next.js (mapa, ranking, fichas)
MINCETUR (TLC, CSV) ────┘   (limpieza,             └─> Modelo de abandono (RF/XGB) ─┘
                             homologación SA)
```

| Requerimiento | Implementación |
|---|---|
| RF-01 Ingesta OGD | `backend/dss/etl/promperu.py` (embarques), `backend/dss/etl/comtrade.py` (API UN Comtrade con caché de archivos crudos) |
| RF-02 Homologación SA | `backend/dss/catalog.py`, tabla `dim_subpartida_nacional` (10 → 6 dígitos) |
| RF-03 Copo de nieve | `backend/dss/models.py`: `fact_exportaciones`, `fact_comercio_mundial`, `dim_tiempo`, `dim_pais → dim_region`, `dim_producto → dim_prenda`, `dim_empresa`, `dim_regulaciones` |
| RF-04 Predictor | `backend/dss/ml/` (Random Forest, XGBoost; líneas base estática y logística) |
| RF-05 Dashboard | Next.js: `/` mapa de calor + ranking + ficha de mercado + what-if de pesos, `/modelo`, `/servicio` |
| RF-06 Servicio y calidad | tablas `etl_ejecucion`, `calidad_datos`; página `/servicio`; latencia por endpoint |
| RNF-01 Latencia < 2.5 s | medida en cada respuesta (`X-Response-Time-ms`) y reportada en `/api/v1/servicio/estado` |
| RNF-03 API REST JSON | FastAPI, Swagger en `http://localhost:8000/docs` |
| RNF-04 Calidad de datos | reglas de recuperación, deduplicación, acotamiento de atípicos (p5–p95) |

## Puesta en marcha

### Con Docker (PostgreSQL 16 + API + web)

```bash
docker compose up -d db api web
docker compose run --rm etl          # primera carga (descarga UN Comtrade; ~5-10 min por límites de la API)
```

Abrir http://localhost:3000. Para recargar los datos periódicamente (cron del servidor):
`0 3 * * 1 cd /ruta/IMPORT_TEXTIL && docker compose run --rm etl`.

### Desarrollo local (sin Docker)

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m dss.pipeline                # sin DATABASE_URL usa SQLite local (backend/dss_local.db)
uvicorn dss.api.main:app --reload     # http://localhost:8000/docs
python -m pytest

cd ..
npm install
npm run dev                           # http://localhost:3000 (reenvía /api/v1 a localhost:8000)
```

Opciones del pipeline: `--sin-api` (usa solo la caché de Comtrade), `--productos todos` (descarga la
demanda de las 7 subpartidas del catálogo).

## Datos

| Archivo | Uso |
|---|---|
| `backend/data/raw/promperu/Exportaciones.xlsx` | Embarques 2021–2025 de la subpartida 6110.19.10.90 + hoja de exportaciones peruanas en Comtrade |
| `backend/data/raw/comtrade/*.json` | Respuestas originales de UN Comtrade (trazabilidad; no se vuelven a descargar) |
| `backend/data/raw/sunat/cdro_*.xlsx` | Cuadros SUNAT 2023–2024 (referencia para contrastar agregados) |
| `backend/data/reference/acceso_mercado.csv` | TLC vigentes del Perú. **Pendiente**: aranceles NMF/preferenciales y NTMs desde Market Access Map; `verificado=false` hasta revisarlo |
| `backend/data/reference/costos_escenarios.csv`, `fletes_region.csv` | **Supuestos sintéticos** para los escenarios económicos; reemplazar por costos reales |

### Problemas de la fuente corregidos en el ETL

1. Fechas mezcladas (texto `dd/mm/aaaa` en ene–jun y fecha Excel en jul–dic) → normalizadas.
2. Montos FOB y pesos convertidos en fechas por la configuración regional de Excel
   (`2125.4` → 01/04/2125; `26.5` → 26/05/2026) → reconstruidos; validado porque el USD/unidad de
   los montos recuperados coincide con el de los montos íntegros.
3. Pesos con tres decimales leídos como miles (`15.351` kg → 15351) → divididos entre 1000 cuando
   superan 20 kg por prenda.

Cada registro corregido conserva su bandera (`fob_recuperado`, `peso_corregido`) y los conteos se
guardan en `calidad_datos`.

## Método

**Índice de Atractivo Comercial** (SRS §3): `I(p,c) = 100 × Σ wᵢ·zᵢ(p,c)`, con pesos 0.35 demanda,
0.25 trayectoria, 0.15 acceso, 0.15 competencia, 0.10 económico. `zᵢ` es min-max orientado
(mayor = más favorable) tras acotar atípicos a p5–p95. Mercados sin exportaciones peruanas
(potenciales) se evalúan sin trayectoria, renormalizando pesos. Sin demanda → `incompleta`
(sin puntaje). Requisito obligatorio incumplible → `no_elegible`.

**Abandono**: relación sin exportaciones durante 24 meses consecutivos tras una operación,
declarado solo si el intervalo completo es observable.

**Modelo**: unidad = relación empresa–país activa en una fecha de corte; variables con información
hasta el corte; etiqueta = sin envíos en los 24 meses siguientes. Validación temporal estricta
(solo se entrena con cortes cuya etiqueta ya cerró antes del corte de prueba), comparación con una
regla estática y una regresión logística, IC bootstrap del ΔAUC y prueba de McNemar. Las métricas
se guardan en `backend/artifacts/metricas_modelo_<sa6>.json` y en `/api/v1/modelo/<sa6>`.

**Sensibilidad**: ranking recalculado con pesos iguales, énfasis por dimensión y normalización por
percentiles; se reporta ρ de Spearman, cambio de posiciones y permanencia en el top 10.
