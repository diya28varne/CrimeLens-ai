import { apiFetch } from "@/shared/api/client";

export type ReportTemplate = {
  id: string;
  name: string;
  description: string;
  default_days: number;
};

export type IntelligenceReport = {
  id: string;
  template_id: string;
  cover: {
    title: string;
    subtitle: string;
    prepared_for: string;
    classification: string;
    report_type: string;
    date_label: string;
    range_label: string;
    generated_at: string;
  };
  executive_summary: string;
  overview: {
    total_incidents: number;
    delta_pct: number | null;
    open_incidents: number;
    high_severity: number;
    by_severity: Array<{ key: string; name: string; count: number }>;
    by_offense: Array<{ key: string; name: string; count: number }>;
    trend_daily: Array<{ date: string; count: number }>;
  };
  insights: Array<{ title: string; body: string; kind: "observed" | "forecast" }>;
  hotspots: Array<{
    label: string;
    risk_level: string;
    score: number;
    confidence: number;
    factors: string[];
    suggested_action: string;
  }>;
  predictions: Array<{
    scope_name: string;
    risk_score: number;
    risk_band: string;
    confidence: number;
    kind: "forecast";
    note: string;
  }>;
  xai_summary: {
    scope_name: string;
    summary: string;
    top_factors: string[];
    confidence: number;
  } | null;
  recommendations: Array<{
    title: string;
    rationale: string;
    confidence: number;
    priority: string;
  }>;
  resource_plan: Array<{ division: string; change: string; note: string }>;
  checklist: Array<{ id: string; text: string; done: boolean }>;
  presenter_script: Array<{
    section_id: string;
    title: string;
    narration: string;
    drill_href?: string | null;
  }>;
  disclaimer: string;
  generated_at: string;
};

export async function fetchReportTemplates() {
  return apiFetch<{ data: ReportTemplate[] }>("/reports/templates");
}

export async function generateReport(body: {
  template_id: string;
  from?: string;
  to?: string;
}) {
  return apiFetch<{ data: IntelligenceReport }>("/reports/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
