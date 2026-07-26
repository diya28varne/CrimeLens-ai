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

export type AnalyticsFinding = {
  id: string;
  severity: "high" | "medium" | "low";
  title: string;
  detail: string;
};

export type AnalyticsInsights = {
  window_days: number;
  current: { from: string; to: string; total: number };
  prior: { from: string; to: string; total: number };
  delta: number;
  pct_change: number;
  daily: Array<{ date: string; count: number }>;
  spikes: Array<{ date: string; count: number; vs_mean: number }>;
  by_hour: Array<{ hour: number; count: number }>;
  by_dow: Array<{ dow: number; label: string; count: number }>;
  weekend: { count: number; per_day: number };
  weekday: { count: number; per_day: number };
  peak_hour: { hour: number; count: number };
  concentration: {
    top1_share_pct: number;
    top3_share_pct: number;
    hhi: number;
    label: string;
    top_offense: { code: string; name: string; count: number } | null;
  };
  severity: {
    high_critical_count: number;
    high_critical_share_pct: number;
    by_severity: Record<string, number>;
  };
  findings: AnalyticsFinding[];
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

export async function fetchInsights(days = 30): Promise<AnalyticsInsights> {
  const res = await apiFetch<{ data: AnalyticsInsights }>(
    `/analytics/insights?days=${days}`,
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
