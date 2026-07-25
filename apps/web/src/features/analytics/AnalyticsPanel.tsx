"use client";

import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import type { EChartsOption } from "echarts";

import {
  fetchBreakdown,
  fetchCorrelation,
  fetchCorrelations,
  fetchTrends,
  type BreakdownItem,
  type CorrelationResult,
  type CorrelationSummary,
  type TrendSeries,
} from "@/features/analytics/api";
import { Chart } from "@/shared/ui/Chart";

const INDICATORS = [
  { code: "unemployment_rate", label: "Unemployment rate" },
  { code: "literacy_rate", label: "Literacy rate" },
  { code: "population_density", label: "Population density" },
  { code: "poverty_index", label: "Poverty index" },
  { code: "urban_pct", label: "Urban %" },
];

export function AnalyticsPanel() {
  const [indicator, setIndicator] = useState("unemployment_rate");
  const [series, setSeries] = useState<TrendSeries[]>([]);
  const [offense, setOffense] = useState<BreakdownItem[]>([]);
  const [severity, setSeverity] = useState<BreakdownItem[]>([]);
  const [corr, setCorr] = useState<CorrelationResult | null>(null);
  const [ranked, setRanked] = useState<CorrelationSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [trends, byOffense, bySev, correlation, correlations] = await Promise.all([
          fetchTrends(),
          fetchBreakdown("offense"),
          fetchBreakdown("severity"),
          fetchCorrelation(indicator),
          fetchCorrelations(),
        ]);
        if (!cancelled) {
          setSeries(trends.series);
          setOffense(byOffense.items);
          setSeverity(bySev.items);
          setCorr(correlation);
          setRanked(correlations);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load analytics");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [indicator]);

  const points = series[0]?.points ?? [];

  const trendOption: EChartsOption = {
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 16, top: 24, bottom: 32 },
    xAxis: {
      type: "category",
      data: points.map((p) => p.bucket_start.slice(5)),
      axisLabel: { color: "#9aa8c7" },
      axisLine: { lineStyle: { color: "#243049" } },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      splitLine: { lineStyle: { color: "#243049" } },
      axisLabel: { color: "#9aa8c7" },
    },
    series: [
      {
        type: "bar",
        data: points.map((p) => p.count),
        itemStyle: { color: "#3d8bfd", borderRadius: [4, 4, 0, 0] },
      },
    ],
  };

  const offenseOption: EChartsOption = {
    tooltip: { trigger: "axis" },
    grid: { left: 110, right: 24, top: 12, bottom: 24 },
    xAxis: {
      type: "value",
      minInterval: 1,
      splitLine: { lineStyle: { color: "#243049" } },
      axisLabel: { color: "#9aa8c7" },
    },
    yAxis: {
      type: "category",
      data: offense.map((o) => o.name).reverse(),
      axisLabel: { color: "#9aa8c7", width: 100, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        data: offense.map((o) => o.count).reverse(),
        itemStyle: { color: "#1f6feb", borderRadius: [0, 4, 4, 0] },
      },
    ],
  };

  const severityOption: EChartsOption = {
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        radius: ["40%", "68%"],
        label: { color: "#e8eefc" },
        data: severity.map((s) => ({ name: s.name, value: s.count })),
        color: ["#5ac8fa", "#ffcc00", "#ff9500", "#ff453a"],
      },
    ],
  };

  const scatterOption: EChartsOption = {
    tooltip: {
      trigger: "item",
      formatter: (params: unknown) => {
        const p = params as { data?: [number, number, string] };
        if (!p.data) return "";
        return `${p.data[2]}<br/>Indicator: ${p.data[0]}<br/>Crime: ${p.data[1]}`;
      },
    },
    grid: { left: 48, right: 24, top: 24, bottom: 40 },
    xAxis: {
      name: indicator,
      nameLocation: "middle",
      nameGap: 28,
      nameTextStyle: { color: "#9aa8c7" },
      splitLine: { lineStyle: { color: "#243049" } },
      axisLabel: { color: "#9aa8c7" },
    },
    yAxis: {
      name: corr?.crime_metric ?? "crime",
      nameTextStyle: { color: "#9aa8c7" },
      splitLine: { lineStyle: { color: "#243049" } },
      axisLabel: { color: "#9aa8c7" },
    },
    series: [
      {
        type: "scatter",
        symbolSize: 14,
        data: (corr?.points ?? []).map((pt) => [
          pt.indicator_value,
          pt.crime_value,
          pt.district_name,
        ]),
        itemStyle: { color: "#3d8bfd" },
      },
    ],
  };

  const rankedOption: EChartsOption = {
    tooltip: { trigger: "axis" },
    grid: { left: 130, right: 24, top: 12, bottom: 24 },
    xAxis: {
      type: "value",
      min: 0,
      max: 1,
      splitLine: { lineStyle: { color: "#243049" } },
      axisLabel: { color: "#9aa8c7" },
    },
    yAxis: {
      type: "category",
      data: ranked.map((r) => r.indicator_code).reverse(),
      axisLabel: { color: "#9aa8c7" },
    },
    series: [
      {
        type: "bar",
        data: ranked.map((r) => r.abs_coefficient ?? 0).reverse(),
        itemStyle: { color: "#ff9500", borderRadius: [0, 4, 4, 0] },
      },
    ],
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "end" }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <h1 style={{ margin: 0 }}>Analytics</h1>
          <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14 }}>
            Crime trends, offense mix, and socio-economic Pearson correlations.
          </p>
        </div>
        <label style={{ display: "grid", gap: 4, fontSize: 12, color: "var(--cl-muted)" }}>
          Socio indicator
          <select
            value={indicator}
            onChange={(e) => setIndicator(e.target.value)}
            style={selectStyle}
          >
            {INDICATORS.map((i) => (
              <option key={i.code} value={i.code}>
                {i.label}
              </option>
            ))}
          </select>
        </label>
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

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.3fr) minmax(0, 1fr)", gap: 12 }}>
        <Panel title="Incident trend (30d)">
          <Chart option={trendOption} height={260} loading={loading} />
        </Panel>
        <Panel title="Severity mix">
          <Chart option={severityOption} height={260} loading={loading} />
        </Panel>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 12 }}>
        <Panel title="Top offenses">
          <Chart option={offenseOption} height={280} loading={loading} />
        </Panel>
        <Panel
          title={
            corr
              ? `Correlation r=${corr.coefficient?.toFixed(3) ?? "n/a"} (${corr.interpretation})`
              : "Socio-economic scatter"
          }
        >
          <Chart option={scatterOption} height={280} loading={loading} />
        </Panel>
      </div>

      <Panel title="Ranked |r| across indicators">
        <Chart option={rankedOption} height={240} loading={loading} />
      </Panel>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={panelStyle}>
      <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>{title}</div>
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

const selectStyle: CSSProperties = {
  background: "var(--cl-surface)",
  color: "var(--cl-text)",
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "8px 10px",
  minWidth: 180,
};
