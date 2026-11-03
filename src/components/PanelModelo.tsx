"use client";

import { useModelo, useSensibilidad } from "@/hooks/useDss";
import { NOMBRE_MODELO, pct } from "@/lib/formato";
import type { Protocolo } from "@/types/dss";
import { BarrasH } from "./Graficos";

const METRICAS: [keyof NonNullable<Protocolo["metricas"]>[string], string][] = [
  ["roc_auc", "AUC-ROC"], ["pr_auc", "AUC-PR"], ["accuracy", "Exactitud"], ["balanced_accuracy", "Exact. balanceada"],
  ["f1", "F1"], ["precision", "Precisión"], ["recall", "Sensibilidad"], ["brier", "Brier ↓"],
];

// JSONB (PostgreSQL) no conserva el orden de las claves: el orden de presentación se fija aquí
const ORDEN_MODELOS = ["regla_estatica", "regresion_logistica", "random_forest", "xgboost"];

const VARIANTES: Record<string, string> = {
  pesos_iguales: "Pesos iguales",
  pesos_demanda_alta: "Énfasis en demanda",
  pesos_trayectoria_alta: "Énfasis en trayectoria",
  pesos_acceso_alto: "Énfasis en acceso",
  normalizacion_percentil: "Normalización por percentiles",
};

function TablaProtocolo({ titulo, p, nota }: { titulo: string; p?: Protocolo; nota: string }) {
  if (!p) return null;
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-slate-100">{titulo}</h2>
        <p className="text-xs text-slate-400">
          Entrenamiento: cortes {p.cortes_entrenamiento.join(", ")} ({p.n_entrenamiento} relaciones, abandono {pct(p.tasa_abandono_entrenamiento)}) ·
          Prueba: corte {p.corte_prueba} ({p.n_prueba} relaciones, abandono {pct(p.tasa_abandono_prueba)}). {nota}
        </p>
      </div>
      {p.omitido ? (
        <p className="text-sm text-amber-200">{p.omitido.join(" ")}</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-xs tabular-nums">
              <thead className="text-slate-400">
                <tr><th className="text-left font-normal py-1">Modelo</th>{METRICAS.map(([, n]) => <th key={n} className="text-right font-normal px-2">{n}</th>)}</tr>
              </thead>
              <tbody>
                {ORDEN_MODELOS.filter((k) => p.metricas?.[k]).map((modelo) => [modelo, p.metricas![modelo]] as const).map(([modelo, m]) => (
                  <tr key={modelo} className={`border-t border-slate-800 ${modelo === p.mejor_modelo ? "text-slate-50 font-semibold" : "text-slate-300"}`}>
                    <td className="py-1.5">{NOMBRE_MODELO[modelo] ?? modelo}{modelo === p.mejor_modelo && " ★"}</td>
                    {METRICAS.map(([k]) => <td key={k} className="text-right px-2">{m[k].toFixed(3)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            {Object.entries(p.contrastes ?? {}).map(([nombre, c]) => {
              const [a, b] = nombre.split("_vs_");
              return (
                <div key={nombre} className="rounded-lg bg-slate-900 p-3 text-xs text-slate-300 space-y-1">
                  <div className="font-semibold text-slate-100">{NOMBRE_MODELO[a]} vs {NOMBRE_MODELO[b]}</div>
                  <div>ΔAUC = {c.auc.dif_auc.toFixed(3)} (IC95% bootstrap {c.auc.ic95[0].toFixed(3)} a {c.auc.ic95[1].toFixed(3)}; p = {c.auc.p_unilateral.toFixed(3)})</div>
                  <div>McNemar: solo {NOMBRE_MODELO[a]} acierta {c.mcnemar.solo_a_acierta}, solo {NOMBRE_MODELO[b]} acierta {c.mcnemar.solo_b_acierta}; p = {c.mcnemar.p_valor.toFixed(4)}</div>
                </div>
              );
            })}
          </div>
          {p.importancia_permutacion && (
            <div>
              <h3 className="text-xs font-semibold text-slate-400 mb-2">Importancia por permutación ({NOMBRE_MODELO[p.mejor_modelo ?? ""]}, caída de AUC en prueba)</h3>
              <BarrasH
                datos={Object.entries(p.importancia_permutacion).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([v, imp]) => ({ etiqueta: v, valor: Math.max(imp, 0) }))}
                formato={(v) => (v == null ? "—" : v.toFixed(4))}
              />
            </div>
          )}
        </>
      )}
    </section>
  );
}

export function PanelModelo({ sa6 }: { sa6: string }) {
  const { data: modelo, error: errModelo } = useModelo(sa6);
  const { data: sens, error: errSens } = useSensibilidad(sa6);

  return (
    <div className="space-y-6">
      {errModelo && <p className="text-sm text-red-300">Modelo: {errModelo.message}</p>}
      {modelo && (
        <>
          <p className="text-xs text-slate-400">
            Subpartida {modelo.sa6} · entrenado {modelo.entrenado_en.replace("T", " ")} · etiqueta: sin envíos durante {modelo.horizonte_meses} meses
            después del corte · modelo en producción: {NOMBRE_MODELO[modelo.modelo_produccion?.nombre ?? ""] ?? "—"}.
          </p>
          {modelo.omitido && <p className="text-sm text-amber-200">{modelo.omitido}</p>}
          <TablaProtocolo titulo="Protocolo estricto (validación temporal sin fuga de información)" p={modelo.protocolo_estricto}
            nota="Solo se entrena con cortes cuyo horizonte de 24 meses terminó antes del corte de prueba." />
          <TablaProtocolo titulo="Protocolo relajado (contraste)" p={modelo.protocolo_relajado}
            nota="Usa todos los cortes previos; sus etiquetas incluyen meses posteriores al corte de prueba." />
        </>
      )}

      {errSens && <p className="text-sm text-red-300">Sensibilidad: {errSens.message}</p>}
      {sens && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-slate-100">Análisis de sensibilidad del ranking ({sens.n_mercados} mercados con puntaje)</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs tabular-nums">
              <thead className="text-slate-400">
                <tr>
                  <th className="text-left font-normal py-1">Variante frente a pesos SRS</th>
                  <th className="text-right font-normal px-2">Spearman ρ</th>
                  <th className="text-right font-normal px-2">Cambio medio de posición</th>
                  <th className="text-right font-normal px-2">Cambio máximo</th>
                  <th className="text-right font-normal px-2">Permanencia top {sens.top_n}</th>
                </tr>
              </thead>
              <tbody className="text-slate-300">
                {Object.entries(sens.variantes).map(([k, v]) => (
                  <tr key={k} className="border-t border-slate-800">
                    <td className="py-1.5">{VARIANTES[k] ?? k}</td>
                    <td className="text-right px-2">{v.spearman.toFixed(3)}</td>
                    <td className="text-right px-2">{v.cambio_medio_posiciones.toFixed(1)}</td>
                    <td className="text-right px-2">{v.cambio_max_posiciones}</td>
                    <td className="text-right px-2">{v[`permanencia_top${sens.top_n}_pct`]}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-400">
            Mercados que permanecen en el top {sens.top_n} en todas las variantes: {sens.mercados_siempre_en_top.join(", ") || "ninguno"}.
          </p>
        </section>
      )}
    </div>
  );
}
