import { apiFetch } from "@/shared/api/client";

export type PredictionRun = {
  id: string;
  model_code: string;
  model_version: string;
  task: string;
  metric: string;
  scope_type: string;
  horizon_start: string;
  horizon_end: string;
  generated_at: string;
  is_current: boolean;
  status_banner: string;
};

export type PredictionValue = {
  id: string;
  scope: { type: string; district_id?: string | null; station_id?: string | null };
  value: number;
  lower_bound?: number | null;
  upper_bound?: number | null;
  properties: Record<string, unknown>;
};

export type Explanation = {
  prediction_value_id: string;
  model_version: string;
  base_value: number;
  output_value: number;
  global_importance: Array<{ feature: string; importance: number }>;
  local_contributions: Array<{
    feature: string;
    value?: number | string | null;
    contribution: number;
  }>;
  summary_text?: string | null;
};

export type HotspotFeature = {
  id: string;
  rank: number;
  score: number;
  incident_count: number;
  centroid: { type?: string; coordinates?: [number, number] };
  properties: Record<string, unknown>;
};

export async function fetchCurrentPredictions() {
  return apiFetch<{
    data: { run: PredictionRun | null; values: PredictionValue[] };
  }>("/predictions/current?metric=risk_score&top_n=20");
}

export async function fetchHotspots() {
  return apiFetch<{
    data: {
      run: {
        id: string;
        method: string;
        model_version: string | null;
        is_current: boolean;
      } | null;
      features: HotspotFeature[];
    };
  }>("/predictions/hotspots/current?limit=20");
}

export async function fetchExplanation(valueId: string) {
  return apiFetch<{ data: Explanation }>(`/predictions/values/${valueId}/explanation`);
}

export async function fetchModels() {
  return apiFetch<{
    data: Array<{
      model_code: string;
      model_version: string;
      task: string;
      algorithm: string;
      status: string;
      metrics: Record<string, number>;
    }>;
  }>("/predictions/models");
}
