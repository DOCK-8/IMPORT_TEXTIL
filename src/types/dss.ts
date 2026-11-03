// Contratos de la API REST del DSS (backend FastAPI, /api/v1)

export type Dimension = "demanda" | "trayectoria" | "acceso" | "competencia" | "economico";
export type Pesos = Record<Dimension, number>;
export type EstadoEvaluacion = "completa" | "parcial" | "incompleta" | "no_elegible";

export interface Riesgo {
  probabilidad: number;
  clase: "bajo" | "medio" | "alto";
  n_relaciones: number;
  modelo: string;
}

export interface Mercado {
  iso3: string;
  nombre: string;
  region: string | null;
  score: number | null;
  ranking: number | null;
  estado: EstadoEvaluacion;
  tipo_mercado: "con_presencia" | "potencial";
  dimensiones: Record<Dimension, number | null>;
  faltantes: Dimension[];
  v_imp: number | null;
  cagr: number | null;
  s_peru: number | null;
  hhi: number | null;
  tlc: number | null;
  acuerdo: string | null;
  fob_peru_total: number | null;
  n_empresas: number | null;
  recencia_meses: number | null;
  estado_continuidad: string | null;
  margen_pct: number | null;
  riesgo_abandono: Riesgo | null;
}

export interface ViabilidadResponse {
  sa6: string;
  descripcion: string;
  nota_agregacion: string | null;
  escenario: string;
  pesos: Pesos;
  anio_referencia: number | null;
  periodo: string;
  calculado_en: string | null;
  resumen: { mercados: number; con_presencia: number; potenciales: number; por_estado: Record<string, number> };
  mercados: Mercado[];
}

export interface Subpartida {
  sa6: string;
  descripcion: string;
  nacionales: string[];
  nota_agregacion: string | null;
  registros_exportacion: number;
  tiene_indice: boolean;
}

export interface Prenda {
  codigo: string;
  nombre: string;
  subpartidas: Subpartida[];
}

export interface EscenarioEconomico {
  escenario: string;
  incoterm: string;
  precio_usd_unidad: number;
  costos_usd_unidad: Record<string, number>;
  costo_total_usd_unidad: number;
  margen_usd_unidad: number;
  margen_pct: number | null;
  margen_envio_usd: number;
  datos: string;
}

export interface FichaMercado extends Mercado {
  sa6: string;
  producto: string;
  nota_agregacion: string | null;
  subindicadores: Record<string, number | null>;
  indicadores: Record<string, unknown> & {
    imp_anual?: Record<string, number>;
    fob_peru_anual?: Record<string, number>;
    top_proveedores?: Record<string, number>;
    n_proveedores?: number | null;
    principal_proveedor?: string | null;
    actividad_pct?: number;
    meses_activos?: number;
    max_intervalo_meses?: number | null;
    episodios?: number;
    precio_unitario?: number | null;
    fuente_precio?: string | null;
    fuente_s_peru?: string | null;
    acceso_verificado?: boolean;
    yoy?: number | null;
  };
  serie_mensual: { mes: string; fob_usd: number; envios: number; empresas: number }[];
  escenarios_economicos: EscenarioEconomico[];
  fuentes: Record<string, string | null>;
}

export interface EstadoServicio {
  salud: { estado: string; base_datos: string; iniciado: string };
  ejecuciones: {
    id: number;
    inicio: string;
    fin: string | null;
    duracion_seg: number | null;
    estado: string;
    pasos: { paso: string; segundos: number; registros?: number }[];
    mensaje: string | null;
  }[];
  calidad: { fuente: string; metrica: string; valor: number; detalle: string | null }[];
  latencias: Record<string, { n: number; p50_ms: number; p95_ms: number; cumple_rnf01: boolean }>;
  umbral_latencia_ms: number;
}

export interface MetricasModelo {
  roc_auc: number;
  pr_auc: number;
  accuracy: number;
  balanced_accuracy: number;
  f1: number;
  precision: number;
  recall: number;
  brier: number;
  umbral: number;
}

export interface Protocolo {
  cortes_entrenamiento: string[];
  corte_prueba: string;
  n_entrenamiento: number;
  n_prueba: number;
  tasa_abandono_entrenamiento: number | null;
  tasa_abandono_prueba: number | null;
  omitido?: string[];
  metricas?: Record<string, MetricasModelo>;
  mejor_modelo?: string;
  contrastes?: Record<string, {
    auc: { dif_auc: number; ic95: [number, number]; p_unilateral: number };
    mcnemar: { solo_a_acierta: number; solo_b_acierta: number; p_valor: number };
  }>;
  importancia_permutacion?: Record<string, number>;
}

export interface ReporteModelo {
  sa6: string;
  entrenado_en: string;
  horizonte_meses: number;
  cortes_etiquetables: string[];
  protocolo_estricto?: Protocolo;
  protocolo_relajado?: Protocolo;
  modelo_produccion?: { nombre: string; n_entrenamiento: number; corte_prediccion: string };
  omitido?: string;
}

export interface Sensibilidad {
  sa6: string;
  calculado_en: string;
  n_mercados: number;
  top_n: number;
  variantes: Record<string, Record<string, number>>;
  mercados_siempre_en_top: string[];
  rango_posiciones: Record<string, { min: number; max: number }>;
}
