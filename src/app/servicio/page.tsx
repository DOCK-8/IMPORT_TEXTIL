import { PanelServicio } from "@/components/PanelServicio";

export default function ServicioPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-50">Gestión del servicio (GSTI)</h1>
        <p className="text-sm text-slate-400 mt-1 max-w-3xl">
          Disponibilidad de la API, ejecuciones del pipeline ETL, controles de calidad de datos y latencia frente al
          umbral RNF-01.
        </p>
      </div>
      <PanelServicio />
    </div>
  );
}
