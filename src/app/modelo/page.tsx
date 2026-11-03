import { PanelModelo } from "@/components/PanelModelo";

export default function ModeloPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-50">Modelo predictivo y robustez del índice</h1>
        <p className="text-sm text-slate-400 mt-1 max-w-3xl">
          Evaluación temporal del predictor de abandono de mercado (horizonte de 24 meses) frente a métodos estáticos y
          lineales, y estabilidad del ranking ante cambios de ponderación y normalización.
        </p>
      </div>
      <PanelModelo sa6="611019" />
    </div>
  );
}
