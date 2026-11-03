import useSWR from "swr";
import type {
  EstadoServicio, FichaMercado, Prenda, ReporteModelo, Sensibilidad, ViabilidadResponse,
} from "@/types/dss";

export const fetcher = async <T,>(url: string): Promise<T> => {
  const res = await fetch(url);
  if (!res.ok) {
    const detalle = await res.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${res.status} al consultar ${url}`);
  }
  return res.json();
};

const opciones = { revalidateOnFocus: false, dedupingInterval: 60000 };

export const useProductos = () => useSWR<Prenda[]>("/api/v1/productos", fetcher, opciones);

export const useViabilidad = (sa6: string, escenario: string) =>
  useSWR<ViabilidadResponse>(`/api/v1/viabilidad?sa6=${sa6}&escenario=${escenario}`, fetcher, opciones);

export const useFichaMercado = (sa6: string, iso3: string | null) =>
  useSWR<FichaMercado>(iso3 ? `/api/v1/viabilidad/${sa6}/${iso3}` : null, fetcher, opciones);

export const useModelo = (sa6: string) => useSWR<ReporteModelo>(`/api/v1/modelo/${sa6}`, fetcher, opciones);

export const useSensibilidad = (sa6: string) =>
  useSWR<Sensibilidad>(`/api/v1/sensibilidad/${sa6}`, fetcher, opciones);

export const useEstadoServicio = () =>
  useSWR<EstadoServicio>("/api/v1/servicio/estado", fetcher, { refreshInterval: 30000 });
