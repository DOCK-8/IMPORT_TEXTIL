"use client";

import React, { useState, useMemo } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
  Sphere,
  Graticule,
} from "react-simple-maps";
import { Tooltip } from "react-tooltip";
import { scaleLinear } from "d3-scale";
import { useCountries } from "@/hooks/useCountries";
import { getAlpha3Code } from "@/lib/geoUtils";
import { CountryData } from "@/types/country";

// Ruta al geojson/topojson en local
const GEO_URL = "/world-110m.json";

interface TooltipContent {
  name: string;
  code: string;
  percentage: number;
  isCustom: boolean;
}

export function WorldMap() {
  const { countries, countryMap, defaultPercentage, isLoading, isError } = useCountries();
  const [tooltipContent, setTooltipContent] = useState<TooltipContent | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<CountryData | null>(null);

  // Escala de color basada en el porcentaje (0% -> Celeste, 50% -> Azul medio, 100% -> Azul profundo)
  const colorScale = useMemo(() => {
    return scaleLinear<string>()
      .domain([0, 50, 100])
      .range(["#60a5fa", "#2563eb", "#1e3a8a"]);
  }, []);

  return (
    <div className="w-full flex flex-col items-center">
      {/* Barra de estado / Indicador de datos */}
      <div className="w-full max-w-6xl mb-4 flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/60 backdrop-blur border border-slate-800 text-slate-200">
        <div className="flex items-center gap-3">
          <span className="relative flex h-3 w-3">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isLoading ? "bg-amber-400" : isError ? "bg-red-400" : "bg-emerald-400"
              }`}
            ></span>
            <span
              className={`relative inline-flex rounded-full h-3 w-3 ${
                isLoading ? "bg-amber-500" : isError ? "bg-red-500" : "bg-emerald-500"
              }`}
            ></span>
          </span>
          <span className="text-sm font-medium">
            {isLoading
              ? "Cargando métricas de países..."
              : isError
              ? "Modo sin conexión (datos por defecto)"
              : `${countries.length} países consultados`}
          </span>
        </div>

        <div className="flex items-center gap-6 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span>Escala (%):</span>
            <span className="inline-block w-3.5 h-3.5 rounded bg-[#60a5fa]" title="0%"></span>
            <span>0%</span>
            <span className="inline-block w-12 h-2 rounded bg-gradient-to-r from-[#60a5fa] via-[#2563eb] to-[#1e3a8a]"></span>
            <span>100%</span>
            <span className="inline-block w-3.5 h-3.5 rounded bg-[#1e3a8a]" title="100%"></span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded bg-slate-700 border border-slate-600"></span>
            <span>Por defecto: {defaultPercentage}%</span>
          </div>
        </div>
      </div>

      {/* Contenedor del Mapa SVG Interactivo */}
      <div className="relative w-full max-w-6xl aspect-[1.9/1] bg-slate-950/80 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl shadow-blue-950/20">
        <ComposableMap
          projectionConfig={{
            rotate: [-10, 0, 0],
            scale: 147,
          }}
          className="w-full h-full"
        >
          <ZoomableGroup zoom={1} minZoom={0.8} maxZoom={5}>
            <Sphere stroke="#1e293b" strokeWidth={0.5} id="world-sphere" fill="transparent" />
            <Graticule stroke="#334155" strokeWidth={0.3} strokeDasharray="2 2" />

            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const countryName = (geo.properties?.name as string | undefined) || "Desconocido";
                  const geoId = geo.id !== undefined ? String(geo.id) : "";
                  const alpha3 = getAlpha3Code(geoId, countryName);
                  const countryRecord = countryMap.get(alpha3);

                  const percentage = countryRecord ? countryRecord.percentage : defaultPercentage;
                  const isCustom = Boolean(countryRecord);
                  const fillColor = isCustom ? colorScale(percentage) : "#334155";

                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      data-tooltip-id="map-tooltip"
                      fill={fillColor}
                      stroke="#0f172a"
                      strokeWidth={0.5}
                      className="transition-colors duration-200 outline-none cursor-pointer hover:fill-sky-400 hover:stroke-white hover:stroke-[1.5px]"
                      onMouseEnter={() => {
                        setTooltipContent({
                          name: countryRecord?.name || countryName,
                          code: alpha3,
                          percentage: Number(percentage.toFixed(1)),
                          isCustom,
                        });
                      }}
                      onMouseLeave={() => {
                        setTooltipContent(null);
                      }}
                      onClick={() => {
                        setSelectedCountry({
                          id: countryRecord?.id || `temp-${alpha3}`,
                          code: alpha3,
                          name: countryRecord?.name || countryName,
                          percentage: Number(percentage.toFixed(1)),
                        });
                      }}
                    />
                  );
                })
              }
            </Geographies>
          </ZoomableGroup>
        </ComposableMap>

        {/* Modal / Card flotante de país seleccionado */}
        {selectedCountry && (
          <div className="absolute bottom-4 left-4 right-4 md:right-auto md:w-80 bg-slate-900/95 backdrop-blur-md p-4 rounded-xl border border-blue-500/30 shadow-xl text-white">
            <div className="flex justify-between items-start mb-2">
              <div>
                <span className="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">
                  {selectedCountry.code}
                </span>
                <h3 className="text-lg font-bold">{selectedCountry.name}</h3>
              </div>
              <button
                onClick={() => setSelectedCountry(null)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800"
              >
                ✕
              </button>
            </div>

            <div className="mt-3">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-400">Porcentaje asignado:</span>
                <span className="font-semibold text-blue-300">{selectedCountry.percentage}%</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-blue-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(selectedCountry.percentage, 100)}%` }}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* React Tooltip que flota sobre el mouse al hacer hover */}
      <Tooltip
        id="map-tooltip"
        className="!bg-slate-900 !text-white !rounded-lg !border !border-slate-700 !shadow-xl !px-3 !py-2 !opacity-100 z-50 pointer-events-none"
      >
        {tooltipContent && (
          <div className="text-xs flex flex-col gap-0.5">
            <div className="font-semibold text-sm flex items-center gap-1.5 text-slate-100">
              <span>{tooltipContent.name}</span>
              <span className="text-slate-400 font-normal">({tooltipContent.code})</span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-slate-400">Porcentaje:</span>
              <span className="font-bold text-blue-400">{tooltipContent.percentage}%</span>
              {!tooltipContent.isCustom && (
                <span className="text-[10px] px-1 py-0.5 bg-slate-800 text-slate-400 rounded">
                  Defecto
                </span>
              )}
            </div>
          </div>
        )}
      </Tooltip>
    </div>
  );
}
