"use client";

import { useEstadoServicio } from "@/hooks/useDss";

const ESTADO: Record<string, { color: string; icono: string; texto: string }> = {
  ok: { color: "#0ca30c", icono: "●", texto: "Operativo" },
  exitoso: { color: "#0ca30c", icono: "●", texto: "Exitoso" },
  en_curso: { color: "#fab219", icono: "▲", texto: "En curso" },
  degradado: { color: "#fab219", icono: "▲", texto: "Degradado" },
  fallido: { color: "#d03b3b", icono: "■", texto: "Fallido" },
  interrumpido: { color: "#d03b3b", icono: "■", texto: "Interrumpido" },
};

function Estado({ valor }: { valor: string }) {
  const e = ESTADO[valor] ?? { color: "#94a3b8", icono: "○", texto: valor };
  return <span className="inline-flex items-center gap-1.5"><span style={{ color: e.color }} aria-hidden>{e.icono}</span>{e.texto}</span>;
}

export function PanelServicio() {
  const { data, error } = useEstadoServicio();
  if (error) return <p className="text-sm text-red-300">API no disponible: {error.message}</p>;
  if (!data) return <p className="text-sm text-slate-400">Consultando estado…</p>;
  const ultima = data.ejecuciones[0];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs text-slate-400">API y base de datos</div>
          <div className="mt-1 text-slate-100"><Estado valor={data.salud.estado} /></div>
          <div className="text-xs text-slate-500 mt-1">BD: {data.salud.base_datos} · activo desde {data.salud.iniciado.replace("T", " ")}</div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs text-slate-400">Última carga ETL</div>
          <div className="mt-1 text-slate-100">{ultima ? <Estado valor={ultima.estado} /> : "Sin ejecuciones"}</div>
          {ultima && <div className="text-xs text-slate-500 mt-1">#{ultima.id} · {ultima.inicio.replace("T", " ")} · {ultima.duracion_seg ?? "—"} s</div>}
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs text-slate-400">Latencia p95 (umbral RNF-01: {data.umbral_latencia_ms} ms)</div>
          <div className="mt-1 text-slate-100 tabular-nums">
            {Object.keys(data.latencias).length
              ? `${Math.max(...Object.values(data.latencias).map((l) => l.p95_ms)).toFixed(0)} ms (peor endpoint)`
              : "Sin mediciones aún"}
          </div>
        </div>
      </div>

      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="text-sm font-semibold text-slate-100 mb-3">Controles de calidad de datos (última carga exitosa)</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="text-slate-400"><tr><th className="text-left font-normal py-1">Fuente</th><th className="text-left font-normal">Control</th><th className="text-right font-normal px-2">Valor</th><th className="text-left font-normal px-2">Detalle</th></tr></thead>
            <tbody className="text-slate-300">
              {data.calidad.map((c, i) => (
                <tr key={i} className="border-t border-slate-800">
                  <td className="py-1.5 pr-2">{c.fuente}</td>
                  <td className="pr-2">{c.metrica.replaceAll("_", " ")}</td>
                  <td className="text-right px-2 tabular-nums">{Number.isInteger(c.valor) ? c.valor.toLocaleString("es-PE") : c.valor.toFixed(2)}</td>
                  <td className="px-2 text-slate-500">{c.detalle}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid lg:grid-cols-2 gap-6">
        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h2 className="text-sm font-semibold text-slate-100 mb-3">Ejecuciones del pipeline</h2>
          <ul className="space-y-3 text-xs">
            {data.ejecuciones.map((e) => (
              <li key={e.id} className="border-t border-slate-800 pt-2">
                <div className="flex justify-between text-slate-200"><span>#{e.id} · {e.inicio.replace("T", " ")}</span><Estado valor={e.estado} /></div>
                <div className="text-slate-500">{e.pasos.length} pasos · {e.duracion_seg ?? "—"} s</div>
                {e.mensaje && <pre className="mt-1 whitespace-pre-wrap text-red-300">{e.mensaje}</pre>}
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h2 className="text-sm font-semibold text-slate-100 mb-3">Latencia por endpoint</h2>
          <table className="w-full text-xs tabular-nums">
            <thead className="text-slate-400"><tr><th className="text-left font-normal py-1">Endpoint</th><th className="text-right font-normal">n</th><th className="text-right font-normal">p50</th><th className="text-right font-normal">p95</th><th className="text-right font-normal">RNF-01</th></tr></thead>
            <tbody className="text-slate-300">
              {Object.entries(data.latencias).map(([ruta, l]) => (
                <tr key={ruta} className="border-t border-slate-800">
                  <td className="py-1.5 font-mono">{ruta}</td><td className="text-right">{l.n}</td>
                  <td className="text-right">{l.p50_ms} ms</td><td className="text-right">{l.p95_ms} ms</td>
                  <td className="text-right"><Estado valor={l.cumple_rnf01 ? "ok" : "fallido"} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}
