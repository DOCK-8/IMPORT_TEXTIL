import useSWR from "swr";
import { CountriesApiResponse, CountryData } from "@/types/country";

const fetcher = async (url: string): Promise<CountriesApiResponse> => {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Error ${res.status}: Fallo al consultar los países`);
  }
  return res.json();
};

export function useCountries() {
  const { data, error, isLoading, mutate } = useSWR<CountriesApiResponse>(
    "/api/countries",
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  // Crear un mapa indexado por código ISO para búsquedas O(1) en el render del mapa
  const countryMap = new Map<string, CountryData>();
  if (data?.data) {
    for (const country of data.data) {
      countryMap.set(country.code.toUpperCase(), country);
    }
  }

  return {
    countries: data?.data ?? [],
    countryMap,
    defaultPercentage: data?.defaultPercentage ?? 45.0,
    isLoading,
    isError: Boolean(error),
    error,
    mutate,
  };
}
