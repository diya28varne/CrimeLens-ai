import Link from "next/link";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function HomePage() {
  return (
    <main
      style={{
        maxWidth: 880,
        margin: "0 auto",
        padding: "4rem 1.5rem",
      }}
    >
      <p
        style={{
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: "var(--cl-muted)",
          fontSize: 12,
          marginBottom: 12,
        }}
      >
        Karnataka State Police Datathon
      </p>
      <h1 style={{ fontSize: "clamp(2.4rem, 6vw, 4rem)", lineHeight: 1.05, margin: "0 0 1rem" }}>
        CrimeLens AI
      </h1>
      <p style={{ color: "var(--cl-muted)", fontSize: 18, maxWidth: 620, marginBottom: 28 }}>
        AI-Powered Crime Intelligence & Decision Support Platform. Phase 1 foundation is online —
        identity, crime, map, and prediction modules follow after approval.
      </p>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Link
          href="/dashboard"
          style={{
            background: "var(--cl-accent)",
            color: "#fff",
            padding: "0.75rem 1.1rem",
            borderRadius: 8,
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          Open console shell
        </Link>
        <a
          href={`${apiBase}/health/live`}
          style={{
            border: "1px solid var(--cl-border)",
            color: "var(--cl-text)",
            padding: "0.75rem 1.1rem",
            borderRadius: 8,
            textDecoration: "none",
          }}
        >
          API health
        </a>
      </div>
    </main>
  );
}
