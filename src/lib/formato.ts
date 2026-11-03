import type { Dimension } from "@/types/dss";

export const DIMENSIONES: { clave: Dimension; nombre: string }[] = [
  { clave: "demanda", nombre: "Demanda internacional" },
  { clave: "trayectoria", nombre: "Trayectoria exportadora" },
  { clave: "acceso", nombre: "Acceso al mercado" },
  { clave: "competencia", nombre: "Competencia" },
  { clave: "economico", nombre: "Resultado económico" },
];

const compacto = new Intl.NumberFormat("es-PE", { notation: "compact", maximumFractionDigits: 1 });
const entero = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 0 });

export const usd = (v: number | null | undefined) => (v == null ? "—" : `US$ ${compacto.format(v)}`);
export const num = (v: number | null | undefined) => (v == null ? "—" : entero.format(v));
export const pct = (v: number | null | undefined, decimales = 1) =>
  v == null ? "—" : `${(v * 100).toFixed(decimales)}%`;
export const score = (v: number | null | undefined) => (v == null ? "—" : v.toFixed(1));

export const ESTADO_EVALUACION: Record<string, string> = {
  completa: "Evaluación completa",
  parcial: "Evaluación parcial",
  incompleta: "Información crítica faltante",
  no_elegible: "No elegible",
};

export const ESTADO_CONTINUIDAD: Record<string, string> = {
  continuo: "Continuo",
  en_observacion: "En observación (12–23 meses sin envíos)",
  abandono: "Posible abandono (≥24 meses)",
  reingreso: "Reingreso tras abandono",
  sin_presencia: "Sin exportaciones peruanas",
};

export const NOMBRE_MODELO: Record<string, string> = {
  regla_estatica: "Regla estática (actividad)",
  regresion_logistica: "Regresión logística",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
};
