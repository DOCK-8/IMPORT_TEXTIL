import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

// Valor por defecto para X%
const DEFAULT_PERCENTAGE = 45.0;

// Lista de países base con código ISO Alpha-3 estándar (coincidente con topojson mundiales)
const INITIAL_COUNTRIES = [
  { code: "USA", name: "United States", percentage: 78.5 },
  { code: "CAN", name: "Canada", percentage: 64.2 },
  { code: "MEX", name: "Mexico", percentage: 52.0 },
  { code: "BRA", name: "Brazil", percentage: 59.4 },
  { code: "ARG", name: "Argentina", percentage: 48.7 },
  { code: "CHL", name: "Chile", percentage: 61.3 },
  { code: "COL", name: "Colombia", percentage: 45.0 },
  { code: "PER", name: "Peru", percentage: 42.1 },
  { code: "ESP", name: "Spain", percentage: 71.0 },
  { code: "FRA", name: "France", percentage: 68.4 },
  { code: "DEU", name: "Germany", percentage: 82.3 },
  { code: "GBR", name: "United Kingdom", percentage: 75.6 },
  { code: "ITA", name: "Italy", percentage: 63.8 },
  { code: "PRT", name: "Portugal", percentage: 58.9 },
  { code: "RUS", name: "Russia", percentage: 41.2 },
  { code: "CHN", name: "China", percentage: 88.0 },
  { code: "JPN", name: "Japan", percentage: 84.5 },
  { code: "KOR", name: "South Korea", percentage: 79.1 },
  { code: "IND", name: "India", percentage: 53.6 },
  { code: "AUS", name: "Australia", percentage: 76.9 },
  { code: "NZL", name: "New Zealand", percentage: 73.2 },
  { code: "ZAF", name: "South Africa", percentage: 38.4 },
  { code: "EGY", name: "Egypt", percentage: 34.0 },
  { code: "NGA", name: "Nigeria", percentage: 29.5 },
  { code: "NOR", name: "Norway", percentage: 89.2 },
  { code: "SWE", name: "Sweden", percentage: 86.4 },
  { code: "FIN", name: "Finland", percentage: 87.1 },
  { code: "POL", name: "Poland", percentage: 55.3 },
  { code: "UKR", name: "Ukraine", percentage: 37.8 },
  { code: "SAU", name: "Saudi Arabia", percentage: 62.0 },
  { code: "ARE", name: "United Arab Emirates", percentage: 80.5 },
];

export async function main() {
  console.log("🌱 Iniciando seed de países en la base de datos...");

  for (const country of INITIAL_COUNTRIES) {
    await prisma.country.upsert({
      where: { code: country.code },
      update: {
        name: country.name,
        percentage: country.percentage,
      },
      create: {
        code: country.code,
        name: country.name,
        percentage: country.percentage ?? DEFAULT_PERCENTAGE,
      },
    });
  }

  console.log(`✅ Seed completado: ${INITIAL_COUNTRIES.length} países registrados con éxito.`);
}

main()
  .catch((e) => {
    console.error("❌ Error ejecutando seed:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
