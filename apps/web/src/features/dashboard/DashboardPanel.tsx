"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import type { EChartsOption } from "echarts";

import {
  fetchDashboardAlerts,
  fetchDashboardOverview,
  type DashboardAlert,
  type DashboardOverview,
} from "@/features/dashboard/api";
import { Chart } from "@/shared/ui/Chart";

export function DashboardPanel() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [alerts, setAlerts] = useState<DashboardAlert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [ov, al] = await Promise.all([
          fetchDashboardOverview(),
          fetchDashboardAlerts(),
        ]);
        if (!cancelled) {
          setOverview(ov);
          setAlerts(al);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load dashboard");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const trendOption: EChartsOption | null = overview
    ? {
        tooltip: { trigger: "axis" },
        grid: { left: 40, right: 16, top: 24, bottom: 32 },
        xAxis: {
          type: "category",
          data: overview.trend_daily.map((d) => d.date.slice(5)),
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
            type: "line",
            smooth: true,
            data: overview.trend_daily.map((d) => d.count),
            areaStyle: { color: "rgba(61, 139, 253, 0.18)" },
            lineStyle: { color: "#3d8bfd", width: 2 },
            itemStyle: { color: "#3d8bfd" },
          },
        ],
      }
    : null;

  const severityOption: EChartsOption | null = overview
    ? {
        tooltip: { trigger: "item" },
        series: [
          {
            type: "pie",
            radius: ["42%", "68%"],
            label: { color: "#e8eefc" },
            data: overview.by_severity.map((s) => ({
              name: s.name,
              value: s.count,
            })),
            color: ["#5ac8fa", "#ffcc00", "#ff9500", "#ff453a"],
          },
        ],
      }
    : null;

  const offenseOption: EChartsOption | null = overview
    ? {
        tooltip: { trigger: "axis" },
        grid: { left: 100, right: 24, top: 16, bottom: 24 },
        xAxis: {
          type: "value",
          minInterval: 1,
          splitLine: { lineStyle: { color: "#243049" } },
          axisLabel: { color: "#9aa8c7" },
        },
        yAxis: {
          type: "category",
          data: overview.by_offense_top.map((o) => o.name).reverse(),
          axisLabel: { color: "#9aa8c7", width: 90, overflow: "truncate" },
        },
        series: [
          {
            type: "bar",
            data: overview.by_offense_top.map((o) => o.count).reverse(),
            itemStyle: { color: "#1f6feb", borderRadius: [0, 4, 4, 0] },
          },
        ],
      }
    : null;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <header>
        <h1 style={{ margin: 0 }}>Dashboard</h1>
        <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14 }}>
          Live incident KPIs for the last 30 days.{" "}
          <Link href="/map" style={{ color: "var(--cl-accent)" }}>
            Open map
          </Link>
        </p>
      </header>

      {error && (
        <div style={bannerStyle("#ff453a")}>
          {error}. Sign in if needed — dashboard requires analytics read.
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
        }}
      >
        <Kpi
          label="Total incidents"
          value={overview?.kpis.total_incidents}
          delta={overview?.kpis.total_incidents_delta_pct}
          loading={loading}
        />
        <Kpi label="Open cases" value={overview?.kpis.open_incidents} loading={loading} />
        <Kpi label="High / critical" value={overview?.kpis.high_severity} loading={loading} />
        <Kpi
          label="Hotspots"
          value={overview?.kpis.hotspot_count}
          hint="Prediction module"
          loading={loading}
        />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr)",
          gap: 12,
        }}
        className="cl-dash-charts"
      >
        <Panel title="Daily trend">
          {trendOption ? <Chart option={trendOption} height={260} loading={loading} /> : <Empty />}
        </Panel>
        <Panel title="By severity">
          {severityOption ? (
            <Chart option={severityOption} height={260} loading={loading} />
          ) : (
            <Empty />
          )}
        </Panel>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.2fr) minmax(0, 1fr)",
          gap: 12,
        }}
      >
        <Panel title="Top offenses">
          {offenseOption ? (
            <Chart option={offenseOption} height={240} loading={loading} />
          ) : (
            <Empty />
          )}
        </Panel>
        <Panel title="Alerts">
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 10 }}>
            {alerts.map((a) => (
              <li key={a.id} style={alertItemStyle(a.severity)}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{a.title}</div>
                <div style={{ color: "var(--cl-muted)", fontSize: 13, marginTop: 4 }}>{a.body}</div>
                {a.href && (
                  <Link href={a.href} style={{ color: "var(--cl-accent)", fontSize: 12 }}>
                    Investigate →
                  </Link>
                )}
              </li>
            ))}
            {!loading && alerts.length === 0 && <Empty />}
          </ul>
        </Panel>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .cl-dash-charts { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}

function Kpi({
  label,
  value,
  delta,
  hint,
  loading,
}: {
  label: string;
  value?: number;
  delta?: number | null;
  hint?: string;
  loading?: boolean;
}) {
  return (
    <div style={panelStyle}>
      <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, marginTop: 6 }}>
        {loading && value == null ? "…" : (value ?? "—")}
      </div>
      {delta != null && (
        <div
          style={{
            fontSize: 12,
            marginTop: 4,
            color: delta >= 0 ? "#ff9500" : "#34c759",
          }}
        >
          {delta >= 0 ? "+" : ""}
          {delta}% vs prior window
        </div>
      )}
      {hint && (
        <div style={{ fontSize: 11, color: "var(--cl-muted)", marginTop: 4 }}>{hint}</div>
      )}
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

function Empty() {
  return (
    <div style={{ color: "var(--cl-muted)", fontSize: 13, padding: "2rem 0", textAlign: "center" }}>
      No data in window
    </div>
  );
}

const panelStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  background: "rgba(18, 26, 43, 0.72)",
  padding: "14px 16px",
};

function bannerStyle(color: string): CSSProperties {
  return {
    border: `1px solid ${color}`,
    borderRadius: 10,
    padding: "10px 12px",
    color: "var(--cl-text)",
    background: "rgba(255,69,58,0.08)",
    fontSize: 14,
  };
}

function alertItemStyle(severity: string): CSSProperties {
  const accent =
    severity === "critical"
      ? "#ff453a"
      : severity === "warning"
        ? "#ff9500"
        : "var(--cl-accent)";
  return {
    borderLeft: `3px solid ${accent}`,
    padding: "8px 10px",
    background: "rgba(11, 18, 32, 0.45)",
    borderRadius: 6,
  };
}
