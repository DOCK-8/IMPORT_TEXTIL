# World Map Interactive with Next.js, Prisma & PostgreSQL

Aplicación Full-Stack en Next.js (App Router, TypeScript y Tailwind CSS) que muestra un mapa mundi interactivo SVG con porcentajes asignados a cada país (y valor por defecto de X%).

---

## 🏛️ Arquitectura del Proyecto

1. **Base de Datos (Prisma ORM + PostgreSQL)**:
   - Schema en [`prisma/schema.prisma`](file:///home/iamstupid/Repository/GPST/prisma/schema.prisma) con el modelo `Country`:
     - `id`: Identificador único (UUID).
     - `code`: Código ISO 3166-1 alpha-3 único (e.g. `USA`, `MEX`, `ESP`, `COL`).
     - `name`: Nombre descriptivo del país.
     - `percentage`: Valor flotante asignado (default `X%`).
   - Script de Seed en [`prisma/seed.ts`](file:///home/iamstupid/Repository/GPST/prisma/seed.ts) con soporte para `upsert` y valor base de porcentaje.
   - Singleton de conexión optimizado en [`src/lib/prisma.ts`](file:///home/iamstupid/Repository/GPST/src/lib/prisma.ts).

2. **Backend / API (Next.js App Router)**:
   - Route Handler en [`src/app/api/countries/route.ts`](file:///home/iamstupid/Repository/GPST/src/app/api/countries/route.ts) atendiendo solicitudes `GET /api/countries`.
   - Incluye fallback graceful para permitir el renderizado y prueba inmediata de la UI interactiva mientras se inicia el servicio PostgreSQL.

3. **Capa de Comunicación (SWR)**:
   - Hook reactivo [`useCountries`](file:///home/iamstupid/Repository/GPST/src/hooks/useCountries.ts) con SWR.
   - Provee indexación O(1) con `Map` por código ISO, estado de carga (`isLoading`), y revalidación.

4. **Frontend / UI**:
   - Componente [`WorldMap`](file:///home/iamstupid/Repository/GPST/src/components/WorldMap.tsx) con `react-simple-maps` y `react-tooltip`.
   - TopoJSON local de alta eficiencia en [`public/world-110m.json`](file:///home/iamstupid/Repository/GPST/public/world-110m.json).
   - Conversión de identificadores ISO en [`src/lib/geoUtils.ts`](file:///home/iamstupid/Repository/GPST/src/lib/geoUtils.ts).
   - Escala cromática dinámica (D3) según el porcentaje del país y tarjeta flotante interactiva al hacer click o hover.

---

## 🚀 Puesta en Marcha

### 1. Variables de Entorno (.env)
Asegúrate de tener configurada tu cadena de conexión a PostgreSQL en `.env`:
```env
DATABASE_URL="postgresql://usuario:password@localhost:5432/gpst_db?schema=public"
```

### 2. Ejecutar Migraciones y Seed en PostgreSQL
```bash
# Aplicar migración inicial
npx prisma migrate dev --name init

# Poblar la base de datos con los países y porcentajes iniciales
npm run db:seed
```

### 3. Iniciar Servidor de Desarrollo
```bash
npm run dev
```
Abre [http://localhost:3000](http://localhost:3000) en tu navegador.
