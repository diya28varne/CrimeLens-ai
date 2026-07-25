import { apiFetch } from "@/shared/api/client";

export type NetworkNode = {
  id: string;
  label: string;
  is_repeat_offender: boolean;
  incident_count: number;
  risk_flags: Record<string, unknown>;
};

export type NetworkEdge = {
  id: string;
  source: string;
  target: string;
  link_type: string;
  origin: string;
  weight: number;
};

export type RepeatOffender = {
  person_id: string;
  full_name: string;
  incident_count: number;
  score: number;
  offense_mix: Array<{ key: string; name: string; count: number }>;
};

export async function fetchNetworkGraph() {
  return apiFetch<{
    data: {
      nodes: NetworkNode[];
      edges: NetworkEdge[];
      meta: { truncated: boolean; node_count: number; edge_count: number };
    };
  }>("/network/graph?limit_nodes=50");
}

export async function fetchRepeatOffenders() {
  return apiFetch<{ data: RepeatOffender[] }>("/network/repeat-offenders?limit=20");
}
