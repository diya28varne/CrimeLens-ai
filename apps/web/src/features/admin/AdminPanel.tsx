"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

import { apiFetch, ApiError } from "@/shared/api/client";
import { fetchAuditTrail, type AuditRecord } from "@/features/explain/api";
import { appConfig } from "@/shared/config";

type Overview = {
  api_version: string;
  users: Array<{
    id: string;
    email: string;
    full_name: string;
    status: string;
    roles: string[];
  }>;
  roles: Array<{ code: string; name: string; permission_count: number }>;
  permission_codes: string[];
  feature_flags: Array<{ id: string; label: string; route: string; status: string }>;
};

export function AdminPanel() {
  const [data, setData] = useState<Overview | null>(null);
  const [audit, setAudit] = useState<AuditRecord[]>([]);
  const [health, setHealth] = useState<string>("…");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [ov, h] = await Promise.all([
          apiFetch<{ data: Overview }>("/admin/overview"),
          fetch(`${appConfig.apiBaseUrl}/health/live`)
            .then((r) => (r.ok ? "ok" : `http ${r.status}`))
            .catch(() => "unreachable"),
        ]);
        if (cancelled) return;
        setData(ov.data);
        setHealth(h);
        try {
          const a = await fetchAuditTrail();
          if (!cancelled) setAudit(a.data.slice(0, 8));
        } catch {
          if (!cancelled) setAudit([]);
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError && e.status === 401
              ? "Sign in as admin required."
              : e instanceof ApiError && e.status === 403
                ? "admin:users permission required."
                : e instanceof Error
                  ? e.message
                  : "Failed to load admin overview",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div style={{ display: "grid", gap: 14, maxWidth: 960 }}>
      <header>
        <h1 style={{ margin: 0, fontSize: 22 }}>Admin</h1>
        <p style={{ margin: "4px 0 0", color: "var(--cl-muted)", fontSize: 13 }}>
          Users, roles, platform modules, and AI decision audit snapshot.
        </p>
      </header>

      {error ? <div style={{ color: "#ff8e8e", fontSize: 13 }}>{error}</div> : null}
      {loading ? <div style={{ color: "var(--cl-muted)" }}>Loading…</div> : null}

      {data ? (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 10 }}>
            <Stat label="API" value={data.api_version} />
            <Stat label="Health" value={health} />
            <Stat label="Users" value={String(data.users.length)} />
            <Stat label="Roles" value={String(data.roles.length)} />
            <Stat label="Permissions" value={String(data.permission_codes.length)} />
          </div>

          <Section title="Users">
            <div style={{ display: "grid", gap: 8 }}>
              {data.users.map((u) => (
                <div key={u.id} style={card}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                    <strong>{u.full_name}</strong>
                    <span style={{ fontSize: 12, color: "var(--cl-muted)" }}>{u.status}</span>
                  </div>
                  <div style={{ fontSize: 13, color: "var(--cl-muted)" }}>{u.email}</div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>Roles: {u.roles.join(", ") || "—"}</div>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Roles">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 8 }}>
              {data.roles.map((r) => (
                <div key={r.code} style={card}>
                  <strong>{r.name}</strong>
                  <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>{r.code}</div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>{r.permission_count} permissions</div>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Feature modules">
            <div style={{ display: "grid", gap: 6 }}>
              {data.feature_flags.map((f) => (
                <div key={f.id} style={{ ...card, display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <div>
                    <strong style={{ fontSize: 13 }}>{f.label}</strong>
                    <div style={{ fontSize: 11, color: "var(--cl-muted)" }}>{f.route}</div>
                  </div>
                  <Link href={f.route} style={{ color: "var(--cl-accent)", fontSize: 12 }}>
                    {f.status} →
                  </Link>
                </div>
              ))}
            </div>
          </Section>

          <Section title="AI Decision Audit (recent)">
            {audit.length === 0 ? (
              <p style={{ margin: 0, fontSize: 13, color: "var(--cl-muted)" }}>
                No audit rows yet — open a Decision Card on{" "}
                <Link href="/explain" style={{ color: "var(--cl-accent)" }}>
                  /explain
                </Link>{" "}
                to create one.
              </p>
            ) : (
              <div style={{ display: "grid", gap: 8 }}>
                {audit.map((a) => (
                  <div key={a.id} style={card}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                      <strong style={{ fontSize: 13 }}>{a.scope_name}</strong>
                      <span style={{ fontSize: 11, color: "var(--cl-muted)" }}>{a.outcome_status}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>
                      {(a.risk_score * 100).toFixed(0)}% · {Math.round(a.confidence * 100)}% conf ·{" "}
                      {new Date(a.created_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="Permission catalog">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {data.permission_codes.map((p) => (
                <span key={p} style={chip}>
                  {p}
                </span>
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
    <section style={panel}>
      <h3 style={sectionTitle}>{title}</h3>
      {children}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={card}>
      <div style={{ fontSize: 11, color: "var(--cl-muted)" }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}

const panel: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  background: "rgba(18,26,43,0.72)",
  padding: "14px 16px",
};
const sectionTitle: CSSProperties = {
  margin: "0 0 12px",
  fontSize: 11,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "var(--cl-muted)",
};
const card: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "10px 12px",
  background: "rgba(12,18,32,0.45)",
};
const chip: CSSProperties = {
  fontSize: 11,
  padding: "4px 8px",
  borderRadius: 6,
  border: "1px solid var(--cl-border)",
  color: "var(--cl-muted)",
};
