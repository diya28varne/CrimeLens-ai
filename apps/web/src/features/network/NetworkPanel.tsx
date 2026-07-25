"use client";

import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import type { EChartsOption } from "echarts";

import {
  fetchNetworkGraph,
  fetchRepeatOffenders,
  type NetworkEdge,
  type NetworkNode,
  type RepeatOffender,
} from "@/features/network/api";
import { Chart } from "@/shared/ui/Chart";

export function NetworkPanel() {
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [edges, setEdges] = useState<NetworkEdge[]>([]);
  const [repeats, setRepeats] = useState<RepeatOffender[]>([]);
  const [selected, setSelected] = useState<NetworkNode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [graph, reps] = await Promise.all([fetchNetworkGraph(), fetchRepeatOffenders()]);
        if (cancelled) return;
        setNodes(graph.data.nodes);
        setEdges(graph.data.edges);
        setRepeats(reps.data);
        setSelected(graph.data.nodes.find((n) => n.is_repeat_offender) ?? graph.data.nodes[0] ?? null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load network");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const graphOption: EChartsOption = {
    tooltip: {},
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        label: { show: true, color: "#e8eefc", fontSize: 11 },
        force: { repulsion: 180, edgeLength: [60, 140] },
        data: nodes.map((n) => ({
          id: n.id,
          name: n.label,
          symbolSize: 18 + Math.min(24, n.incident_count * 3),
          itemStyle: {
            color: n.is_repeat_offender ? "#ff453a" : "#3d8bfd",
          },
          category: n.is_repeat_offender ? 0 : 1,
        })),
        links: edges.map((e) => ({
          source: e.source,
          target: e.target,
          value: e.weight,
          lineStyle: { width: Math.max(1, e.weight), color: "#9aa8c7", opacity: 0.55 },
          label: { show: false },
        })),
        categories: [{ name: "Repeat" }, { name: "Other" }],
        lineStyle: { curveness: 0.15 },
        emphasis: { focus: "adjacency" },
      },
    ],
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <header>
        <h1 style={{ margin: 0 }}>Network Analysis</h1>
        <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14 }}>
          Co-accused / associate graph from seeded demo persons.
        </p>
      </header>

      {error && (
        <div
          style={{
            border: "1px solid #ff453a",
            borderRadius: 10,
            padding: "10px 12px",
            background: "rgba(255,69,58,0.08)",
            fontSize: 14,
          }}
        >
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.4fr) minmax(260px,0.8fr)", gap: 12 }}>
        <Panel title={`Graph · ${nodes.length} nodes / ${edges.length} edges`}>
          <Chart option={graphOption} height={420} loading={loading} />
        </Panel>
        <div style={{ display: "grid", gap: 12, alignContent: "start" }}>
          <Panel title="Inspector">
            {selected ? (
              <div style={{ display: "grid", gap: 8, fontSize: 13 }}>
                <div style={{ fontWeight: 700, fontSize: 16 }}>{selected.label}</div>
                <div style={{ color: "var(--cl-muted)" }}>
                  {selected.is_repeat_offender ? "Repeat offender" : "Person of interest"}
                </div>
                <div>Incidents: {selected.incident_count}</div>
                <div>
                  Linked edges:{" "}
                  {
                    edges.filter((e) => e.source === selected.id || e.target === selected.id)
                      .length
                  }
                </div>
              </div>
            ) : (
              <div style={{ color: "var(--cl-muted)", fontSize: 13 }}>Select a node</div>
            )}
            <div style={{ display: "grid", gap: 6, marginTop: 12 }}>
              {nodes.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => setSelected(n)}
                  style={{
                    ...rowBtn,
                    borderColor: selected?.id === n.id ? "var(--cl-accent)" : "var(--cl-border)",
                  }}
                >
                  {n.label}
                </button>
              ))}
            </div>
          </Panel>
          <Panel title="Repeat offenders">
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
              {repeats.map((r) => (
                <li key={r.person_id} style={repeatRow}>
                  <div style={{ fontWeight: 600 }}>{r.full_name}</div>
                  <div style={{ color: "var(--cl-muted)", fontSize: 12 }}>
                    score {r.score.toFixed(2)} · {r.incident_count} incidents
                  </div>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={panelStyle}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{title}</div>
      {children}
    </div>
  );
}

const panelStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  background: "rgba(18, 26, 43, 0.72)",
  padding: "14px 16px",
};

const rowBtn: CSSProperties = {
  padding: "7px 10px",
  borderRadius: 8,
  border: "1px solid var(--cl-border)",
  background: "transparent",
  color: "var(--cl-text)",
  textAlign: "left",
  cursor: "pointer",
  fontSize: 13,
};

const repeatRow: CSSProperties = {
  padding: "8px 10px",
  borderRadius: 8,
  background: "rgba(11,18,32,0.45)",
};
