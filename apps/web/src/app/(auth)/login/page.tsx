"use client";

import { FormEvent, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";

import { LanguageSwitcher } from "@/shared/i18n/LanguageSwitcher";
import { appConfig } from "@/shared/config";
import { setAccessToken } from "@/shared/lib/auth-storage";
import { readStoredLocale } from "@/shared/i18n";
import { KspLogo } from "@/shared/ui/KspLogo";

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
        body: JSON.stringify({ email, password, client: "browser" }),
      });
      const payload = (await response.json().catch(() => null)) as LoginResponse | null;
      if (!response.ok) {
        throw new Error(
          (payload as unknown as { error?: { message?: string } })?.error?.message ??
            t("failed"),
        );
      }
      // Browser login sets httpOnly cookies; also keep token if API returns one.
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
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        alignContent: "start",
        justifyItems: "center",
        padding: "1.25rem 1rem 3rem",
        background:
          "radial-gradient(ellipse at 50% 0%, rgba(30, 60, 110, 0.45) 0%, transparent 55%), var(--cl-bg)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 520,
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: 8,
        }}
      >
        <LanguageSwitcher emphasize />
      </div>

      <div
        style={{
          width: "100%",
          maxWidth: 440,
          display: "grid",
          justifyItems: "center",
          gap: 10,
          marginTop: 4,
          marginBottom: 28,
        }}
      >
        <KspLogo size={220} priority />
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: 1.2,
              textTransform: "uppercase",
              color: "#f5d76e",
            }}
          >
            {tc("govBadge")}
          </div>
          <h1 style={{ margin: "8px 0 0", fontSize: 28, fontWeight: 800 }}>{t("title")}</h1>
          <p style={{ color: "var(--cl-muted)", margin: "8px 0 0", fontSize: 15 }}>{t("subtitle")}</p>
          <p style={{ color: "var(--cl-muted)", margin: "6px 0 0", fontSize: 13 }}>{t("govNote")}</p>
        </div>
      </div>

      <form
        onSubmit={onSubmit}
        style={{
          width: "100%",
          maxWidth: 420,
          display: "grid",
          gap: 12,
          padding: "1.25rem",
          borderRadius: 16,
          border: "1px solid var(--cl-border)",
          background: "rgba(18, 26, 43, 0.92)",
          boxShadow: "0 16px 40px rgba(0,0,0,0.35)",
        }}
      >
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
