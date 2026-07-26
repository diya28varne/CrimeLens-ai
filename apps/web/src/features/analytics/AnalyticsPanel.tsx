"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import type { EChartsOption } from "echarts";

import {
  fetchBreakdown,
  fetchCorrelation,
  fetchCorrelations,
  fetchInsights,
  type AnalyticsFinding,
  type AnalyticsInsights,
  type BreakdownItem,
  type CorrelationResult,
  type CorrelationSummary,
} from "@/features/analytics/api";
import { Chart } from "@/shared/ui/Chart";
import { useTranslation } from "react-i18next";
import { useAppLocale } from "@/shared/i18n/useAppLocale";

const INDICATORS = [
  { code: "unemployment_rate", label: "Unemployment rate" },
  { code: "literacy_rate", label: "Literacy rate" },
  { code: "population_density", label: "Population density" },
  { code: "poverty_index", label: "Poverty index" },
  { code: "urban_pct", label: "Urban %" },
];

const SEV_COLOR: Record<string, string> = {
  high: "#ff453a",
  medium: "#ff9500",
  low: "#5ac8fa",
};

export function AnalyticsPanel() {
  const { t } = useTranslation("analytics");
  const locale = useAppLocale();
  const [indicator, setIndicator] = useState("unemployment_rate");
  const [insights, setInsights] = useState<AnalyticsInsights | null>(null);
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
        const [ins, byOffense, bySev, correlation, correlations] = await Promise.all([
          fetchInsights(30),
          fetchBreakdown("offense"),
          fetchBreakdown("severity"),
          fetchCorrelation(indicator),
          fetchCorrelations(),
        ]);
        if (!cancelled) {
          setInsights(ins);
          setOffense(byOffense.items);
          setSeverity(bySev.items);
          setCorr(correlation);
          setRanked(correlations);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : t("errorLoad"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [indicator, locale, t]);

  const hourOption: EChartsOption = {
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 16, top: 24, bottom: 32 },
    xAxis: {
      type: "category",
      data: (insights?.by_hour ?? []).map((h) => `${String(h.hour).padStart(2, "0")}`),
      axisLabel: { color: "#9aa8c7", interval: 3 },
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
        data: (insights?.by_hour ?? []).map((h) => {
          const peak = insights?.peak_hour.hour ?? -1;
          return {
            value: h.count,
            itemStyle: {
              color: h.hour === peak ? "#ff9500" : "#3d8bfd",
              borderRadius: [3, 3, 0, 0],
            },
          };
        }),
      },
    ],
  };

  const dowOption: EChartsOption = {
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    xAxis: {
      type: "category",
      data: (insights?.by_dow ?? []).map((d) => d.label),
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
        data: (insights?.by_dow ?? []).map((d) => ({
          value: d.count,
          itemStyle: {
            color: d.dow === 0 || d.dow === 6 ? "#ff9500" : "#1f6feb",
            borderRadius: [4, 4, 0, 0],
          },
        })),
      },
    ],
  };

  const compareOption: EChartsOption | null = insights
    ? {
        tooltip: { trigger: "axis" },
        legend: {
          data: ["Current 30d", "Prior 30d (total)"],
          textStyle: { color: "#9aa8c7" },
          top: 0,
        },
        grid: { left: 44, right: 16, top: 36, bottom: 32 },
        xAxis: {
          type: "category",
          data: insights.daily.map((d) => d.date.slice(5)),
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
            name: "Current 30d",
            type: "line",
            smooth: true,
            data: insights.daily.map((d) => d.count),
            markPoint: insights.spikes.length
              ? {
                  symbol: "pin",
                  symbolSize: 42,
                  data: insights.spikes.slice(0, 3).map((s) => ({
                    name: "Spike",
                    coord: [s.date.slice(5), s.count],
                    value: s.count,
                    itemStyle: { color: "#ff453a" },
                  })),
                }
              : undefined,
            areaStyle: { color: "rgba(61, 139, 253, 0.14)" },
            lineStyle: { color: "#3d8bfd", width: 2 },
            itemStyle: { color: "#3d8bfd" },
          },
          {
            name: "Prior 30d (total)",
            type: "line",
            data: insights.daily.map(() =>
              insights.daily.length
                ? Math.round((insights.prior.total / insights.daily.length) * 10) / 10
                : 0,
            ),
            lineStyle: { type: "dashed", color: "#9aa8c7", width: 1.5 },
            itemStyle: { color: "#9aa8c7" },
            symbol: "none",
          },
        ],
      }
    : null;

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

  const topCorr = ranked[0];
  const pct = insights?.pct_change ?? 0;
  const deltaUp = pct > 0;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "end" }}>
        <div style={{ flex: 1, minWidth: 260 }}>
          <h1 style={{ margin: 0 }}>{t("title")}</h1>
          <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14, maxWidth: 560 }}>
            {t("subtitle")}
          </p>
        </div>
        <label style={{ display: "grid", gap: 4, fontSize: 12, color: "var(--cl-muted)" }}>
          {t("socioIndicator")}
          <select
            value={indicator}
            onChange={(e) => setIndicator(e.target.value)}
            style={selectStyle}
          >
            {INDICATORS.map((i) => (
              <option key={i.code} value={i.code}>
                {t(`indicators.${i.code}`)}
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

      {/* Impact KPIs — not duplicated Dashboard counts */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 10,
        }}
      >
        <Metric
          label="vs prior 30d"
          value={insights ? `${pct >= 0 ? "+" : ""}${pct}%` : "—"}
          hint={
            insights
              ? `${insights.current.total} now · ${insights.prior.total} prior`
              : loading
                ? "…"
                : "—"
          }
          accent={deltaUp ? "#ff453a" : "#32d74b"}
        />
        <Metric
          label="Spike days"
          value={insights ? String(insights.spikes.length) : "—"}
          hint="days above mean+1.5σ"
          accent="#ff9500"
        />
        <Metric
          label="Peak hour"
          value={
            insights
              ? `${String(insights.peak_hour.hour).padStart(2, "0")}:00`
              : "—"
          }
          hint={insights ? `${insights.peak_hour.count} incidents` : ""}
          accent="#3d8bfd"
        />
        <Metric
          label="Top offense share"
          value={
            insights ? `${insights.concentration.top1_share_pct}%` : "—"
          }
          hint={insights?.concentration.top_offense?.name ?? ""}
          accent="#bf5af2"
        />
        <Metric
          label="High/critical"
          value={
            insights ? `${insights.severity.high_critical_share_pct}%` : "—"
          }
          hint={
            insights
              ? `${insights.severity.high_critical_count} incidents`
              : ""
          }
          accent="#ff453a"
        />
        <Metric
          label="Offense mix"
          value={insights?.concentration.label ?? "—"}
          hint={insights ? `HHI ${insights.concentration.hhi}` : ""}
          accent="#5ac8fa"
        />
      </div>

      {/* Analyst findings */}
      <section style={panelStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            gap: 12,
            marginBottom: 10,
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 14 }}>Analyst findings</div>
          <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>
            Auto-derived from the last {insights?.window_days ?? 30} days
          </div>
        </div>
        {loading && !insights ? (
          <p style={{ margin: 0, color: "var(--cl-muted)", fontSize: 13 }}>Loading findings…</p>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {(insights?.findings ?? []).map((f) => (
              <FindingRow key={f.id} finding={f} />
            ))}
          </div>
        )}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            marginTop: 14,
            paddingTop: 12,
            borderTop: "1px solid var(--cl-border)",
          }}
        >
          <ActionLink href="/advisor">Open Advisor →</ActionLink>
          <ActionLink href="/explain">Explain model →</ActionLink>
          <ActionLink href="/story">Story playback →</ActionLink>
          <ActionLink href="/map">Map / hotspots →</ActionLink>
        </div>
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr)", gap: 12 }}>
        <Panel
          title="Period impact — current vs prior baseline"
          subtitle="Spikes marked · dashed line = prior-period daily average"
        >
          {compareOption ? (
            <Chart option={compareOption} height={280} loading={loading} />
          ) : (
            <Chart option={{}} height={280} loading={loading} />
          )}
        </Panel>
        <Panel title="Weekday vs weekend intensity" subtitle="Orange = weekend">
          <Chart option={dowOption} height={280} loading={loading} />
          {insights && (
            <div
              style={{
                display: "flex",
                gap: 16,
                marginTop: 8,
                fontSize: 12,
                color: "var(--cl-muted)",
              }}
            >
              <span>
                Weekday ~{insights.weekday.per_day}/day
              </span>
              <span>
                Weekend ~{insights.weekend.per_day}/day
              </span>
            </div>
          )}
        </Panel>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 12 }}>
        <Panel title="Hour-of-day pattern" subtitle="Peak hour highlighted">
          <Chart option={hourOption} height={240} loading={loading} />
        </Panel>
        <Panel title="Severity mix">
          <Chart option={severityOption} height={240} loading={loading} />
        </Panel>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 12 }}>
        <Panel
          title="Offense concentration"
          subtitle={
            insights
              ? `Top-3 = ${insights.concentration.top3_share_pct}% of volume`
              : undefined
          }
        >
          <Chart option={offenseOption} height={280} loading={loading} />
        </Panel>
        <Panel
          title={
            corr
              ? `Socio driver · r=${corr.coefficient?.toFixed(3) ?? "n/a"} (${corr.interpretation})`
              : "Socio-economic scatter"
          }
          subtitle="District-level Pearson correlation — not shown on Dashboard"
        >
          <Chart option={scatterOption} height={280} loading={loading} />
          {topCorr && (
            <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--cl-muted)" }}>
              Strongest |r| overall: <strong style={{ color: "var(--cl-text)" }}>{topCorr.indicator_code}</strong>{" "}
              ({topCorr.abs_coefficient?.toFixed(3)}, {topCorr.interpretation}). Use Advisor to turn this into
              deployment guidance.
            </p>
          )}
        </Panel>
      </div>

      <Panel title="Ranked |r| across socio-economic indicators">
        <Chart option={rankedOption} height={240} loading={loading} />
      </Panel>
    </div>
  );
}

function FindingRow({ finding }: { finding: AnalyticsFinding }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "8px 1fr",
        gap: 10,
        alignItems: "start",
        padding: "10px 12px",
        borderRadius: 10,
        background: "rgba(255,255,255,0.03)",
        border: "1px solid var(--cl-border)",
      }}
    >
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: 99,
          marginTop: 5,
          background: SEV_COLOR[finding.severity] ?? SEV_COLOR.low,
        }}
      />
      <div>
        <div style={{ fontWeight: 600, fontSize: 13 }}>{finding.title}</div>
        <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 2, lineHeight: 1.45 }}>
          {finding.detail}
        </div>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint: string;
  accent: string;
}) {
  return (
    <div
      style={{
        ...panelStyle,
        padding: "12px 14px",
        borderTop: `3px solid ${accent}`,
      }}
    >
      <div style={{ fontSize: 11, color: "var(--cl-muted)", textTransform: "uppercase", letterSpacing: 0.4 }}>
        {label}
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, marginTop: 4, color: accent }}>{value}</div>
      {hint ? (
        <div style={{ fontSize: 11, color: "var(--cl-muted)", marginTop: 4, lineHeight: 1.3 }}>{hint}</div>
      ) : null}
    </div>
  );
}

function ActionLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      style={{
        fontSize: 12,
        color: "#3d8bfd",
        textDecoration: "none",
        padding: "6px 10px",
        borderRadius: 8,
        border: "1px solid var(--cl-border)",
        background: "rgba(61,139,253,0.08)",
      }}
    >
      {children}
    </Link>
  );
}

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div style={panelStyle}>
      <div style={{ fontWeight: 600, marginBottom: subtitle ? 2 : 8, fontSize: 14 }}>{title}</div>
      {subtitle ? (
        <div style={{ fontSize: 11, color: "var(--cl-muted)", marginBottom: 8 }}>{subtitle}</div>
      ) : null}
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
