import type { ReactNode } from "react";
import Link from "next/link";

const nav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/analytics", label: "Analytics" },
  { href: "/map", label: "Map" },
  { href: "/prediction", label: "Prediction" },
  { href: "/network", label: "Network" },
  { href: "/reports", label: "Reports" },
  { href: "/ai", label: "AI Copilot" },
  { href: "/settings", label: "Settings" },
  { href: "/admin", label: "Admin" },
];

export default function AppShellLayout({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", minHeight: "100vh" }}>
      <aside
        style={{
          borderRight: "1px solid var(--cl-border)",
          background: "rgba(18, 26, 43, 0.9)",
          padding: "1.25rem 1rem",
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 20 }}>CrimeLens AI</div>
        <nav style={{ display: "grid", gap: 8 }}>
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              style={{ color: "var(--cl-muted)", textDecoration: "none", fontSize: 14 }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div style={{ marginTop: 28 }}>
          <Link href="/login" style={{ color: "var(--cl-accent)", fontSize: 13, textDecoration: "none" }}>
            Sign in
          </Link>
        </div>
      </aside>
      <section style={{ padding: "1.25rem 1.5rem", minWidth: 0 }}>{children}</section>
    </div>
  );
}
