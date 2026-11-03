"use client";

import { useState } from "react";
import { DIMENSIONES, score as fmtScore } from "@/lib/formato";
import type { Pesos } from "@/types/dss";

const SRS: Pesos = { demanda: 0.35, trayectoria: 0.25, acceso: 0.15, competencia: 0.15, economico: 0.1 };

interface Resultado {
  mercados: { iso3: string; nombre: string; score: number | null; ranking: number | null }[];
}

/** Análisis what-if: el usuario redefine las ponderaciones y el backend recalcula el ranking. */
export function SimuladorPesos({ sa6, onSelect }: { sa6: string; onSelect: (iso3: string) => void }) {
  const [pesos, setPesos] = useState<Pesos>(SRS);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [error, setError] = useState<string | null>(null);
  const suma = Object.values(pesos).reduce((a, b) => a + b, 0);
  const valida = Math.abs(suma - 1) < 1e-6;

  async function simular() {
    setError(null);
    const res = await fetch(`/api/v1/viabilidad/${sa6}/simular`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pesos),
    });
    if (!res.ok) {
      setError(`Error ${res.status}`);
      return;
    }
    setResultado(await res.json());
  }

  return (
    <details className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <summary className="cursor-pointer text-sm font-semibold text-slate-200">Ponderaciones personalizadas (análisis what-if)</summary>
      <div className="mt-4 grid md:grid-cols-[320px_1fr] gap-6">
        <div className="space-y-3">
          {DIMENSIONES.map((d) => (
            <label key={d.clave} className="block text-xs text-slate-300">
              <span className="flex justify-between"><span>{d.nombre}</span><span className="tabular-nums">{Math.round(pesos[d.clave] * 100)}%</span></span>
              <input type="range" min={0} max={100} step={5} value={Math.round(pesos[d.clave] * 100)}
                onChange={(e) => setPesos({ ...pesos, [d.clave]: Number(e.target.value) / 100 })}
                className="w-full accent-blue-500" />
            </label>
          ))}
          <div className={`text-xs ${valida ? "text-slate-400" : "text-amber-300"}`}>Suma: {Math.round(suma * 100)}% {valida ? "" : "(debe ser 100%)"}</div>
          <div className="flex gap-2">
            <button disabled={!valida} onClick={simular} className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm disabled:opacity-40">Recalcular</button>
            <button onClick={() => { setPesos(SRS); setResultado(null); }} className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 text-sm">Restablecer SRS</button>
          </div>
          {error && <p className="text-xs text-red-300">{error}</p>}
        </div>
        <div>
          {resultado ? (
            <ol className="text-sm space-y-1">
              {resultado.mercados.filter((m) => m.score != null).slice(0, 12).map((m) => (
                <li key={m.iso3} className="flex justify-between border-b border-slate-800/60 py-1 cursor-pointer hover:text-white text-slate-300" onClick={() => onSelect(m.iso3)}>
                  <span><span className="text-slate-500 tabular-nums mr-2">{m.ranking}</span>{m.nombre}</span>
                  <span className="tabular-nums">{fmtScore(m.score)}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-slate-500">Ajuste los pesos y pulse Recalcular para ver el nuevo orden de mercados.</p>
          )}
        </div>
      </div>
    </details>
  );
}
