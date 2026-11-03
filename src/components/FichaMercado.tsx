"use client";

import { useFichaMercado } from "@/hooks/useDss";
import {
  DIMENSIONES, ESTADO_CONTINUIDAD, ESTADO_EVALUACION, num, pct, score as fmtScore, usd,
} from "@/lib/formato";
import { BarrasH, Columnas, InsigniaRiesgo } from "./Graficos";

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-slate-800 pt-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">{titulo}</h3>
      {children}
    </section>
  );
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] text-slate-500">{etiqueta}</dt>
      <dd className="text-sm text-slate-100 tabular-nums">{valor}</dd>
    </div>
  );
}

export function FichaMercado({ sa6, iso3, onClose }: { sa6: string; iso3: string; onClose: () => void }) {
  const { data: f, error, isLoading } = useFichaMercado(sa6, iso3);

  if (isLoading) return <div className="p-6 text-sm text-slate-400">Cargando ficha de {iso3}…</div>;
  if (error || !f) return <div className="p-6 text-sm text-red-300">No se pudo cargar la ficha: {error?.message}</div>;

  const ind = f.indicadores;
  const presencia = f.tipo_mercado === "con_presencia";

  return (
    <div className="p-5 space-y-5">
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-mono text-slate-400">{f.iso3} · {f.region}</p>
          <h2 className="text-xl font-bold text-slate-50">{f.nombre}</h2>
          <p className="text-xs text-slate-400 mt-1">
            {presencia ? "Con presencia peruana" : "Mercado potencial (sin exportaciones peruanas observadas)"}
          </p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white text-sm px-2 py-1 rounded bg-slate-800" aria-label="Cerrar ficha">✕</button>
      </header>

      <div className="flex items-end gap-6">
        <div>
          <div className="text-4xl font-extrabold text-slate-50 tabular-nums">{fmtScore(f.score)}</div>
          <div className="text-xs text-slate-400">Exporting Score {f.ranking != null && `· puesto ${f.ranking}`}</div>
        </div>
        <div className="space-y-1 pb-1">
          <div className="text-xs text-slate-300">{ESTADO_EVALUACION[f.estado]}</div>
          <InsigniaRiesgo riesgo={f.riesgo_abandono} />
        </div>
      </div>
      {f.faltantes.length > 0 && (
        <p className="text-xs text-amber-200/80">
          Dimensiones sin datos (pesos renormalizados): {f.faltantes.join(", ")}.
        </p>
      )}

      <Seccion titulo="Dimensiones del índice (0–100)">
        <BarrasH
          datos={DIMENSIONES.map((d) => ({ etiqueta: d.nombre, valor: f.dimensiones[d.clave] == null ? null : f.dimensiones[d.clave]! * 100 }))}
          max={100}
          formato={(v) => (v == null ? "—" : v.toFixed(0))}
          nota={(d) => (d.etiqueta.startsWith("Trayectoria") && !presencia ? "No aplica (mercado potencial)" : "Sin datos")}
        />
      </Seccion>

      <Seccion titulo="Demanda internacional">
        <dl className="grid grid-cols-2 gap-3 mb-3">
          <Dato etiqueta="Importaciones desde el mundo" valor={usd(f.v_imp)} />
          <Dato etiqueta="CAGR" valor={pct(f.cagr)} />
          <Dato etiqueta="Variación interanual" valor={pct(ind.yoy ?? null)} />
          <Dato etiqueta="Participación del Perú" valor={pct(f.s_peru, 2)} />
        </dl>
        {ind.imp_anual && Object.keys(ind.imp_anual).length > 0 && (
          <Columnas datos={Object.entries(ind.imp_anual).map(([a, v]) => ({ etiqueta: a, valor: v }))} formato={usd} alto={80} />
        )}
      </Seccion>

      <Seccion titulo="Competencia">
        <dl className="grid grid-cols-2 gap-3 mb-3">
          <Dato etiqueta="Países proveedores" valor={num(ind.n_proveedores ?? null)} />
          <Dato etiqueta="Concentración (HHI)" valor={f.hhi == null ? "—" : f.hhi.toFixed(3)} />
        </dl>
        {ind.top_proveedores && Object.keys(ind.top_proveedores).length > 0 && (
          <BarrasH datos={Object.entries(ind.top_proveedores).map(([iso, s]) => ({ etiqueta: iso, valor: s }))} max={1} formato={(v) => pct(v)} />
        )}
      </Seccion>

      <Seccion titulo="Trayectoria exportadora del Perú">
        {presencia ? (
          <>
            <dl className="grid grid-cols-2 gap-3 mb-3">
              <Dato etiqueta="FOB 2021–2025" valor={usd(f.fob_peru_total)} />
              <Dato etiqueta="Empresas exportadoras" valor={num(f.n_empresas)} />
              <Dato etiqueta="Meses con exportaciones" valor={`${num(ind.meses_activos ?? null)} (${(ind.actividad_pct ?? 0).toFixed(0)}%)`} />
              <Dato etiqueta="Meses desde el último envío" valor={num(f.recencia_meses)} />
              <Dato etiqueta="Mayor intervalo sin envíos" valor={`${num(ind.max_intervalo_meses ?? null)} meses`} />
              <Dato etiqueta="Continuidad" valor={ESTADO_CONTINUIDAD[f.estado_continuidad ?? ""] ?? "—"} />
            </dl>
            <p className="text-[11px] text-slate-500 mb-1">FOB mensual (USD)</p>
            <Columnas
              datos={f.serie_mensual.map((m) => ({ etiqueta: m.mes, valor: m.fob_usd, extra: `${m.envios} envíos, ${m.empresas} empresas` }))}
              formato={usd}
            />
          </>
        ) : (
          <p className="text-sm text-slate-400">Sin exportaciones peruanas registradas en 2021–2025: la trayectoria se muestra como información contextual y no pondera en el índice.</p>
        )}
      </Seccion>

      <Seccion titulo="Acceso al mercado">
        <dl className="grid grid-cols-1 gap-2">
          <Dato etiqueta="Acuerdo comercial vigente" valor={f.acuerdo ?? "Sin TLC registrado"} />
        </dl>
        {!ind.acceso_verificado && (
          <p className="mt-2 text-xs text-amber-200/80">
            Dato preliminar: aranceles NMF/preferenciales y medidas no arancelarias pendientes de verificar en Market Access Map.
          </p>
        )}
        {f.fuentes.acceso && (
          <a href={f.fuentes.acceso} target="_blank" rel="noreferrer" className="text-xs text-blue-300 hover:underline">Fuente: {f.fuentes.acceso}</a>
        )}
      </Seccion>

      <Seccion titulo="Resultado económico estimado (por unidad, incoterm CIF)">
        {f.escenarios_economicos.length ? (
          <>
            <table className="w-full text-xs tabular-nums">
              <thead className="text-slate-500">
                <tr><th className="text-left font-normal">Escenario</th><th className="text-right font-normal">Precio</th><th className="text-right font-normal">Costo</th><th className="text-right font-normal">Margen</th></tr>
              </thead>
              <tbody className="text-slate-200">
                {f.escenarios_economicos.map((e) => (
                  <tr key={e.escenario} className="border-t border-slate-800">
                    <td className="py-1 capitalize">{e.escenario}</td>
                    <td className="text-right">US$ {e.precio_usd_unidad.toFixed(2)}</td>
                    <td className="text-right">US$ {e.costo_total_usd_unidad.toFixed(2)}</td>
                    <td className="text-right">{e.margen_pct?.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-[11px] text-amber-200/80">
              Costos con datos sintéticos de demostración. Precio de referencia: {ind.fuente_precio === "valor_unitario_fob_peru_24m" ? "valor unitario FOB peruano (24 meses)" : "valor unitario del importador (todas las procedencias)"}.
            </p>
          </>
        ) : (
          <p className="text-sm text-slate-400">Sin precio de referencia para este mercado.</p>
        )}
      </Seccion>

      {f.nota_agregacion && (
        <p className="text-[11px] text-slate-500 border-t border-slate-800 pt-3">Nivel de agregación: {f.nota_agregacion}</p>
      )}
    </div>
  );
}
