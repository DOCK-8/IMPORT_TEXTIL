"use client";

import { useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography, Graticule, Sphere, ZoomableGroup } from "react-simple-maps";
import { Tooltip } from "react-tooltip";
import { scaleQuantize } from "d3-scale";
import { getAlpha3Code } from "@/lib/geoUtils";
import { ESTADO_EVALUACION, score as fmtScore } from "@/lib/formato";
import type { Mercado } from "@/types/dss";

const GEO_URL = "/world-110m.json";

// Rampa secuencial azul (paso 650 -> 150): en fondo oscuro el valor bajo se funde con la superficie
export const RAMPA = ["#104281", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"];
const SIN_PUNTAJE = "#475569";
const FUERA_DE_UNIVERSO = "#1e293b";

interface Props {
  mercados: Mercado[];
  seleccionado: string | null;
  onSelect: (iso3: string) => void;
}

export function WorldMap({ mercados, seleccionado, onSelect }: Props) {
  const [hover, setHover] = useState<{ nombre: string; mercado?: Mercado } | null>(null);
  const porIso = useMemo(() => new Map(mercados.map((m) => [m.iso3, m])), [mercados]);
  const color = useMemo(() => scaleQuantize<string>().domain([0, 100]).range(RAMPA), []);

  return (
    <div className="w-full">
      <div className="relative w-full aspect-[1.9/1] rounded-xl border border-slate-800 bg-slate-950 overflow-hidden">
        <ComposableMap projectionConfig={{ rotate: [-10, 0, 0], scale: 147 }} className="w-full h-full">
          <ZoomableGroup zoom={1} minZoom={0.8} maxZoom={6}>
            <Sphere id="esfera" stroke="#1e293b" strokeWidth={0.5} fill="transparent" />
            <Graticule stroke="#1e293b" strokeWidth={0.3} />
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const nombreGeo = (geo.properties?.name as string | undefined) ?? "—";
                  const iso3 = getAlpha3Code(geo.id !== undefined ? String(geo.id) : "", nombreGeo);
                  const m = porIso.get(iso3);
                  const fill = !m ? FUERA_DE_UNIVERSO : m.score == null ? SIN_PUNTAJE : color(m.score);
                  const activo = seleccionado === iso3;
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      data-tooltip-id="mapa-tooltip"
                      fill={fill}
                      stroke={activo ? "#f8fafc" : "#0f172a"}
                      strokeWidth={activo ? 1.5 : 0.5}
                      className={`outline-none hover:stroke-slate-50 hover:stroke-[1.2px] ${m ? "cursor-pointer" : ""}`}
                      onMouseEnter={() => setHover({ nombre: m?.nombre ?? nombreGeo, mercado: m })}
                      onMouseLeave={() => setHover(null)}
                      onClick={() => m && onSelect(iso3)}
                    />
                  );
                })
              }
            </Geographies>
          </ZoomableGroup>
        </ComposableMap>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span>Exporting Score</span>
          <span>0</span>
          <span className="flex">
            {RAMPA.map((c) => (
              <span key={c} className="inline-block w-6 h-3" style={{ background: c }} />
            ))}
          </span>
          <span>100</span>
        </div>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: SIN_PUNTAJE }} />
          Sin puntaje (información crítica faltante)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm border border-slate-700" style={{ background: FUERA_DE_UNIVERSO }} />
          Sin importaciones registradas
        </span>
      </div>

      <Tooltip id="mapa-tooltip" className="!bg-slate-900 !text-slate-100 !rounded-lg !border !border-slate-700 !opacity-100 z-50">
        {hover && (
          <div className="text-xs space-y-0.5">
            <div className="font-semibold text-sm">{hover.nombre}</div>
            {hover.mercado ? (
              <>
                <div>
                  Score <span className="font-semibold">{fmtScore(hover.mercado.score)}</span>
                  {hover.mercado.ranking != null && <span className="text-slate-400"> · puesto {hover.mercado.ranking}</span>}
                </div>
                <div className="text-slate-400">
                  {hover.mercado.tipo_mercado === "potencial" ? "Mercado potencial" : "Con presencia peruana"} ·{" "}
                  {ESTADO_EVALUACION[hover.mercado.estado]}
                </div>
                <div className="text-slate-500">Clic para ver la ficha</div>
              </>
            ) : (
              <div className="text-slate-400">Sin datos de importación</div>
            )}
          </div>
        )}
      </Tooltip>
    </div>
  );
}
