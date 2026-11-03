"use client";

import { useMemo, useState } from "react";
import { useProductos, useViabilidad } from "@/hooks/useDss";
import { DIMENSIONES, ESTADO_EVALUACION, pct, score as fmtScore, usd } from "@/lib/formato";
import type { Mercado } from "@/types/dss";
import { WorldMap } from "./WorldMap";
import { FichaMercado } from "./FichaMercado";
import { InsigniaRiesgo } from "./Graficos";
import { SimuladorPesos } from "./SimuladorPesos";

const ESCENARIOS: Record<string, string> = {
  srs: "Pesos del SRS (35/25/15/15/10)",
  iguales: "Pesos iguales (20% c/u)",
  demanda_alta: "Énfasis en demanda",
  trayectoria_alta: "Énfasis en trayectoria",
  acceso_alto: "Énfasis en acceso",
};

const select = "bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100";

function Kpi({ titulo, valor, detalle }: { titulo: string; valor: string; detalle?: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="text-xs text-slate-400">{titulo}</div>
      <div className="text-2xl font-bold text-slate-50 tabular-nums mt-1">{valor}</div>
      {detalle && <div className="text-xs text-slate-500 mt-1">{detalle}</div>}
    </div>
  );
}

export function Dashboard() {
  const { data: productos } = useProductos();
  const [sa6, setSa6] = useState("611019");
  const [escenario, setEscenario] = useState("srs");
  const [tipo, setTipo] = useState<"todos" | "con_presencia" | "potencial">("todos");
  const [seleccionado, setSeleccionado] = useState<string | null>(null);
  const { data, error, isLoading } = useViabilidad(sa6, escenario);

  const mercados = useMemo(
    () => (data?.mercados ?? []).filter((m) => tipo === "todos" || m.tipo_mercado === tipo),
    [data, tipo],
  );
  const conScore = mercados.filter((m) => m.score != null);
  const subpartidas = productos?.flatMap((p) => p.subpartidas.map((s) => ({ ...s, prenda: p.nombre }))) ?? [];

  return (
    <div className="space-y-6">
      {/* Filtros: una sola fila sobre los gráficos */}
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Prenda / subpartida SA
          <select className={select} value={sa6} onChange={(e) => { setSa6(e.target.value); setSeleccionado(null); }}>
            {subpartidas.length === 0 && <option value="611019">611019 · Chompas de pelo fino</option>}
            {subpartidas.map((s) => (
              <option key={s.sa6} value={s.sa6} disabled={!s.tiene_indice}>
                {s.prenda} · {s.sa6} {s.tiene_indice ? "" : "(sin datos cargados)"}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Ponderación
          <select className={select} value={escenario} onChange={(e) => setEscenario(e.target.value)}>
            {Object.entries(ESCENARIOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <div className="flex flex-col gap-1 text-xs text-slate-400">
          Mercados
          <div className="flex rounded-lg border border-slate-700 overflow-hidden">
            {(["todos", "con_presencia", "potencial"] as const).map((t) => (
              <button key={t} onClick={() => setTipo(t)}
                className={`px-3 py-2 text-sm ${tipo === t ? "bg-blue-600 text-white" : "bg-slate-900 text-slate-300 hover:bg-slate-800"}`}>
                {t === "todos" ? "Todos" : t === "con_presencia" ? "Con presencia" : "Potenciales"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <div className="rounded-lg border border-red-800 bg-red-950/40 p-4 text-sm text-red-200">No se pudo consultar la API del DSS: {error.message}. Verifique que el backend esté activo en el puerto 8000.</div>}
      {isLoading && <div className="text-sm text-slate-400">Calculando viabilidad…</div>}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Kpi titulo="Mercados evaluados" valor={String(conScore.length)} detalle={`de ${mercados.length} con datos`} />
            <Kpi titulo="Con presencia peruana" valor={String(data.resumen.con_presencia)} detalle="exportaciones 2021–2025" />
            <Kpi titulo="Mercados potenciales" valor={String(data.resumen.potenciales)} detalle="importan, sin envíos peruanos" />
            <Kpi titulo="Mejor mercado" valor={conScore[0]?.nombre ?? "—"} detalle={conScore[0] ? `Score ${fmtScore(conScore[0].score)}` : undefined} />
          </div>

          {data.nota_agregacion && (
            <p className="text-xs text-slate-500">
              {data.sa6} · {data.descripcion}. {data.nota_agregacion} Demanda: UN Comtrade {data.anio_referencia}; trayectoria: PROMPERÚ {data.periodo}.
            </p>
          )}

          <div className={`grid gap-6 ${seleccionado ? "lg:grid-cols-[1fr_420px]" : ""}`}>
            <div className="space-y-6 min-w-0">
              <WorldMap mercados={mercados} seleccionado={seleccionado} onSelect={setSeleccionado} />
              <Ranking mercados={mercados} seleccionado={seleccionado} onSelect={setSeleccionado} />
            </div>
            {seleccionado && (
              <aside className="rounded-xl border border-slate-800 bg-slate-900/70 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:sticky lg:top-4">
                <FichaMercado sa6={sa6} iso3={seleccionado} onClose={() => setSeleccionado(null)} />
              </aside>
            )}
          </div>

          <SimuladorPesos sa6={sa6} onSelect={setSeleccionado} />
        </>
      )}
    </div>
  );
}

function Ranking({ mercados, seleccionado, onSelect }: { mercados: Mercado[]; seleccionado: string | null; onSelect: (iso: string) => void }) {
  const [verTodos, setVerTodos] = useState(false);
  const filas = verTodos ? mercados : mercados.slice(0, 15);
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="text-left px-4 pt-4 pb-2 text-sm font-semibold text-slate-200">Ranking de mercados por Índice de Atractivo Comercial</caption>
        <thead className="text-xs text-slate-400">
          <tr className="border-b border-slate-800">
            <th className="text-left px-4 py-2 font-normal">#</th>
            <th className="text-left px-2 py-2 font-normal">Mercado</th>
            <th className="text-left px-2 py-2 font-normal w-48">Score</th>
            {DIMENSIONES.map((d) => <th key={d.clave} className="text-right px-2 py-2 font-normal hidden xl:table-cell">{d.nombre.split(" ")[0]}</th>)}
            <th className="text-right px-2 py-2 font-normal hidden md:table-cell">Importaciones</th>
            <th className="text-right px-2 py-2 font-normal hidden md:table-cell">Cuota Perú</th>
            <th className="text-left px-4 py-2 font-normal">Riesgo de abandono</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((m) => (
            <tr key={m.iso3} onClick={() => onSelect(m.iso3)}
              className={`border-b border-slate-800/60 cursor-pointer hover:bg-slate-800/50 ${seleccionado === m.iso3 ? "bg-slate-800/70" : ""}`}>
              <td className="px-4 py-2 text-slate-400 tabular-nums">{m.ranking ?? "—"}</td>
              <td className="px-2 py-2">
                <div className="text-slate-100">{m.nombre}</div>
                <div className="text-[11px] text-slate-500">{m.tipo_mercado === "potencial" ? "Potencial" : "Con presencia"}{m.estado !== "completa" && ` · ${ESTADO_EVALUACION[m.estado]}`}</div>
              </td>
              <td className="px-2 py-2">
                <div className="flex items-center gap-2">
                  <span className="w-10 text-right tabular-nums text-slate-100">{fmtScore(m.score)}</span>
                  <span className="flex-1 h-2 rounded bg-slate-800">
                    {m.score != null && <span className="block h-2 rounded bg-[#3987e5]" style={{ width: `${m.score}%` }} />}
                  </span>
                </div>
              </td>
              {DIMENSIONES.map((d) => (
                <td key={d.clave} className="px-2 py-2 text-right tabular-nums text-slate-300 hidden xl:table-cell">
                  {m.dimensiones[d.clave] == null ? "—" : (m.dimensiones[d.clave]! * 100).toFixed(0)}
                </td>
              ))}
              <td className="px-2 py-2 text-right tabular-nums text-slate-300 hidden md:table-cell">{usd(m.v_imp)}</td>
              <td className="px-2 py-2 text-right tabular-nums text-slate-300 hidden md:table-cell">{pct(m.s_peru, 2)}</td>
              <td className="px-4 py-2"><InsigniaRiesgo riesgo={m.riesgo_abandono} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      {mercados.length > 15 && (
        <button onClick={() => setVerTodos(!verTodos)} className="w-full py-2 text-xs text-blue-300 hover:bg-slate-800/50">
          {verTodos ? "Ver solo los 15 primeros" : `Ver los ${mercados.length} mercados`}
        </button>
      )}
    </div>
  );
}
