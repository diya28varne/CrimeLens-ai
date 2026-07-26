"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import type { EChartsOption } from "echarts";
import { useTranslation } from "react-i18next";

import {
  fetchBreakdown,
  fetchInsights,
  type AnalyticsFinding,
  type AnalyticsInsights,
  type BreakdownItem,
} from "@/features/analytics/api";
import { Chart } from "@/shared/ui/Chart";
import { useAppLocale } from "@/shared/i18n/useAppLocale";

const SEV_COLOR: Record<string, string> = {
  high: "#ff453a",
  medium: "#ff9500",
  low: "#5ac8fa",
};

/** Insights section for Dashboard — only the two most relevant charts. */
export function AnalyticsPanel({ embedded = false }: { embedded?: boolean }) {
  const { t } = useTranslation("analytics");
  const locale = useAppLocale();
  const [insights, setInsights] = useState<AnalyticsInsights | null>(null);
  const [offense, setOffense] = useState<BreakdownItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [ins, byOffense] = await Promise.all([
          fetchInsights(30),
          fetchBreakdown("offense"),
        ]);
        if (!cancelled) {
          setInsights(ins);
          setOffense(byOffense.items);
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
  }, [locale, t]);

  const current30d = t("charts.current30d");
  const priorAvg = t("charts.prior30dAvg");
  const spikeLabel = t("charts.spike");

  const compareOption: EChartsOption | null = insights
    ? {
        tooltip: { trigger: "axis" },
        legend: {
          data: [current30d, priorAvg],
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
            name: current30d,
            type: "line",
            smooth: true,
            data: insights.daily.map((d) => d.count),
            markPoint: insights.spikes.length
              ? {
                  symbol: "pin",
                  symbolSize: 42,
                  data: insights.spikes.slice(0, 3).map((s) => ({
                    name: spikeLabel,
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
            name: priorAvg,
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

  const pct = insights?.pct_change ?? 0;
  const deltaUp = pct > 0;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <header>
        {embedded ? (
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>{t("sectionTitle")}</h2>
        ) : (
          <h1 style={{ margin: 0 }}>{t("title")}</h1>
        )}
        <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14, maxWidth: 560 }}>
          {embedded ? t("sectionSubtitle") : t("subtitle")}
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

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 10,
        }}
      >
        <Metric
          label={t("metrics.vsPrior")}
          value={insights ? `${pct >= 0 ? "+" : ""}${pct}%` : "—"}
          hint={
            insights
              ? t("metrics.nowPrior", {
                  current: insights.current.total,
                  prior: insights.prior.total,
                })
              : loading
                ? "…"
                : "—"
          }
          accent={deltaUp ? "#ff453a" : "#32d74b"}
        />
        <Metric
          label={t("metrics.spikeDays")}
          value={insights ? String(insights.spikes.length) : "—"}
          hint={t("metrics.spikeHint")}
          accent="#ff9500"
        />
        <Metric
          label={t("metrics.peakHour")}
          value={insights ? `${String(insights.peak_hour.hour).padStart(2, "0")}:00` : "—"}
          hint={
            insights
              ? t("metrics.incidentsCount", { count: insights.peak_hour.count })
              : ""
          }
          accent="#3d8bfd"
        />
        <Metric
          label={t("metrics.topOffenseShare")}
          value={insights ? `${insights.concentration.top1_share_pct}%` : "—"}
          hint={insights?.concentration.top_offense?.name ?? ""}
          accent="#bf5af2"
        />
      </div>

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
          <div style={{ fontWeight: 600, fontSize: 14 }}>{t("findings.title")}</div>
          <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>
            {t("findings.autoDerived", { days: insights?.window_days ?? 30 })}
          </div>
        </div>
        {loading && !insights ? (
          <p style={{ margin: 0, color: "var(--cl-muted)", fontSize: 13 }}>{t("findings.loading")}</p>
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
          <ActionLink href="/advisor">{t("actions.advisor")}</ActionLink>
          <ActionLink href="/map">{t("actions.map")}</ActionLink>
        </div>
      </section>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr)",
          gap: 12,
        }}
        className="cl-dash-two-charts"
      >
        <Panel title={t("charts.periodImpactShort")} subtitle={t("charts.periodHint")}>
          {compareOption ? (
            <Chart option={compareOption} height={300} loading={loading} />
          ) : (
            <Chart option={{}} height={300} loading={loading} />
          )}
        </Panel>
        <Panel
          title={t("charts.offenseConcentration")}
          subtitle={
            insights
              ? t("charts.top3", { pct: insights.concentration.top3_share_pct })
              : undefined
          }
        >
          <Chart option={offenseOption} height={300} loading={loading} />
        </Panel>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .cl-dash-two-charts { grid-template-columns: 1fr !important; }
        }
      `}</style>
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
