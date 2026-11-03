"use client";

import { useState } from "react";
import type { Riesgo } from "@/types/dss";

const SERIE = "#3987e5";

/** Barras horizontales de una sola serie; el valor se escribe en tinta de texto, no en el color de la barra. */
export function BarrasH({
  datos, max, formato, nota,
}: {
  datos: { etiqueta: string; valor: number | null; detalle?: string }[];
  max?: number;
  formato: (v: number | null) => string;
  nota?: (d: { etiqueta: string; valor: number | null }) => string | null;
}) {
  const tope = max ?? Math.max(...datos.map((d) => d.valor ?? 0), 1e-9);
  return (
    <ul className="space-y-2">
      {datos.map((d) => (
        <li key={d.etiqueta} className="group" title={d.detalle}>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-300">{d.etiqueta}</span>
            <span className="text-slate-100 tabular-nums">{d.valor == null ? (nota?.(d) ?? "No aplica") : formato(d.valor)}</span>
          </div>
          <div className="h-2 rounded bg-slate-800">
            {d.valor != null && (
              <div className="h-2 rounded" style={{ width: `${Math.max(0, Math.min(1, d.valor / tope)) * 100}%`, background: SERIE }} />
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Columnas por periodo con tooltip por columna (hit target de altura completa). */
export function Columnas({
  datos, formato, alto = 140,
}: {
  datos: { etiqueta: string; valor: number; extra?: string }[];
  formato: (v: number) => string;
  alto?: number;
}) {
  const [activo, setActivo] = useState<number | null>(null);
  const max = Math.max(...datos.map((d) => d.valor), 1e-9);
  const ancho = 100 / Math.max(datos.length, 1);
  const marcas = datos.map((d, i) => ({ ...d, i })).filter((d) => /-01$|^\d{4}$/.test(d.etiqueta));
  return (
    <div className="relative">
      <div className="absolute right-0 -top-1 text-xs text-slate-300 tabular-nums h-4">
        {activo != null ? `${datos[activo].etiqueta}: ${formato(datos[activo].valor)}${datos[activo].extra ? ` · ${datos[activo].extra}` : ""}` : ""}
      </div>
      <svg viewBox={`0 0 100 ${alto}`} preserveAspectRatio="none" className="w-full mt-4" style={{ height: alto }}
        onMouseLeave={() => setActivo(null)} role="img" aria-label="Serie por periodo">
        <line x1="0" x2="100" y1={alto - 0.5} y2={alto - 0.5} stroke="#334155" strokeWidth="1" vectorEffect="non-scaling-stroke" />
        {datos.map((d, i) => {
          const h = (d.valor / max) * (alto - 4);
          return (
            <g key={d.etiqueta} onMouseEnter={() => setActivo(i)}>
              <rect x={i * ancho} y={0} width={ancho} height={alto} fill="transparent" />
              {d.valor > 0 && (
                <rect x={i * ancho + ancho * 0.15} y={alto - h} width={ancho * 0.7} height={h} rx={0.6}
                  fill={SERIE} opacity={activo == null || activo === i ? 1 : 0.45} />
              )}
            </g>
          );
        })}
      </svg>
      <div className="relative h-4 text-[10px] text-slate-500">
        {marcas.map((m) => (
          <span key={m.etiqueta} className="absolute" style={{ left: `${m.i * ancho}%` }}>{m.etiqueta.slice(0, 4)}</span>
        ))}
      </div>
    </div>
  );
}

const RIESGO = {
  bajo: { color: "#0ca30c", icono: "●", texto: "Riesgo bajo" },
  medio: { color: "#fab219", icono: "▲", texto: "Riesgo medio" },
  alto: { color: "#d03b3b", icono: "■", texto: "Riesgo alto" },
} as const;

export function InsigniaRiesgo({ riesgo }: { riesgo: Riesgo | null }) {
  if (!riesgo) return <span className="text-xs text-slate-500">Sin predicción</span>;
  const r = RIESGO[riesgo.clase];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-200" title={`Modelo ${riesgo.modelo} · ${riesgo.n_relaciones} relaciones activas`}>
      <span style={{ color: r.color }} aria-hidden>{r.icono}</span>
      {r.texto} <span className="text-slate-400 tabular-nums">({(riesgo.probabilidad * 100).toFixed(0)}%)</span>
    </span>
  );
}
