"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

import { apiFetch, ApiError } from "@/shared/api/client";
import { clearAccessToken } from "@/shared/lib/auth-storage";
import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "@/shared/i18n/LanguageSwitcher";

type MeData = {
  user: { id: string; email: string; full_name: string; status: string };
  roles: string[];
  permissions: string[];
  jurisdictions: { district_ids: string[]; station_ids: string[] };
};

const PREFS_KEY = "cl_user_prefs";

type Prefs = {
  defaultReport: "daily" | "weekly" | "festival";
  mapLayer: "points" | "heatmap" | "both";
  showDisclaimers: boolean;
  denseUi: boolean;
};

const DEFAULT_PREFS: Prefs = {
  defaultReport: "weekly",
  mapLayer: "both",
  showDisclaimers: true,
  denseUi: false,
};

function loadPrefs(): Prefs {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return DEFAULT_PREFS;
    return { ...DEFAULT_PREFS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_PREFS;
  }
}

function savePrefs(p: Prefs) {
  localStorage.setItem(PREFS_KEY, JSON.stringify(p));
}

export function SettingsPanel() {
  const { t } = useTranslation("settings");
  const { t: tc } = useTranslation("common");
  const [me, setMe] = useState<MeData | null>(null);
  const [prefs, setPrefs] = useState<Prefs>(DEFAULT_PREFS);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setPrefs(loadPrefs());
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch<{ data: MeData }>("/auth/me");
        if (!cancelled) setMe(res.data);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError && e.status === 401
              ? tc("signInRequiredShort")
              : e instanceof Error
                ? e.message
                : t("errorProfile"),
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t, tc]);

  function updatePrefs(patch: Partial<Prefs>) {
    const next = { ...prefs, ...patch };
    setPrefs(next);
    savePrefs(next);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1500);
  }

  function signOut() {
    clearAccessToken();
    void (async () => {
      try {
        const { appConfig } = await import("@/shared/config");
        await fetch(`${appConfig.apiBaseUrl}/auth/logout`, {
          method: "POST",
          credentials: "include",
        });
      } catch {
        // ignore network errors on logout
      }
      window.location.assign("/login");
    })();
  }

  const jurisdictionValue =
    me && (me.jurisdictions.district_ids.length || me.jurisdictions.station_ids.length)
      ? t("jurisdictionsCount", {
          districts: me.jurisdictions.district_ids.length,
          stations: me.jurisdictions.station_ids.length,
        })
      : t("jurisdictionsAll");

  return (
    <div style={{ display: "grid", gap: 14, maxWidth: 820 }}>
      <header>
        <h1 style={{ margin: 0, fontSize: 22 }}>{t("title")}</h1>
        <p style={{ margin: "4px 0 0", color: "var(--cl-muted)", fontSize: 13 }}>{t("subtitle")}</p>
      </header>

      {error ? <div style={{ color: "#ff8e8e", fontSize: 13 }}>{error}</div> : null}
      {loading ? <div style={{ color: "var(--cl-muted)" }}>{tc("loading")}</div> : null}

      {me ? (
        <Section title={t("profile")}>
          <div style={{ display: "grid", gap: 8, fontSize: 14 }}>
            <Row label={t("profile")} value={me.user.full_name} />
            <Row label={t("email")} value={me.user.email} />
            <Row label={tc("status")} value={me.user.status} />
            <Row label={t("roles")} value={me.roles.join(", ") || "—"} />
            <Row label={t("jurisdictions")} value={jurisdictionValue} />
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 12, color: "var(--cl-muted)", marginBottom: 6 }}>{t("language")}</div>
              <LanguageSwitcher />
            </div>
            <button type="button" onClick={signOut} style={primaryBtn}>
              {t("signOut")}
            </button>
          </div>
        </Section>
      ) : null}

      <Section title={t("preferences")}>
        <p style={{ margin: "0 0 12px", fontSize: 12, color: "var(--cl-muted)" }}>
          {t("prefsStoredLocally")}
          {saved ? t("savedSuffix") : ""}
        </p>
        <label style={field}>
          <span>{t("defaultReport")}</span>
          <select
            value={prefs.defaultReport}
            onChange={(e) => updatePrefs({ defaultReport: e.target.value as Prefs["defaultReport"] })}
            style={input}
          >
            <option value="daily">{t("reportDaily")}</option>
            <option value="weekly">{t("reportWeekly")}</option>
            <option value="festival">{t("reportFestival")}</option>
          </select>
        </label>
        <label style={field}>
          <span>{t("mapLayer")}</span>
          <select
            value={prefs.mapLayer}
            onChange={(e) => updatePrefs({ mapLayer: e.target.value as Prefs["mapLayer"] })}
            style={input}
          >
            <option value="points">{t("layerPoints")}</option>
            <option value="heatmap">{t("layerHeatmap")}</option>
            <option value="both">{t("layerBoth")}</option>
          </select>
        </label>
        <label style={checkRow}>
          <input
            type="checkbox"
            checked={prefs.showDisclaimers}
            onChange={(e) => updatePrefs({ showDisclaimers: e.target.checked })}
          />
          {t("showDisclaimersFull")}
        </label>
        <label style={checkRow}>
          <input
            type="checkbox"
            checked={prefs.denseUi}
            onChange={(e) => updatePrefs({ denseUi: e.target.checked })}
          />
          {t("denseUiFull")}
        </label>
      </Section>

      <Section title={t("quickLinks")}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", fontSize: 13 }}>
          <Link href="/reports" style={{ color: "var(--cl-accent)" }}>
            {tc("nav.reports")}
          </Link>
          <Link href="/explain" style={{ color: "var(--cl-accent)" }}>
            {tc("nav.explain")}
          </Link>
          <Link href="/advisor" style={{ color: "var(--cl-accent)" }}>
            {tc("nav.advisor")}
          </Link>
          <Link href="/simulation" style={{ color: "var(--cl-accent)" }}>
            {tc("nav.simulation")}
          </Link>
        </div>
      </Section>

      {me ? (
        <Section title={t("yourPermissions")}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {me.permissions.map((p) => (
              <span key={p} style={chip}>
                {p}
              </span>
            ))}
          </div>
        </Section>
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

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 8 }}>
      <span style={{ color: "var(--cl-muted)" }}>{label}</span>
      <strong style={{ fontWeight: 600 }}>{value}</strong>
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

const field: CSSProperties = { display: "grid", gap: 6, marginBottom: 12, fontSize: 13 };
const input: CSSProperties = {
  padding: 8,
  borderRadius: 8,
  border: "1px solid var(--cl-border)",
  background: "var(--cl-surface)",
  color: "var(--cl-text)",
};
const checkRow: CSSProperties = {
  display: "flex",
  gap: 8,
  alignItems: "center",
  fontSize: 13,
  marginBottom: 8,
};
const chip: CSSProperties = {
  fontSize: 11,
  padding: "4px 8px",
  borderRadius: 6,
  border: "1px solid var(--cl-border)",
  color: "var(--cl-muted)",
};
const primaryBtn: CSSProperties = {
  background: "var(--cl-accent)",
  color: "#fff",
  border: 0,
  borderRadius: 8,
  padding: "8px 12px",
  fontWeight: 600,
  cursor: "pointer",
};
