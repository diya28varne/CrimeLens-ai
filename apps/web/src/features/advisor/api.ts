import { apiFetch } from "@/shared/api/client";

export type EvidenceItem = {
  kind: string;
  label: string;
  detail: string;
  value?: number | string | null;
  href?: string | null;
};

export type Pattern = {
  id: string;
  title: string;
  explanation: string;
  kind: "observed" | "forecast";
  confidence: number;
  strength: "high" | "medium" | "low";
  evidence: EvidenceItem[];
};

export type RiskArea = {
  id: string;
  name: string;
  risk_band: "High" | "Medium" | "Elevated-low" | "Low";
  risk_score: number;
  confidence: number;
  why: string;
  kind: "observed" | "forecast";
  evidence: EvidenceItem[];
};

export type ActionRec = {
  id: string;
  title: string;
  rationale: string;
  confidence: number;
  priority: "high" | "medium" | "low";
  simulation_preset_id?: string | null;
  evidence: EvidenceItem[];
};

export type TimelineEntry = {
  id: string;
  generated_at: string;
  summary_excerpt: string;
  recommendation_count: number;
  hotspot_realized_note?: string | null;
  accuracy_note?: string | null;
  acted_on_demo?: boolean | null;
};

export type AdvisorBrief = {
  id: string;
  generated_at: string;
  summary: {
    headline: string;
    body: string;
    week_over_week_pct?: number | null;
    kind_tags: Array<"observed" | "forecast">;
  };
  patterns: Pattern[];
  risk_areas: RiskArea[];
  actions: ActionRec[];
  timeline: TimelineEntry[];
  sources: Array<Record<string, unknown>>;
  disclaimer: string;
  confidence: number;
};

export async function fetchAdvisorBrief() {
  return apiFetch<{ data: AdvisorBrief }>("/advisor/brief/current");
}

export async function refreshAdvisorBrief() {
  return apiFetch<{ data: AdvisorBrief }>("/advisor/brief/refresh", {
    method: "POST",
  });
}

export async function fetchAdvisorHistory() {
  return apiFetch<{ data: TimelineEntry[] }>("/advisor/brief/history?limit=14");
}
