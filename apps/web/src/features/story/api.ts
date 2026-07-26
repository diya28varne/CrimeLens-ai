import { apiFetch } from "@/shared/api/client";

export type StoryPoint = {
  id: string;
  lon: number;
  lat: number;
  offense_code: string;
  offense_name: string;
  severity: string;
  occurred_at: string;
  title?: string | null;
};

export type DensityCell = {
  lon: number;
  lat: number;
  count: number;
  intensity: number;
  stage: string;
};

export type StoryFrame = {
  t: string;
  cumulative_count: number;
  new_count: number;
  new_points: StoryPoint[];
  density_cells: DensityCell[];
};

export type StoryChapter = {
  id: string;
  t_start: string;
  t_end: string;
  title: string;
  narrative: string;
  kind: "observed";
  metrics: Record<string, unknown>;
};

export type StoryEvent = {
  id: string;
  t: string;
  label: string;
  kind: string;
  detail: string;
};

export type DetectiveBrief = {
  cursor_at: string;
  window_from: string;
  window_to: string;
  headline: string;
  findings: Array<{
    question: string;
    answer: string;
    kind: "observed" | "forecast";
    evidence: string[];
  }>;
  suggested_actions: string[];
  simulation_preset_id?: string | null;
  disclaimer: string;
  confidence: number;
};

export async function fetchStoryFrames(params: {
  from?: string;
  to?: string;
  offense_code?: string;
}) {
  const q = new URLSearchParams();
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  if (params.offense_code) q.set("offense_code", params.offense_code);
  return apiFetch<{
    data: {
      range: {
        from: string;
        to: string;
        total_incidents: number;
        offense_codes: string[];
      };
      frames: StoryFrame[];
    };
  }>(`/story/frames?${q.toString()}`);
}

export async function fetchStoryChapters(params: {
  from?: string;
  to?: string;
  offense_code?: string;
}) {
  const q = new URLSearchParams();
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  if (params.offense_code) q.set("offense_code", params.offense_code);
  return apiFetch<{ data: StoryChapter[] }>(`/story/chapters?${q.toString()}`);
}

export async function fetchStoryEvents(params: { from?: string; to?: string }) {
  const q = new URLSearchParams();
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  return apiFetch<{ data: StoryEvent[] }>(`/story/events?${q.toString()}`);
}

export async function runDetective(body: {
  cursor_at: string;
  window_days?: number;
  offense_code?: string | null;
}) {
  return apiFetch<{ data: DetectiveBrief }>("/story/detective", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchJourney(incidentId: string) {
  return apiFetch<{
    data: {
      incident_id: string;
      title: string;
      offense_code: string;
      nearby_similar: number;
      steps: Array<{ key: string; label: string; at?: string | null; detail: string }>;
      disclaimer: string;
    };
  }>(`/story/journey/${incidentId}`);
}
