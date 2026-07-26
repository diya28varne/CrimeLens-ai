import { apiFetch } from "@/shared/api/client";

export type ScenarioControls = {
  patrol_delta_pct: number;
  cctv_delta_pct: number;
  public_event: boolean;
  event_zone: "central" | "metro_corridor_a" | "east" | "west" | "north" | "south";
  time_of_day: "morning" | "afternoon" | "evening" | "night";
  day_type: "weekday" | "weekend" | "holiday";
  weather_stress: boolean;
};

export type ScenarioPreset = {
  id: string;
  name: string;
  description: string;
  controls: ScenarioControls;
};

export type SimulationPoint = {
  id: string;
  kind: "station" | "hotspot";
  label: string;
  lon: number;
  lat: number;
  baseline_risk: number;
  simulated_risk: number;
  delta: number;
  delta_pct: number;
};

export type SimulationRun = {
  run_id: string;
  scenario_label: string;
  preset_id: string | null;
  controls: ScenarioControls;
  baseline: {
    aggregate_risk: number;
    hotspot_count: number;
    patrol_coverage: number;
    resource_utilization: number;
    ops_cost_index: number;
  };
  simulated: {
    aggregate_risk: number;
    hotspot_count: number;
    patrol_coverage: number;
    resource_utilization: number;
    ops_cost_index: number;
  };
  comparison: Array<{
    key: string;
    label: string;
    baseline: number;
    simulated: number;
    unit: string;
    higher_is_better: boolean | null;
  }>;
  deltas: Array<{
    sector: string;
    pct_change: number;
    direction: "up" | "down" | "flat";
    note: string;
  }>;
  points: SimulationPoint[];
  event_zone: {
    id: string;
    label: string;
    lon: number;
    lat: number;
    radius_km: number;
  };
  briefing: {
    scenario_label: string;
    current_risk_band: string;
    predicted_changes: string[];
    suggested_actions: string[];
    confidence: number;
    disclaimer: string;
  };
  confidence: number;
  disclaimer: string;
  source: Record<string, unknown>;
};

export const DEFAULT_CONTROLS: ScenarioControls = {
  patrol_delta_pct: 0,
  cctv_delta_pct: 0,
  public_event: false,
  event_zone: "central",
  time_of_day: "evening",
  day_type: "weekday",
  weather_stress: false,
};

export async function fetchScenarios() {
  return apiFetch<{ data: ScenarioPreset[] }>("/simulation/scenarios");
}

export async function runSimulation(body: {
  preset_id?: string | null;
  controls: ScenarioControls;
}) {
  return apiFetch<{ data: SimulationRun }>("/simulation/runs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
