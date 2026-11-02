import { WorldMap } from "@/components/WorldMap";

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-start p-4 md:p-8 selection:bg-blue-600 selection:text-white">
      {/* Encabezado */}
      <header className="max-w-6xl w-full text-center my-6 md:my-10 space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-xs font-semibold uppercase tracking-wider">
          <span>Interactive Visualization</span>
          <span>•</span>
          <span>Next.js 16 + Prisma</span>
        </div>
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          Mapa Mundi Interactivo de Porcentajes
        </h1>
        <p className="max-w-2xl mx-auto text-slate-400 text-sm md:text-base leading-relaxed">
          Pasa el cursor sobre cualquier país para ver su porcentaje asignado o haz clic para ver más
          detalles. Los datos provienen del Route Handler respaldado por Prisma ORM y PostgreSQL.
        </p>
      </header>

      {/* Componente del Mapa */}
      <main className="w-full max-w-6xl flex flex-col items-center">
        <WorldMap />
      </main>

      {/* Footer informativo */}
      <footer className="mt-12 text-center text-xs text-slate-600">
        <p>
          Construido con Next.js (App Router), Prisma ORM, PostgreSQL, Tailwind CSS, SWR,
          react-simple-maps y react-tooltip.
        </p>
      </footer>
    </div>
  );
}
