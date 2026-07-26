"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import type { EChartsOption } from "echarts";

import {
  fetchCurrentPredictions,
  fetchExplanation,
  fetchHotspots,
  fetchModels,
  type Explanation,
  type HotspotFeature,
  type PredictionRun,
  type PredictionValue,
} from "@/features/prediction/api";
import { Chart } from "@/shared/ui/Chart";

export function PredictionPanel() {
  const [run, setRun] = useState<PredictionRun | null>(null);
  const [values, setValues] = useState<PredictionValue[]>([]);
  const [hotspots, setHotspots] = useState<HotspotFeature[]>([]);
  const [hotspotMethod, setHotspotMethod] = useState<string | null>(null);
  const [models, setModels] = useState<
    Array<{ model_code: string; model_version: string; status: string; algorithm: string }>
  >([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [expl, setExpl] = useState<Explanation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [pred, hs, mods] = await Promise.all([
          fetchCurrentPredictions(),
          fetchHotspots(),
          fetchModels(),
        ]);
        if (cancelled) return;
        setRun(pred.data.run);
        setValues(pred.data.values);
        setHotspots(hs.data.features);
        setHotspotMethod(hs.data.run?.method ?? null);
        setModels(mods.data);
        if (pred.data.values[0]) setSelected(pred.data.values[0].id);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load predictions");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchExplanation(selected);
        if (!cancelled) setExpl(res.data);
      } catch {
        if (!cancelled) setExpl(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const riskOption: EChartsOption = {
    tooltip: { trigger: "axis" },
    grid: { left: 120, right: 24, top: 16, bottom: 28 },
    xAxis: {
      type: "value",
      max: 1,
      splitLine: { lineStyle: { color: "#243049" } },
      axisLabel: { color: "#9aa8c7" },
    },
    yAxis: {
      type: "category",
      data: values
        .map((v) => String(v.properties.station_name ?? v.properties.station_code ?? "Station"))
        .reverse(),
      axisLabel: { color: "#9aa8c7", width: 110, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        data: values.map((v) => v.value).reverse(),
        itemStyle: { color: "#ff9500", borderRadius: [0, 4, 4, 0] },
      },
    ],
  };

  const shapOption: EChartsOption | null = expl
    ? {
        tooltip: { trigger: "axis" },
        grid: { left: 120, right: 24, top: 16, bottom: 28 },
        xAxis: {
          type: "value",
          splitLine: { lineStyle: { color: "#243049" } },
          axisLabel: { color: "#9aa8c7" },
        },
        yAxis: {
          type: "category",
          data: expl.local_contributions.map((c) => c.feature).reverse(),
          axisLabel: { color: "#9aa8c7" },
        },
        series: [
          {
            type: "bar",
            data: expl.local_contributions.map((c) => c.contribution).reverse(),
            itemStyle: { color: "#3d8bfd", borderRadius: [0, 4, 4, 0] },
          },
        ],
      }
    : null;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <header>
        <h1 style={{ margin: 0 }}>Prediction</h1>
        <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14 }}>
          Precomputed risk scores + SHAP explanations
          {run ? ` · ${run.model_code}@${run.model_version} (${run.status_banner})` : ""}.
        </p>
      </header>

      {error && <Banner>{error}</Banner>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12 }}>
        <Stat label="Model" value={models[0] ? `${models[0].model_code}` : "—"} />
        <Stat label="Status" value={models[0]?.status ?? "—"} />
        <Stat label="Hotspot method" value={hotspotMethod ?? "—"} />
        <Stat label="Stations scored" value={loading ? "…" : String(values.length)} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.2fr) minmax(0,1fr)", gap: 12 }}>
        <Panel title="Station risk scores">
          <Chart option={riskOption} height={280} loading={loading} />
          <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
            {values.map((v) => {
              const name = String(v.properties.station_name ?? "Station");
              const active = selected === v.id;
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => setSelected(v.id)}
                  style={{
                    ...rowBtn,
                    borderColor: active ? "var(--cl-accent)" : "var(--cl-border)",
                    background: active ? "rgba(61,139,253,0.12)" : "transparent",
                  }}
                >
                  <span>{name}</span>
                  <strong>{v.value.toFixed(3)}</strong>
                </button>
              );
            })}
          </div>
        </Panel>
        <Panel title="SHAP local contributions">
          {shapOption ? <Chart option={shapOption} height={240} /> : <Empty text="Select a station" />}
          {expl?.summary_text && (
            <p style={{ color: "var(--cl-muted)", fontSize: 13, lineHeight: 1.5, marginTop: 8 }}>
              {expl.summary_text}
            </p>
          )}
          {expl && (
            <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 6 }}>
              base {expl.base_value.toFixed(2)} → output {expl.output_value.toFixed(3)} ·{" "}
              {expl.model_version}
            </div>
          )}
          {selected ? (
            <Link
              href={`/explain?value=${selected}`}
              style={{
                display: "inline-block",
                marginTop: 12,
                background: "var(--cl-accent)",
                color: "#fff",
                textDecoration: "none",
                borderRadius: 8,
                padding: "8px 12px",
                fontWeight: 600,
                fontSize: 13,
              }}
            >
              Open Decision Card →
            </Link>
          ) : null}
        </Panel>
      </div>

      <Panel title="Current hotspots">
        <div style={{ display: "grid", gap: 8 }}>
          {hotspots.map((h) => (
            <div key={h.id} style={hotspotRow}>
              <strong>#{h.rank}</strong>
              <span>{String(h.properties.label ?? "Hotspot")}</span>
              <span style={{ color: "var(--cl-muted)" }}>score {h.score.toFixed(2)}</span>
              <span style={{ color: "var(--cl-muted)" }}>{h.incident_count} incidents</span>
            </div>
          ))}
          {!loading && hotspots.length === 0 && <Empty text="No hotspots" />}
        </div>
      </Panel>
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={panelStyle}>
      <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, marginTop: 6 }}>{value}</div>
    </div>
  );
}

function Banner({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        border: "1px solid #ff453a",
        borderRadius: 10,
        padding: "10px 12px",
        background: "rgba(255,69,58,0.08)",
        fontSize: 14,
      }}
    >
      {children}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div style={{ color: "var(--cl-muted)", fontSize: 13, padding: "1.5rem 0", textAlign: "center" }}>
      {text}
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
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid var(--cl-border)",
  color: "var(--cl-text)",
  cursor: "pointer",
  fontSize: 13,
  textAlign: "left",
};

const hotspotRow: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "40px 1fr auto auto",
  gap: 12,
  alignItems: "center",
  padding: "8px 10px",
  borderRadius: 8,
  background: "rgba(11,18,32,0.45)",
  fontSize: 13,
};
