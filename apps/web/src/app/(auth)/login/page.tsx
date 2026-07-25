"use client";

import { FormEvent, useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";

import { appConfig } from "@/shared/config";
import { setAccessToken } from "@/shared/lib/auth-storage";

type LoginResponse = {
  data: {
    access_token: string | null;
    permissions: string[];
  };
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@crimelens.local");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      // client=api returns bearer token for cross-origin SPA map/API calls
      const response = await fetch(`${appConfig.apiBaseUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password, client: "api" }),
      });
      const payload = (await response.json().catch(() => null)) as LoginResponse | null;
      if (!response.ok) {
        throw new Error(
          (payload as unknown as { error?: { message?: string } })?.error?.message ??
            "Login failed",
        );
      }
      if (payload?.data.access_token) {
        setAccessToken(payload.data.access_token);
      }
      router.push("/map");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 420, margin: "4rem auto", padding: "0 1rem" }}>
      <h1>Sign in</h1>
      <p style={{ color: "var(--cl-muted)" }}>
        Use seeded admin credentials after <code>make seed</code>, then open the crime map.
      </p>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: 12, marginTop: 24 }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Email</span>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
            style={inputStyle}
          />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Password</span>
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
          {loading ? "Signing in…" : "Sign in"}
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
