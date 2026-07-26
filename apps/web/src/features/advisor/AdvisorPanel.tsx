"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from "react";

import {
  fetchAdvisorBrief,
  refreshAdvisorBrief,
  type ActionRec,
  type AdvisorBrief,
  type EvidenceItem,
  type Pattern,
  type RiskArea,
  type TimelineEntry,
} from "@/features/advisor/api";
import { ApiError } from "@/shared/api/client";

export function AdvisorPanel() {
  const [brief, setBrief] = useState<AdvisorBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  const load = useCallback(async (mode: "current" | "refresh" = "current") => {
    if (mode === "refresh") setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const res = mode === "refresh" ? await refreshAdvisorBrief() : await fetchAdvisorBrief();
      setBrief(res.data);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 401
          ? "Sign in required — open /login with seeded admin credentials."
          : e instanceof Error
            ? e.message
            : "Failed to load intelligence brief",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load("current");
  }, [load]);

  function toggle(id: string) {
    setOpenId((prev) => (prev === id ? null : id));
  }

  return (
    <div style={{ display: "grid", gap: 14, maxWidth: 1100 }}>
      <header style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Strategic Intelligence Advisor</h1>
          <p style={{ margin: "4px 0 0", color: "var(--cl-muted)", fontSize: 13 }}>
            Daily briefing — what’s happening, why it matters, what to consider next.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button type="button" onClick={() => void load("refresh")} disabled={refreshing} style={btnStyle}>
            {refreshing ? "Refreshing…" : "Refresh brief"}
          </button>
          <Link href="/ai" style={{ ...btnStyle, textDecoration: "none", display: "inline-block" }}>
            Ask Copilot
          </Link>
        </div>
      </header>

      <div style={disclaimerStyle}>{brief?.disclaimer ?? "Grounded intelligence briefing — not operational orders."}</div>

      {error ? <div style={{ color: "#ff8e8e", fontSize: 13 }}>{error}</div> : null}
      {loading && !brief ? <div style={{ color: "var(--cl-muted)" }}>Building briefing…</div> : null}

      {brief ? (
        <>
          <Section title="Today’s Intelligence Summary">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
              {brief.summary.kind_tags.map((t) => (
                <KindBadge key={t} kind={t} />
              ))}
              <span style={{ fontSize: 12, color: "var(--cl-muted)" }}>
                Confidence {Math.round(brief.confidence * 100)}% ·{" "}
                {new Date(brief.generated_at).toLocaleString()}
              </span>
            </div>
            <h2 style={{ margin: "0 0 8px", fontSize: 18 }}>{brief.summary.headline}</h2>
            <p style={{ margin: 0, lineHeight: 1.55, fontSize: 14, color: "var(--cl-text)" }}>{brief.summary.body}</p>
            {brief.summary.week_over_week_pct != null ? (
              <div style={{ marginTop: 10, fontSize: 13, color: "var(--cl-muted)" }}>
                Window delta:{" "}
                <strong style={{ color: "var(--cl-text)" }}>
                  {brief.summary.week_over_week_pct >= 0 ? "+" : ""}
                  {brief.summary.week_over_week_pct}%
                </strong>
              </div>
            ) : null}
          </Section>

          <Section title="Emerging patterns">
            <div style={{ display: "grid", gap: 8 }}>
              {brief.patterns.map((p) => (
                <Expandable
                  key={p.id}
                  open={openId === p.id}
                  onToggle={() => toggle(p.id)}
                  header={
                    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", flexWrap: "wrap" }}>
                      <KindBadge kind={p.kind} />
                      <div style={{ flex: 1, minWidth: 180 }}>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{p.title}</div>
                        <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 2 }}>
                          Strength {p.strength} · {Math.round(p.confidence * 100)}% confidence
                        </div>
                      </div>
                    </div>
                  }
                >
                  <p style={{ margin: "0 0 10px", fontSize: 13, lineHeight: 1.5 }}>{p.explanation}</p>
                  <EvidenceList items={p.evidence} />
                </Expandable>
              ))}
            </div>
          </Section>

          <Section title="Risk assessment">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 10,
              }}
            >
              {brief.risk_areas.map((r) => (
                <RiskCard key={r.id} area={r} open={openId === r.id} onToggle={() => toggle(r.id)} />
              ))}
            </div>
          </Section>

          <Section title="Recommended actions">
            <div style={{ display: "grid", gap: 8 }}>
              {brief.actions.map((a) => (
                <ActionCard key={a.id} action={a} open={openId === a.id} onToggle={() => toggle(a.id)} />
              ))}
            </div>
          </Section>

          <Section title="Intelligence Timeline">
            <p style={{ margin: "0 0 10px", fontSize: 12, color: "var(--cl-muted)" }}>
              How assessments evolved (demo history seeded for closed-loop storytelling).
            </p>
            <div style={{ display: "grid", gap: 8 }}>
              {brief.timeline.map((t) => (
                <TimelineRow key={t.id} entry={t} />
              ))}
            </div>
          </Section>
        </>
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

function KindBadge({ kind }: { kind: "observed" | "forecast" }) {
  const observed = kind === "observed";
  return (
    <span
      style={{
        fontSize: 10,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        padding: "3px 7px",
        borderRadius: 6,
        border: observed ? "1px solid #2a6f6a" : "1px solid #6a5a2a",
        color: observed ? "#1abc9c" : "#f0c674",
        background: observed ? "rgba(26,188,156,0.12)" : "rgba(240,198,116,0.12)",
      }}
    >
      {kind}
    </span>
  );
}

function Expandable({
  header,
  children,
  open,
  onToggle,
}: {
  header: ReactNode;
  children: ReactNode;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <div style={cardStyle}>
      <button
        type="button"
        onClick={onToggle}
        style={{
          all: "unset",
          cursor: "pointer",
          display: "block",
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
          <div style={{ flex: 1 }}>{header}</div>
          <span style={{ color: "var(--cl-muted)", fontSize: 12 }}>{open ? "Hide evidence" : "Evidence"}</span>
        </div>
      </button>
      {open ? <div style={{ marginTop: 10, borderTop: "1px solid var(--cl-border)", paddingTop: 10 }}>{children}</div> : null}
    </div>
  );
}

function EvidenceList({ items }: { items: EvidenceItem[] }) {
  if (!items.length) return <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>No evidence attachments.</div>;
  return (
    <ul style={{ margin: 0, paddingLeft: 16, display: "grid", gap: 6, fontSize: 13 }}>
      {items.map((e, i) => (
        <li key={`${e.label}-${i}`}>
          <strong>{e.label}</strong> — {e.detail}
          {e.value != null ? ` (${e.value})` : ""}
          {e.href ? (
            <>
              {" "}
              <Link href={e.href} style={{ color: "var(--cl-accent)" }}>
                Open
              </Link>
            </>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function RiskCard({
  area,
  open,
  onToggle,
}: {
  area: RiskArea;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <div style={cardStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 6 }}>
        <div style={{ fontWeight: 600 }}>{area.name}</div>
        <KindBadge kind={area.kind} />
      </div>
      <div style={{ fontSize: 20, fontWeight: 700, color: riskColor(area.risk_band) }}>{area.risk_band}</div>
      <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 4 }}>
        Score {area.risk_score.toFixed(2)} · {Math.round(area.confidence * 100)}% confidence
      </div>
      <p style={{ margin: "8px 0 0", fontSize: 12, lineHeight: 1.45 }}>{area.why}</p>
      <button type="button" onClick={onToggle} style={{ ...linkBtn, marginTop: 8 }}>
        {open ? "Hide evidence" : "Supporting evidence"}
      </button>
      {open ? (
        <div style={{ marginTop: 8 }}>
          <EvidenceList items={area.evidence} />
        </div>
      ) : null}
    </div>
  );
}

function ActionCard({
  action,
  open,
  onToggle,
}: {
  action: ActionRec;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <Expandable
      open={open}
      onToggle={onToggle}
      header={
        <div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <span style={priorityChip(action.priority)}>{action.priority}</span>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{action.title}</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 4 }}>
            {Math.round(action.confidence * 100)}% confidence
          </div>
        </div>
      }
    >
      <p style={{ margin: "0 0 10px", fontSize: 13, lineHeight: 1.5 }}>{action.rationale}</p>
      <EvidenceList items={action.evidence} />
      {action.simulation_preset_id ? (
        <div style={{ marginTop: 10 }}>
          <Link
            href={`/simulation`}
            style={{ color: "var(--cl-accent)", fontSize: 13 }}
          >
            Test related scenario in Simulator →
          </Link>
        </div>
      ) : null}
    </Expandable>
  );
}

function TimelineRow({ entry }: { entry: TimelineEntry }) {
  return (
    <div style={{ ...cardStyle, display: "grid", gap: 4 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
        <strong style={{ fontSize: 13 }}>{new Date(entry.generated_at).toLocaleDateString()}</strong>
        <span style={{ fontSize: 12, color: "var(--cl-muted)" }}>
          {entry.recommendation_count} recommendations
          {entry.acted_on_demo != null ? (entry.acted_on_demo ? " · acted (demo)" : " · not acted (demo)") : ""}
        </span>
      </div>
      <div style={{ fontSize: 13 }}>{entry.summary_excerpt}</div>
      {entry.accuracy_note ? (
        <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>Accuracy: {entry.accuracy_note}</div>
      ) : null}
      {entry.hotspot_realized_note ? (
        <div style={{ fontSize: 12, color: "#f0c674" }}>{entry.hotspot_realized_note}</div>
      ) : null}
    </div>
  );
}

function riskColor(band: string) {
  if (band === "High") return "#e74c3c";
  if (band === "Medium") return "#e67e22";
  if (band === "Elevated-low") return "#f1c40f";
  return "#3498db";
}

function priorityChip(p: string): CSSProperties {
  const color = p === "high" ? "#e74c3c" : p === "medium" ? "#e67e22" : "#95a5a6";
  return {
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    color,
    border: `1px solid ${color}`,
    borderRadius: 6,
    padding: "2px 6px",
  };
}

const panelStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  background: "rgba(18, 26, 43, 0.72)",
  padding: "14px 16px",
};

const sectionTitle: CSSProperties = {
  margin: "0 0 12px",
  fontSize: 13,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "var(--cl-muted)",
  fontWeight: 600,
};

const cardStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 10,
  padding: "12px 12px",
  background: "rgba(12, 18, 32, 0.55)",
};

const btnStyle: CSSProperties = {
  background: "transparent",
  color: "var(--cl-text)",
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "8px 12px",
  cursor: "pointer",
  fontSize: 13,
};

const linkBtn: CSSProperties = {
  background: "transparent",
  border: 0,
  color: "var(--cl-accent)",
  cursor: "pointer",
  padding: 0,
  fontSize: 12,
};

const disclaimerStyle: CSSProperties = {
  fontSize: 12,
  color: "#f0c674",
  border: "1px solid #5a4a20",
  background: "rgba(90, 74, 32, 0.35)",
  borderRadius: 8,
  padding: "8px 10px",
};
