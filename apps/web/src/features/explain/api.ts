import { apiFetch } from "@/shared/api/client";

export type Factor = {
  feature: string;
  label: string;
  contribution: number;
  share_pct: number;
  raw_value?: number | string | null;
};

export type DecisionCard = {
  audit_id: string;
  prediction_value_id: string;
  scope_name: string;
  risk_score: number;
  risk_band: string;
  confidence: number;
  confidence_band: string;
  summary: string;
  factors: Factor[];
  evidence: Array<{
    id: string;
    label: string;
    detail: string;
    checked: boolean;
    href?: string | null;
  }>;
  scenarios: Array<{
    id: string;
    label: string;
    risk_score: number;
    risk_band: string;
    delta_pct: number;
    why: string;
  }>;
  similar_cases: Array<{
    title: string;
    detail: string;
    period: string;
    analogy_note: string;
  }>;
  timeline: Array<{ day_label: string; dominant_factor: string; note: string }>;
  recommendation: {
    title: string;
    reasons: string[];
    expected_risk_reduction_pct: number;
    confidence: number;
  } | null;
  model_version: string;
  base_value: number;
  generated_at: string;
  disclaimer: string;
};

export type AuditRecord = {
  id: string;
  created_at: string;
  prediction_value_id: string;
  scope_name: string;
  risk_score: number;
  risk_band: string;
  confidence: number;
  summary: string;
  top_factors: string[];
  recommendation?: string | null;
  outcome_status: "pending" | "demo_matched" | "demo_missed";
  outcome_note?: string | null;
};

export async function fetchDecisionCard(valueId: string) {
  return apiFetch<{ data: DecisionCard }>(`/explain/predictions/${valueId}`);
}

export async function fetchWhatIf(valueId: string, body: Record<string, unknown> = {}) {
  return apiFetch<{
    data: {
      baseline_score: number;
      scenarios: DecisionCard["scenarios"];
      disclaimer: string;
    };
  }>(`/explain/predictions/${valueId}/what-if`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchAuditTrail() {
  return apiFetch<{ data: AuditRecord[] }>("/explain/audit?limit=20");
}
