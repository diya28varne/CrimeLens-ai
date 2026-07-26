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

const DEMO_EMAIL = "admin@crimelens.local";
const DEMO_PASSWORD = "ChangeMe123!";

export default function LoginPage() {
  const { t } = useTranslation("auth");
  const { t: tc } = useTranslation("common");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function doLogin(loginEmail: string, loginPassword: string) {
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
        body: JSON.stringify({ email: loginEmail, password: loginPassword, client: "api" }),
      });
      const payload = (await response.json().catch(() => null)) as LoginResponse | null;
      if (!response.ok) {
        throw new Error(
          (payload as unknown as { error?: { message?: string } })?.error?.message ??
            t("failed"),
        );
      }
      const token = payload?.data.access_token;
      if (!token) {
        throw new Error(t("failed"));
      }
      setAccessToken(token);
      window.location.assign("/dashboard");
    } catch (err) {
      const message = err instanceof Error ? err.message : t("failed");
      setError(
        message === "Failed to fetch" || message.toLowerCase().includes("network")
          ? t("networkError")
          : message,
      );
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    await doLogin(email, password);
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
        <button
          type="button"
          disabled={loading}
          onClick={() => void doLogin(DEMO_EMAIL, DEMO_PASSWORD)}
          style={demoButtonStyle}
        >
          {loading ? t("submitting") : t("continueDemo")}
        </button>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr auto 1fr",
            alignItems: "center",
            gap: 8,
            color: "var(--cl-muted)",
            fontSize: 12,
          }}
        >
          <span style={{ height: 1, background: "var(--cl-border)" }} />
          <span>or</span>
          <span style={{ height: 1, background: "var(--cl-border)" }} />
        </div>

        <label style={{ display: "grid", gap: 6 }}>
          <span>{t("email")}</span>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
            placeholder="you@gmail.com"
            autoComplete="username"
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
            minLength={1}
            placeholder="any password"
            autoComplete="current-password"
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

const demoButtonStyle: CSSProperties = {
  background: "linear-gradient(180deg, #3d8bfd, #1f6feb)",
  color: "#fff",
  border: 0,
  borderRadius: 8,
  padding: "0.85rem 1rem",
  fontWeight: 700,
  cursor: "pointer",
  fontSize: 15,
};
