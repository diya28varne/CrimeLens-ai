import { apiFetch } from "@/shared/api/client";

export type DashboardOverview = {
  scope: {
    district_id: string | null;
    station_id: string | null;
    from: string;
    to: string;
  };
  kpis: {
    total_incidents: number;
    total_incidents_delta_pct: number | null;
    open_incidents: number;
    high_severity: number;
    hotspot_count: number;
    avg_risk_score: number | null;
  };
  by_severity: Array<{ key: string; name: string; count: number }>;
  by_offense_top: Array<{ key: string; name: string; count: number }>;
  trend_daily: Array<{ date: string; count: number }>;
  model: {
    prediction_run_id: string | null;
    model_version: string | null;
    generated_at: string | null;
    is_stale: boolean;
  };
};

export type DashboardAlert = {
  id: string;
  severity: string;
  title: string;
  body: string;
  metric: string;
  value: number;
  href?: string | null;
};

export async function fetchDashboardOverview(): Promise<DashboardOverview> {
  const res = await apiFetch<{ data: DashboardOverview }>("/dashboard/overview");
  return res.data;
}

export async function fetchDashboardAlerts(): Promise<DashboardAlert[]> {
  const res = await apiFetch<{ data: DashboardAlert[] }>("/dashboard/alerts");
  return res.data;
}
