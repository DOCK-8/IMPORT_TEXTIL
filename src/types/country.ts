export interface CountryData {
  id: string;
  code: string; // ISO 3166-1 alpha-3 code (e.g. USA, MEX, ESP)
  name: string;
  percentage: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface CountriesApiResponse {
  success: boolean;
  data: CountryData[];
  defaultPercentage: number;
  error?: string;
}
