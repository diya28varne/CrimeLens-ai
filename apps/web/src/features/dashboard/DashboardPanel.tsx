"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import {
  fetchDashboardAlerts,
  fetchDashboardOverview,
  type DashboardAlert,
  type DashboardOverview,
} from "@/features/dashboard/api";
import { AnalyticsPanel } from "@/features/analytics";

/** Combined command overview + analytics insights under one Dashboard. */
export function DashboardPanel() {
  const { t } = useTranslation("dashboard");
  const { t: tc } = useTranslation("common");
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
          setError(e instanceof Error ? e.message : t("errorLoad"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

  return (
    <div style={{ display: "grid", gap: 28 }}>
      <header>
        <h1 style={{ margin: 0 }}>{t("title")}</h1>
        <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14 }}>
          {t("subtitle")}{" "}
          <Link href="/map" style={{ color: "var(--cl-accent)" }}>
            {t("linkMap")}
          </Link>
        </p>
      </header>

      {error && (
        <div style={bannerStyle}>
          {error}. {tc("signIn")}
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
          label={t("kpi.totalIncidents")}
          value={overview?.kpis.total_incidents}
          delta={overview?.kpis.total_incidents_delta_pct}
          loading={loading}
        />
        <Kpi label={t("kpi.openCases")} value={overview?.kpis.open_incidents} loading={loading} />
        <Kpi label={t("kpi.highCritical")} value={overview?.kpis.high_severity} loading={loading} />
        <Kpi label={t("kpi.hotspots")} value={overview?.kpis.hotspot_count} loading={loading} />
      </div>

      <Panel title={t("alerts.title")}>
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 10 }}>
          {alerts.map((a) => (
            <li key={a.id} style={alertItemStyle(a.severity)}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{a.title}</div>
              <div style={{ color: "var(--cl-muted)", fontSize: 13, marginTop: 4 }}>{a.body}</div>
              {a.href && (
                <Link href={a.href} style={{ color: "var(--cl-accent)", fontSize: 12 }}>
                  {t("alerts.view")} →
                </Link>
              )}
            </li>
          ))}
          {!loading && alerts.length === 0 && <Empty label={t("alerts.empty")} />}
        </ul>
      </Panel>

      {/* Exactly two charts: period impact + offense concentration */}
      <AnalyticsPanel embedded />
    </div>
  );
}

function Kpi({
  label,
  value,
  delta,
  loading,
}: {
  label: string;
  value?: number;
  delta?: number | null;
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

function Empty({ label = "—" }: { label?: string }) {
  return (
    <div style={{ color: "var(--cl-muted)", fontSize: 13, padding: "1rem 0", textAlign: "center" }}>
      {label}
    </div>
  );
}

const panelStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  background: "rgba(18, 26, 43, 0.72)",
  padding: "14px 16px",
};

const bannerStyle: CSSProperties = {
  border: "1px solid #ff453a",
  borderRadius: 10,
  padding: "10px 12px",
  color: "var(--cl-text)",
  background: "rgba(255,69,58,0.08)",
  fontSize: 14,
};

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
