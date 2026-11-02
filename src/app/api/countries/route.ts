import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { CountryData } from "@/types/country";

// Porcentaje por defecto solicitado (X%)
const DEFAULT_FALLBACK_PERCENTAGE = 45.0;

// Lista de respaldo en memoria si la base de datos aún no ha corrido las migraciones
const FALLBACK_COUNTRIES: CountryData[] = [
  { id: "1", code: "USA", name: "United States", percentage: 78.5 },
  { id: "2", code: "CAN", name: "Canada", percentage: 64.2 },
  { id: "3", code: "MEX", name: "Mexico", percentage: 52.0 },
  { id: "4", code: "BRA", name: "Brazil", percentage: 59.4 },
  { id: "5", code: "ARG", name: "Argentina", percentage: 48.7 },
  { id: "6", code: "CHL", name: "Chile", percentage: 61.3 },
  { id: "7", code: "COL", name: "Colombia", percentage: 45.0 },
  { id: "8", code: "PER", name: "Peru", percentage: 42.1 },
  { id: "9", code: "ESP", name: "Spain", percentage: 71.0 },
  { id: "10", code: "FRA", name: "France", percentage: 68.4 },
  { id: "11", code: "DEU", name: "Germany", percentage: 82.3 },
  { id: "12", code: "GBR", name: "United Kingdom", percentage: 75.6 },
  { id: "13", code: "ITA", name: "Italy", percentage: 63.8 },
  { id: "14", code: "PRT", name: "Portugal", percentage: 58.9 },
  { id: "15", code: "RUS", name: "Russia", percentage: 41.2 },
  { id: "16", code: "CHN", name: "China", percentage: 88.0 },
  { id: "17", code: "JPN", name: "Japan", percentage: 84.5 },
  { id: "18", code: "KOR", name: "South Korea", percentage: 79.1 },
  { id: "19", code: "IND", name: "India", percentage: 53.6 },
  { id: "20", code: "AUS", name: "Australia", percentage: 76.9 },
  { id: "21", code: "NZL", name: "New Zealand", percentage: 73.2 },
  { id: "22", code: "ZAF", name: "South Africa", percentage: 38.4 },
  { id: "23", code: "EGY", name: "Egypt", percentage: 34.0 },
  { id: "24", code: "NGA", name: "Nigeria", percentage: 29.5 },
  { id: "25", code: "NOR", name: "Norway", percentage: 89.2 },
  { id: "26", code: "SWE", name: "Sweden", percentage: 86.4 },
  { id: "27", code: "FIN", name: "Finland", percentage: 87.1 },
  { id: "28", code: "POL", name: "Poland", percentage: 55.3 },
  { id: "29", code: "UKR", name: "Ukraine", percentage: 37.8 },
  { id: "30", code: "SAU", name: "Saudi Arabia", percentage: 62.0 },
  { id: "31", code: "ARE", name: "United Arab Emirates", percentage: 80.5 },
];

export async function GET() {
  try {
    // Consulta los países en la base de datos PostgreSQL mediante Prisma
    const countries = await prisma.country.findMany({
      orderBy: { name: "asc" },
    });

    // Si la BD está conectada y tiene registros, los retornamos
    if (countries && countries.length > 0) {
      return NextResponse.json({
        success: true,
        data: countries,
        defaultPercentage: DEFAULT_FALLBACK_PERCENTAGE,
        source: "database",
      });
    }

    // Si la tabla está vacía, retornamos los datos preconfigurados
    return NextResponse.json({
      success: true,
      data: FALLBACK_COUNTRIES,
      defaultPercentage: DEFAULT_FALLBACK_PERCENTAGE,
      source: "fallback_empty_table",
    });
  } catch (error) {
    // Si la conexión a la base de datos falla o aún no está corriendo el servicio PostgreSQL,
    // devolvemos un fallback seguro para que la UI interactiva funcione de inmediato.
    console.warn("No se pudo conectar a la base de datos. Sirviendo fallback en memoria:", error);
    return NextResponse.json({
      success: true,
      data: FALLBACK_COUNTRIES,
      defaultPercentage: DEFAULT_FALLBACK_PERCENTAGE,
      source: "fallback_database_unreachable",
    });
  }
}
