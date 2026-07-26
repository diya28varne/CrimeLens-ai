"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import type { EChartsOption } from "echarts";

import {
  fetchReportTemplates,
  generateReport,
  type IntelligenceReport,
  type ReportTemplate,
} from "@/features/reports/api";
import { Chart } from "@/shared/ui/Chart";
import { ApiError } from "@/shared/api/client";
import { useTranslation } from "react-i18next";
import { useAppLocale } from "@/shared/i18n/useAppLocale";

export function ReportsPanel() {
  const { t } = useTranslation("reports");
  const { t: tc } = useTranslation("common");
  const locale = useAppLocale();
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [templateId, setTemplateId] = useState("weekly");
  const [report, setReport] = useState<IntelligenceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [presenting, setPresenting] = useState(false);
  const [slide, setSlide] = useState(0);
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchReportTemplates();
        if (!cancelled) {
          setTemplates(res.data);
          if (res.data[0]) setTemplateId(res.data[0].id);
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError && e.status === 401
              ? tc("signInRequired")
              : e instanceof Error
                ? e.message
                : t("errorTemplates"),
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t, tc]);

  async function onGenerate() {
    setLoading(true);
    setError(null);
    setPresenting(false);
    try {
      const res = await generateReport({ template_id: templateId, locale });
      setReport(res.data);
      setChecked({});
      setSlide(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("errorLoad"));
    } finally {
      setLoading(false);
    }
  }

  const trendOption: EChartsOption | null = useMemo(() => {
    if (!report) return null;
    return {
      tooltip: { trigger: "axis" },
      grid: { left: 40, right: 16, top: 24, bottom: 32 },
      xAxis: {
        type: "category",
        data: report.overview.trend_daily.map((d) => d.date.slice(5)),
        axisLabel: { color: "#9aa8c7" },
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
          data: report.overview.trend_daily.map((d) => d.count),
          areaStyle: { color: "rgba(61,139,253,0.15)" },
          lineStyle: { color: "#3d8bfd" },
          itemStyle: { color: "#3d8bfd" },
        },
      ],
    };
  }, [report]);

  const offenseOption: EChartsOption | null = useMemo(() => {
    if (!report?.overview.by_offense.length) return null;
    return {
      tooltip: { trigger: "item" },
      series: [
        {
          type: "pie",
          radius: ["35%", "65%"],
          data: report.overview.by_offense.map((o) => ({ name: o.name, value: o.count })),
          label: { color: "#9aa8c7" },
        },
      ],
    };
  }, [report]);

  const slides = report?.presenter_script ?? [];
  const currentSlide = slides[slide];

  return (
    <div style={{ display: "grid", gap: 14, maxWidth: 980 }}>
      <header className="no-print" style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>{t("title")}</h1>
          <p style={{ margin: "4px 0 0", color: "var(--cl-muted)", fontSize: 13 }}>
            {t("subtitle")} {t("languageNote")}
          </p>
        </div>
      </header>

      <section className="no-print" style={panelStyle}>
        <div style={sectionTitle}>{t("template")}</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 10 }}>
          {templates.map((tmpl) => {
            const on = templateId === tmpl.id;
            return (
              <button
                key={tmpl.id}
                type="button"
                onClick={() => setTemplateId(tmpl.id)}
                style={{
                  textAlign: "left",
                  padding: 12,
                  borderRadius: 10,
                  border: on ? "1px solid var(--cl-accent)" : "1px solid var(--cl-border)",
                  background: on ? "rgba(61,139,253,0.12)" : "transparent",
                  color: "var(--cl-text)",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 14 }}>{tmpl.name}</div>
                <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 4 }}>{tmpl.description}</div>
              </button>
            );
          })}
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
          <button type="button" onClick={() => void onGenerate()} disabled={loading} style={primaryBtn}>
            {loading ? t("generating") : t("generate")}
          </button>
          {report ? (
            <>
              <button type="button" onClick={() => window.print()} style={ghostBtn}>
                {t("print")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setPresenting(true);
                  setSlide(0);
                }}
                style={ghostBtn}
              >
                {t("present")}
              </button>
            </>
          ) : null}
        </div>
        {error ? <div style={{ color: "#ff8e8e", marginTop: 10, fontSize: 13 }}>{error}</div> : null}
      </section>

      {report ? (
        <article id="intelligence-report" style={{ display: "grid", gap: 14 }}>
          {/* Cover */}
          <section style={{ ...panelStyle, textAlign: "center", padding: "36px 24px" }}>
            <div style={{ letterSpacing: "0.2em", fontSize: 12, color: "var(--cl-muted)" }}>
              {report.cover.classification.toUpperCase()}
            </div>
            <h2 style={{ margin: "12px 0 6px", fontSize: 28 }}>{report.cover.title}</h2>
            <div style={{ fontSize: 16, color: "var(--cl-muted)" }}>{report.cover.subtitle}</div>
            <div style={{ marginTop: 20, fontSize: 14 }}>
              Prepared for <strong>{report.cover.prepared_for}</strong>
            </div>
            <div style={{ marginTop: 8, fontSize: 13, color: "var(--cl-muted)" }}>
              {report.cover.report_type} · {report.cover.date_label}
              <br />
              Range {report.cover.range_label}
            </div>
          </section>

          <div style={disclaimerStyle}>{report.disclaimer}</div>

          <Section title={t("sections.executiveSummary")}>
            <p style={{ margin: 0, lineHeight: 1.6, fontSize: 14 }}>{report.executive_summary}</p>
          </Section>

          <Section title={t("sections.overview")}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(120px,1fr))", gap: 10, marginBottom: 12 }}>
              <Stat label={t("stats.totalCrimes")} value={String(report.overview.total_incidents)} />
              <Stat
                label={t("stats.vsPrior")}
                value={
                  report.overview.delta_pct == null
                    ? "—"
                    : `${report.overview.delta_pct >= 0 ? "+" : ""}${report.overview.delta_pct}%`
                }
              />
              <Stat label={t("stats.open")} value={String(report.overview.open_incidents)} />
              <Stat label={t("stats.highCritical")} value={String(report.overview.high_severity)} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 12 }} className="report-charts">
              <div>
                <div style={{ fontSize: 12, color: "var(--cl-muted)", marginBottom: 6 }}>{t("charts.trend")}</div>
                <Chart option={trendOption} height={220} />
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--cl-muted)", marginBottom: 6 }}>{t("charts.offenseMix")}</div>
                <Chart option={offenseOption} height={220} />
              </div>
            </div>
          </Section>

          <Section title={t("sections.insights")}>
            <div style={{ display: "grid", gap: 8 }}>
              {report.insights.map((i) => (
                <div key={i.title} style={cardStyle}>
                  <KindBadge kind={i.kind} />
                  <strong style={{ display: "block", marginTop: 6 }}>{i.title}</strong>
                  <p style={{ margin: "6px 0 0", fontSize: 13, lineHeight: 1.45 }}>{i.body}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section title={t("sections.hotspots")}>
            <div style={{ display: "grid", gap: 8 }}>
              {report.hotspots.map((h) => (
                <div key={h.label} style={cardStyle}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                    <strong>{h.label}</strong>
                    <span style={{ fontSize: 12, color: "var(--cl-muted)" }}>
                      {h.risk_level} · {(h.score * 100).toFixed(0)}% · {t("confShort", { pct: Math.round(h.confidence * 100) })}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 4 }}>
                    {t("factors")}: {h.factors.join(" · ")}
                  </div>
                  <div style={{ fontSize: 13, marginTop: 6 }}>{h.suggested_action}</div>
                </div>
              ))}
            </div>
          </Section>

          <Section title={t("sections.predictions")}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 8 }}>
              {report.predictions.map((p) => (
                <div key={p.scope_name} style={cardStyle}>
                  <KindBadge kind="forecast" />
                  <div style={{ fontWeight: 600, marginTop: 6 }}>{p.scope_name}</div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{(p.risk_score * 100).toFixed(0)}%</div>
                  <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>
                    {p.risk_band} · {t("confidencePct", { pct: Math.round(p.confidence * 100) })}
                  </div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>{p.note}</div>
                </div>
              ))}
            </div>
          </Section>

          {report.xai_summary ? (
            <Section title={t("sections.xai")}>
              <p style={{ margin: "0 0 8px", fontSize: 14, lineHeight: 1.5 }}>{report.xai_summary.summary}</p>
              <div style={{ fontSize: 13 }}>
                <strong>{t("primaryDrivers")}</strong> {report.xai_summary.top_factors.join(" · ")}
              </div>
              <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 6 }}>
                {t("scopeConfidence", {
                  scope: report.xai_summary.scope_name,
                  pct: Math.round(report.xai_summary.confidence * 100),
                })}
              </div>
              <Link className="no-print" href="/explain" style={{ color: "var(--cl-accent)", fontSize: 13 }}>
                {t("openDecisionCard")}
              </Link>
            </Section>
          ) : null}

          <Section title={t("sections.recommendations")}>
            <div style={{ display: "grid", gap: 8 }}>
              {report.recommendations.map((r) => (
                <div key={r.title} style={cardStyle}>
                  <div style={{ fontSize: 11, color: "var(--cl-muted)", textTransform: "uppercase" }}>
                    {r.priority} · {Math.round(r.confidence * 100)}%
                  </div>
                  <strong>{r.title}</strong>
                  <p style={{ margin: "6px 0 0", fontSize: 13 }}>{r.rationale}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section title={t("sections.resources")}>
            <div style={{ display: "grid", gap: 8 }}>
              {report.resource_plan.map((r) => (
                <div key={r.division} style={{ ...cardStyle, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{r.division}</div>
                    <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>{r.note}</div>
                  </div>
                  <div style={{ fontWeight: 700, textAlign: "right" }}>{r.change}</div>
                </div>
              ))}
            </div>
          </Section>

          <Section title={t("sections.checklist")}>
            <div style={{ display: "grid", gap: 8 }}>
              {report.checklist.map((c) => (
                <label key={c.id} style={{ ...cardStyle, display: "flex", gap: 10, alignItems: "flex-start", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={!!checked[c.id]}
                    onChange={(e) => setChecked((prev) => ({ ...prev, [c.id]: e.target.checked }))}
                  />
                  <span style={{ fontSize: 13 }}>{c.text}</span>
                </label>
              ))}
            </div>
          </Section>

          <p style={{ fontSize: 11, color: "var(--cl-muted)" }}>
            Generated {new Date(report.generated_at).toLocaleString()} · report id {report.id.slice(0, 8)}…
          </p>
        </article>
      ) : null}

      {presenting && report && currentSlide ? (
        <div className="no-print" style={presentOverlay}>
          <div style={presentCard}>
            <div style={{ fontSize: 11, letterSpacing: "0.12em", color: "var(--cl-muted)", textTransform: "uppercase" }}>
              Interactive briefing · {slide + 1}/{slides.length}
            </div>
            <h2 style={{ margin: "10px 0" }}>{currentSlide.title}</h2>
            <p style={{ fontSize: 16, lineHeight: 1.55, margin: 0 }}>{currentSlide.narration}</p>
            <div style={{ display: "flex", gap: 8, marginTop: 20, flexWrap: "wrap" }}>
              <button type="button" style={ghostBtn} disabled={slide === 0} onClick={() => setSlide((s) => s - 1)}>
                Previous
              </button>
              <button
                type="button"
                style={primaryBtn}
                onClick={() => {
                  if (slide >= slides.length - 1) setPresenting(false);
                  else setSlide((s) => s + 1);
                }}
              >
                {slide >= slides.length - 1 ? "End briefing" : "Next"}
              </button>
              {currentSlide.drill_href ? (
                <Link href={currentSlide.drill_href} style={{ ...ghostBtn, textDecoration: "none" }}>
                  Drill into evidence →
                </Link>
              ) : null}
              <button type="button" style={ghostBtn} onClick={() => setPresenting(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={panelStyle}>
      <h3 style={sectionTitle}>{title}</h3>
      {children}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: "var(--cl-muted)" }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}

function KindBadge({ kind }: { kind: "observed" | "forecast" }) {
  const observed = kind === "observed";
  return (
    <span
      style={{
        fontSize: 10,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        padding: "2px 6px",
        borderRadius: 6,
        border: observed ? "1px solid #2a6f6a" : "1px solid #6a5a2a",
        color: observed ? "#1abc9c" : "#f0c674",
      }}
    >
      {kind}
    </span>
  );
}

const panelStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  background: "rgba(18, 26, 43, 0.72)",
  padding: "14px 16px",
};

const sectionTitle: CSSProperties = {
  margin: "0 0 12px",
  fontSize: 12,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "var(--cl-muted)",
  fontWeight: 600,
};

const cardStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "10px 12px",
  background: "rgba(12,18,32,0.45)",
};

const primaryBtn: CSSProperties = {
  background: "var(--cl-accent)",
  color: "#fff",
  border: 0,
  borderRadius: 8,
  padding: "10px 14px",
  fontWeight: 600,
  cursor: "pointer",
};

const ghostBtn: CSSProperties = {
  background: "transparent",
  color: "var(--cl-text)",
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "10px 14px",
  cursor: "pointer",
  fontSize: 13,
};

const disclaimerStyle: CSSProperties = {
  fontSize: 12,
  color: "#f0c674",
  border: "1px solid #5a4a20",
  background: "rgba(90, 74, 32, 0.35)",
  borderRadius: 8,
  padding: "8px 10px",
};

const presentOverlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(5, 10, 20, 0.92)",
  zIndex: 1000,
  display: "grid",
  placeItems: "center",
  padding: 24,
};

const presentCard: CSSProperties = {
  width: "min(720px, 100%)",
  border: "1px solid var(--cl-border)",
  borderRadius: 16,
  background: "rgba(18, 26, 43, 0.98)",
  padding: 28,
};
