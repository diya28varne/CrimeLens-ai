import { apiFetch } from "@/shared/api/client";

export type TrendPoint = { bucket_start: string; count: number };
export type TrendSeries = { key: string; points: TrendPoint[] };

export type BreakdownItem = { key: string; name: string; count: number };

export type CorrelationResult = {
  year: number;
  indicator_code: string;
  crime_metric: string;
  method: string;
  coefficient: number | null;
  abs_coefficient: number | null;
  sample_size: number;
  interpretation: string;
  points: Array<{
    district_id: string;
    district_code: string;
    district_name: string;
    indicator_value: number;
    crime_value: number;
  }>;
};

export type CorrelationSummary = {
  year: number;
  indicator_code: string;
  crime_metric: string;
  coefficient: number | null;
  abs_coefficient: number | null;
  sample_size: number;
  interpretation: string;
};

export async function fetchTrends(): Promise<{ interval: string; series: TrendSeries[] }> {
  const res = await apiFetch<{ data: { interval: string; series: TrendSeries[] } }>(
    "/analytics/trends?interval=day",
  );
  return res.data;
}

export async function fetchBreakdown(
  groupBy: "offense" | "severity",
): Promise<{ group_by: string; items: BreakdownItem[] }> {
  const res = await apiFetch<{ data: { group_by: string; items: BreakdownItem[] } }>(
    `/analytics/breakdown?group_by=${groupBy}`,
  );
  return res.data;
}

export async function fetchCorrelation(
  indicatorCode: string,
): Promise<CorrelationResult> {
  const res = await apiFetch<{ data: CorrelationResult }>(
    `/analytics/socio-economic/correlation?indicator_code=${encodeURIComponent(indicatorCode)}`,
  );
  return res.data;
}

export async function fetchCorrelations(): Promise<CorrelationSummary[]> {
  const res = await apiFetch<{ data: CorrelationSummary[] }>(
    "/analytics/socio-economic/correlations",
  );
  return res.data;
}
