"use client";

import { FormEvent, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";

import { LanguageSwitcher } from "@/shared/i18n/LanguageSwitcher";
import { appConfig } from "@/shared/config";
import { setAccessToken } from "@/shared/lib/auth-storage";
import { readStoredLocale } from "@/shared/i18n";

type LoginResponse = {
  data: {
    access_token: string | null;
    permissions: string[];
  };
};

export default function LoginPage() {
  const { t } = useTranslation("auth");
  const { t: tc } = useTranslation("common");
  const [email, setEmail] = useState("admin@crimelens.local");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const locale = readStoredLocale();
      const response = await fetch(`${appConfig.apiBaseUrl}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CrimeLens-Locale": locale,
          "Accept-Language": locale === "kn" ? "kn-IN,kn;q=0.9" : "en",
        },
        credentials: "include",
        body: JSON.stringify({ email, password, client: "api" }),
      });
      const payload = (await response.json().catch(() => null)) as LoginResponse | null;
      if (!response.ok) {
        throw new Error(
          (payload as unknown as { error?: { message?: string } })?.error?.message ??
            t("failed"),
        );
      }
      if (payload?.data.access_token) {
        setAccessToken(payload.data.access_token);
      }
      window.location.assign("/map");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 420, margin: "4rem auto", padding: "0 1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>{tc("govBadge")}</div>
          <h1 style={{ margin: "6px 0 0" }}>{t("title")}</h1>
        </div>
        <LanguageSwitcher compact />
      </div>
      <p style={{ color: "var(--cl-muted)" }}>{t("subtitle")}</p>
      <p style={{ color: "var(--cl-muted)", fontSize: 13 }}>{t("govNote")}</p>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: 12, marginTop: 24 }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span>{t("email")}</span>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
            style={inputStyle}
          />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span>{t("password")}</span>
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            required
            minLength={8}
            style={inputStyle}
          />
        </label>
        {error ? <p style={{ color: "#ff8e8e", margin: 0 }}>{error}</p> : null}
        <button type="submit" disabled={loading} style={buttonStyle}>
          {loading ? t("submitting") : t("submit")}
        </button>
      </form>
    </main>
  );
}

const inputStyle: CSSProperties = {
  padding: 10,
  borderRadius: 8,
  border: "1px solid var(--cl-border)",
  background: "var(--cl-surface)",
  color: "var(--cl-text)",
};

const buttonStyle: CSSProperties = {
  background: "var(--cl-accent)",
  color: "#fff",
  border: 0,
  borderRadius: 8,
  padding: "0.75rem 1rem",
  fontWeight: 600,
  cursor: "pointer",
};
