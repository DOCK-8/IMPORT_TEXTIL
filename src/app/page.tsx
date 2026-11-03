import { Dashboard } from "@/components/Dashboard";

export default function Home() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-50">¿A qué mercado conviene exportar?</h1>
        <p className="text-sm text-slate-400 mt-1 max-w-3xl">
          Índice de Atractivo Comercial (0–100) por país de destino: demanda internacional, trayectoria exportadora
          peruana, acceso al mercado, competencia y resultado económico estimado. Seleccione un país en el mapa o en el
          ranking para ver su ficha.
        </p>
      </div>
      <Dashboard />
    </div>
  );
}
