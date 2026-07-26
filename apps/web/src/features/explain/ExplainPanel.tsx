"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import type { EChartsOption } from "echarts";

import { fetchCurrentPredictions, type PredictionValue } from "@/features/prediction/api";
import {
  fetchAuditTrail,
  fetchDecisionCard,
  type AuditRecord,
  type DecisionCard,
} from "@/features/explain/api";
import { Chart } from "@/shared/ui/Chart";
import { ApiError } from "@/shared/api/client";

type Props = {
  initialValueId?: string | null;
  /** Link to full Story playback (combined hub). */
  storyHref?: string;
};

export function ExplainPanel({ initialValueId = null, storyHref = "/explain?view=story" }: Props) {
  const [values, setValues] = useState<PredictionValue[]>([]);
  const [selected, setSelected] = useState<string | null>(initialValueId);
  const [card, setCard] = useState<DecisionCard | null>(null);
  const [audit, setAudit] = useState<AuditRecord[]>([]);
  const [showEvidence, setShowEvidence] = useState(false);
  const [activeScenario, setActiveScenario] = useState<string>("current");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const pred = await fetchCurrentPredictions();
        if (cancelled) return;
        setValues(pred.data.values);
        const first = initialValueId && pred.data.values.some((v) => v.id === initialValueId)
          ? initialValueId
          : pred.data.values[0]?.id ?? null;
        setSelected(first);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError && e.status === 401
              ? "Sign in required — open /login with seeded admin credentials."
              : e instanceof Error
                ? e.message
                : "Failed to load predictions",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialValueId]);

  const loadCard = useCallback(async (valueId: string) => {
    setError(null);
    try {
      const [res, aud] = await Promise.all([fetchDecisionCard(valueId), fetchAuditTrail()]);
      setCard(res.data);
      setAudit(aud.data);
      setActiveScenario("current");
      setShowEvidence(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load decision card");
      setCard(null);
    }
  }, []);

  useEffect(() => {
    if (selected) void loadCard(selected);
  }, [selected, loadCard]);

  const factorOption: EChartsOption | null = useMemo(() => {
    if (!card?.factors.length) return null;
    const factors = [...card.factors].reverse();
    return {
      tooltip: { trigger: "axis" },
      grid: { left: 140, right: 24, top: 12, bottom: 24 },
      xAxis: {
        type: "value",
        max: 100,
        axisLabel: { color: "#9aa8c7", formatter: "{value}%" },
        splitLine: { lineStyle: { color: "#243049" } },
      },
      yAxis: {
        type: "category",
        data: factors.map((f) => f.label),
        axisLabel: { color: "#9aa8c7", width: 130, overflow: "truncate" },
      },
      series: [
        {
          type: "bar",
          data: factors.map((f) => f.share_pct),
          itemStyle: { color: "#3d8bfd", borderRadius: [0, 4, 4, 0] },
        },
      ],
    };
  }, [card]);

  const active = card?.scenarios.find((s) => s.id === activeScenario) ?? card?.scenarios[0];

  return (
    <div style={{ display: "grid", gap: 14, maxWidth: 1100 }}>
      <header style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Explainable AI Decision Engine</h1>
          <p style={{ margin: "4px 0 0", color: "var(--cl-muted)", fontSize: 13 }}>
            Don’t just predict — prove it. Decision cards with factors, evidence, and audit trail.
            Open Story to replay how patterns evolved over time.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <Link href={storyHref} style={storyLinkBtn}>
            Open Story playback →
          </Link>
          <Link href="/prediction" style={linkBtn}>
            Back to Prediction
          </Link>
        </div>
      </header>

      <div style={disclaimerStyle}>
        {card?.disclaimer ??
          "Factors are model estimates — not proof of causation. Humans retain operational authority."}
      </div>

      {error ? <div style={{ color: "#ff8e8e", fontSize: 13 }}>{error}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "220px minmax(0,1fr)", gap: 12 }}>
        <aside style={panelStyle}>
          <div style={sectionTitle}>Select prediction</div>
          {loading ? <div style={{ color: "var(--cl-muted)", fontSize: 13 }}>Loading…</div> : null}
          <div style={{ display: "grid", gap: 6 }}>
            {values.map((v) => {
              const name = String(v.properties.station_name ?? "Station");
              const on = selected === v.id;
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => setSelected(v.id)}
                  style={{
                    textAlign: "left",
                    padding: "8px 10px",
                    borderRadius: 8,
                    border: on ? "1px solid var(--cl-accent)" : "1px solid var(--cl-border)",
                    background: on ? "rgba(61,139,253,0.12)" : "transparent",
                    color: "var(--cl-text)",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{name}</div>
                  <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>{v.value.toFixed(3)}</div>
                </button>
              );
            })}
          </div>
        </aside>

        <div style={{ display: "grid", gap: 12, minWidth: 0 }}>
          {card ? (
            <>
              <section style={panelStyle}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                  <div style={sectionTitle}>AI Decision Summary</div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <BandPill label={card.risk_band} />
                    <ConfPill band={card.confidence_band} value={card.confidence} />
                  </div>
                </div>
                <h2 style={{ margin: "0 0 8px", fontSize: 18 }}>{card.scope_name}</h2>
                <p style={{ margin: 0, lineHeight: 1.55, fontSize: 14 }}>{card.summary}</p>
                <div style={{ marginTop: 10, fontSize: 12, color: "var(--cl-muted)" }}>
                  Score {(card.risk_score * 100).toFixed(0)}% · model {card.model_version} · audit{" "}
                  {card.audit_id.slice(0, 8)}…
                </div>
              </section>

              <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.1fr) minmax(0,0.9fr)", gap: 12 }}>
                <section style={panelStyle}>
                  <div style={sectionTitle}>Why did the AI predict this?</div>
                  <Chart option={factorOption} height={240} />
                  <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
                    {card.factors.map((f) => (
                      <div key={f.feature} style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                        <span>{f.label}</span>
                        <strong>{f.share_pct.toFixed(0)}%</strong>
                      </div>
                    ))}
                  </div>
                </section>

                <section style={panelStyle}>
                  <div style={sectionTitle}>Confidence meter</div>
                  <div style={{ fontSize: 36, fontWeight: 700 }}>{Math.round(card.confidence * 100)}%</div>
                  <div style={{ color: "var(--cl-muted)", fontSize: 13, marginBottom: 12 }}>
                    {card.confidence_band} confidence
                  </div>
                  <div style={sectionTitle}>Recommendation</div>
                  {card.recommendation ? (
                    <>
                      <div style={{ fontWeight: 600, marginBottom: 6 }}>{card.recommendation.title}</div>
                      <ul style={{ margin: "0 0 8px", paddingLeft: 18, fontSize: 13 }}>
                        {card.recommendation.reasons.map((r) => (
                          <li key={r}>{r}</li>
                        ))}
                      </ul>
                      <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>
                        Expected risk reduction ~{card.recommendation.expected_risk_reduction_pct}% ·{" "}
                        {Math.round(card.recommendation.confidence * 100)}% confidence
                      </div>
                    </>
                  ) : (
                    <div style={{ color: "var(--cl-muted)", fontSize: 13 }}>No recommendation attached.</div>
                  )}
                </section>
              </div>

              <section style={panelStyle}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={sectionTitle}>Evidence Explorer</div>
                  <button type="button" style={ghostBtn} onClick={() => setShowEvidence((v) => !v)}>
                    {showEvidence ? "Hide evidence" : "View evidence"}
                  </button>
                </div>
                {showEvidence ? (
                  <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none", display: "grid", gap: 8 }}>
                    {card.evidence.map((e) => (
                      <li key={e.id} style={evidenceRow}>
                        <span style={{ color: "#1abc9c" }}>✓</span>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>{e.label}</div>
                          <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>{e.detail}</div>
                          {e.href ? (
                            <Link href={e.href} style={{ color: "var(--cl-accent)", fontSize: 12 }}>
                              Open
                            </Link>
                          ) : null}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ margin: 0, fontSize: 13, color: "var(--cl-muted)" }}>
                    Supporting evidence is traceable to analytics, hotspots, and the model run.
                  </p>
                )}
              </section>

              <section style={panelStyle}>
                <div style={sectionTitle}>Alternative scenarios (what-if)</div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))",
                    gap: 8,
                    marginBottom: 10,
                  }}
                >
                  {card.scenarios.map((s) => {
                    const on = activeScenario === s.id;
                    return (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => setActiveScenario(s.id)}
                        style={{
                          textAlign: "left",
                          padding: 10,
                          borderRadius: 8,
                          border: on ? "1px solid var(--cl-accent)" : "1px solid var(--cl-border)",
                          background: on ? "rgba(61,139,253,0.12)" : "rgba(12,18,32,0.45)",
                          color: "var(--cl-text)",
                          cursor: "pointer",
                        }}
                      >
                        <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>{s.label}</div>
                        <div style={{ fontSize: 20, fontWeight: 700 }}>{(s.risk_score * 100).toFixed(0)}%</div>
                        <div style={{ fontSize: 11, color: s.delta_pct <= 0 ? "#1abc9c" : "#e67e22" }}>
                          {s.delta_pct >= 0 ? "+" : ""}
                          {s.delta_pct}% vs current
                        </div>
                      </button>
                    );
                  })}
                </div>
                {active ? (
                  <p style={{ margin: 0, fontSize: 13, lineHeight: 1.45 }}>
                    <strong>{active.label}:</strong> {active.why}{" "}
                    <Link href="/simulation" style={{ color: "var(--cl-accent)" }}>
                      Open full Simulator →
                    </Link>
                  </p>
                ) : null}
              </section>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <section style={panelStyle}>
                  <div style={sectionTitle}>Explainability timeline</div>
                  <div style={{ display: "grid", gap: 6 }}>
                    {card.timeline.map((t) => (
                      <div key={t.day_label} style={timelineRow}>
                        <strong style={{ width: 36 }}>{t.day_label}</strong>
                        <div>
                          <div style={{ fontSize: 13 }}>{t.dominant_factor}</div>
                          <div style={{ fontSize: 11, color: "var(--cl-muted)" }}>{t.note}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
                <section style={panelStyle}>
                  <div style={sectionTitle}>Similar historical cases</div>
                  <div style={{ display: "grid", gap: 8 }}>
                    {card.similar_cases.map((c) => (
                      <div key={c.title} style={evidenceRow}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>{c.title}</div>
                          <div style={{ fontSize: 12, marginTop: 4 }}>{c.detail}</div>
                          <div style={{ fontSize: 11, color: "var(--cl-muted)", marginTop: 4 }}>
                            {c.period} · {c.analogy_note}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </div>

              <section style={panelStyle}>
                <div style={sectionTitle}>AI Decision Audit Trail</div>
                <p style={{ margin: "0 0 10px", fontSize: 12, color: "var(--cl-muted)" }}>
                  What was predicted, why, evidence, confidence — and demo outcome status when available.
                </p>
                <div style={{ display: "grid", gap: 8 }}>
                  {audit.map((a) => (
                    <div key={a.id} style={evidenceRow}>
                      <div style={{ width: "100%" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                          <strong style={{ fontSize: 13 }}>{a.scope_name}</strong>
                          <span style={{ fontSize: 11, color: "var(--cl-muted)" }}>
                            {new Date(a.created_at).toLocaleString()} · {a.outcome_status}
                          </span>
                        </div>
                        <div style={{ fontSize: 12, marginTop: 4 }}>
                          {(a.risk_score * 100).toFixed(0)}% {a.risk_band} · confidence{" "}
                          {Math.round(a.confidence * 100)}%
                        </div>
                        <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 4 }}>
                          Factors: {a.top_factors.join(" · ")}
                        </div>
                        {a.outcome_note ? (
                          <div style={{ fontSize: 11, color: "#f0c674", marginTop: 4 }}>{a.outcome_note}</div>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </>
          ) : (
            !loading && <div style={{ color: "var(--cl-muted)" }}>Select a prediction to open its Decision Card.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function BandPill({ label }: { label: string }) {
  const color =
    label === "High" ? "#e74c3c" : label === "Medium" ? "#e67e22" : label === "Elevated-low" ? "#f1c40f" : "#3498db";
  return (
    <span style={{ fontSize: 11, padding: "4px 8px", borderRadius: 6, border: `1px solid ${color}`, color }}>
      Risk: {label}
    </span>
  );
}

function ConfPill({ band, value }: { band: string; value: number }) {
  return (
    <span
      style={{
        fontSize: 11,
        padding: "4px 8px",
        borderRadius: 6,
        border: "1px solid #2a6f6a",
        color: "#1abc9c",
      }}
    >
      {band} · {Math.round(value * 100)}%
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
  margin: "0 0 10px",
  fontSize: 11,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "var(--cl-muted)",
  fontWeight: 600,
};

const disclaimerStyle: CSSProperties = {
  fontSize: 12,
  color: "#f0c674",
  border: "1px solid #5a4a20",
  background: "rgba(90, 74, 32, 0.35)",
  borderRadius: 8,
  padding: "8px 10px",
};

const linkBtn: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "8px 12px",
  color: "var(--cl-text)",
  textDecoration: "none",
  fontSize: 13,
};

const storyLinkBtn: CSSProperties = {
  border: "1px solid rgba(61,139,253,0.5)",
  borderRadius: 8,
  padding: "8px 12px",
  color: "#9ec1ff",
  background: "rgba(61,139,253,0.14)",
  textDecoration: "none",
  fontSize: 13,
  fontWeight: 700,
};

const ghostBtn: CSSProperties = {
  background: "transparent",
  border: "1px solid var(--cl-border)",
  color: "var(--cl-text)",
  borderRadius: 8,
  padding: "6px 10px",
  cursor: "pointer",
  fontSize: 12,
};

const evidenceRow: CSSProperties = {
  display: "flex",
  gap: 10,
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "10px 12px",
  background: "rgba(12,18,32,0.45)",
};

const timelineRow: CSSProperties = {
  display: "flex",
  gap: 10,
  alignItems: "flex-start",
  fontSize: 13,
};
