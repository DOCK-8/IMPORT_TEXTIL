import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DSS Viabilidad Comercial Textil",
  description: "Sistema de Soporte a la Decisión para la selección de mercados de exportación de prendas de alpaca y lana.",
};

const NAV = [
  { href: "/", texto: "Mercados" },
  { href: "/modelo", texto: "Modelo y sensibilidad" },
  { href: "/servicio", texto: "Servicio GSTI" },
];

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-100">
        <header className="border-b border-slate-800">
          <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-bold text-slate-50">DSS Viabilidad Comercial Textil</div>
              <div className="text-[11px] text-slate-400">Prendas de alpaca y lana · Perú 2021–2025</div>
            </div>
            <nav className="flex gap-1 text-sm">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href} className="px-3 py-1.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white">
                  {n.texto}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-6">{children}</main>
        <footer className="border-t border-slate-800 py-4 text-center text-[11px] text-slate-500 px-4">
          Fuentes: PROMPERÚ/SUNAT (embarques), UN Comtrade (importaciones), MINCETUR (acuerdos comerciales).
          Los costos de los escenarios económicos son datos sintéticos de demostración.
        </footer>
      </body>
    </html>
  );
}
