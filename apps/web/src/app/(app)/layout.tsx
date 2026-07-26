"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { LanguageSwitcher } from "@/shared/i18n/LanguageSwitcher";
import { useAuthSession } from "@/shared/lib/use-auth-session";
import { KspLogo } from "@/shared/ui/KspLogo";

const NAV_ITEMS: Array<{ href: string; key: string }> = [
  { href: "/dashboard", key: "nav.dashboard" },
  { href: "/map", key: "nav.map" },
  { href: "/prediction", key: "nav.prediction" },
  { href: "/simulation", key: "nav.simulation" },
  { href: "/advisor", key: "nav.advisor" },
  { href: "/explain", key: "nav.explain" },
  { href: "/network", key: "nav.network" },
  { href: "/reports", key: "nav.reports" },
  { href: "/ai", key: "nav.ai" },
  { href: "/settings", key: "nav.settings" },
];

export default function AppShellLayout({ children }: { children: ReactNode }) {
  const { t } = useTranslation("common");
  const pathname = usePathname();
  const { loading: authLoading, user, signOut } = useAuthSession();

  return (
    <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", minHeight: "100vh" }}>
      <aside
        style={{
          borderRight: "1px solid var(--cl-border)",
          background: "rgba(18, 26, 43, 0.92)",
          padding: "1.1rem 0.9rem",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <KspLogo size={48} />
          <div>
            <div style={{ fontSize: 12, color: "#f5d76e", fontWeight: 700, letterSpacing: 0.3 }}>
              {t("govBadge")}
            </div>
            <div style={{ fontWeight: 700, marginTop: 2, fontSize: 16 }}>{t("appName")}</div>
          </div>
        </div>
        <div style={{ fontSize: 11, color: "var(--cl-muted)", lineHeight: 1.4, paddingLeft: 2 }}>
          {t("appTagline")}
        </div>

        <nav style={{ display: "grid", gap: 4, flex: 1, alignContent: "start" }}>
          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/explain"
                ? pathname === "/explain" ||
                  pathname?.startsWith("/explain/") ||
                  pathname === "/story" ||
                  pathname?.startsWith("/story/")
                : pathname === item.href || pathname?.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                prefetch
                style={{
                  color: active ? "var(--cl-text)" : "var(--cl-muted)",
                  textDecoration: "none",
                  fontSize: 13.5,
                  padding: "8px 10px",
                  borderRadius: 8,
                  background: active ? "rgba(61,139,253,0.14)" : "transparent",
                  border: active ? "1px solid rgba(61,139,253,0.35)" : "1px solid transparent",
                }}
              >
                {t(item.key)}
              </Link>
            );
          })}
        </nav>

        <div style={{ display: "grid", gap: 10 }}>
          <LanguageSwitcher />
          {authLoading ? (
            <span style={{ color: "var(--cl-muted)", fontSize: 12, padding: "0 4px" }}>
              {t("loading")}
            </span>
          ) : user ? (
            <div style={{ display: "grid", gap: 6, padding: "0 4px" }}>
              <div style={{ fontSize: 12, color: "var(--cl-text)", fontWeight: 600, lineHeight: 1.3 }}>
                {user.full_name}
              </div>
              <div style={{ fontSize: 11, color: "var(--cl-muted)", wordBreak: "break-all" }}>
                {user.email}
              </div>
              <button
                type="button"
                onClick={() => void signOut()}
                style={{
                  background: "transparent",
                  border: 0,
                  padding: 0,
                  marginTop: 2,
                  color: "var(--cl-accent)",
                  fontSize: 13,
                  textAlign: "left",
                  cursor: "pointer",
                }}
              >
                {t("signOut")}
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              style={{ color: "var(--cl-accent)", fontSize: 13, textDecoration: "none", padding: "0 4px" }}
            >
              {t("signIn")}
            </Link>
          )}
          <div style={{ fontSize: 10, color: "var(--cl-muted)", lineHeight: 1.35, padding: "0 4px" }}>
            {t("footer")}
          </div>
        </div>
      </aside>

      <div style={{ display: "grid", gridTemplateRows: "auto 1fr", minWidth: 0 }}>
        <header
          className="no-print"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 16,
            padding: "0.85rem 1.5rem",
            borderBottom: "1px solid var(--cl-border)",
            background:
              "linear-gradient(90deg, rgba(14, 28, 52, 0.95) 0%, rgba(11, 18, 32, 0.88) 55%, rgba(18, 36, 64, 0.92) 100%)",
            minHeight: 80,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 16, minWidth: 0 }}>
            <KspLogo size={64} priority />
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  fontSize: 26,
                  fontWeight: 800,
                  color: "#ffffff",
                  letterSpacing: 0.15,
                  lineHeight: 1.1,
                  textShadow: "0 1px 2px rgba(0,0,0,0.45)",
                }}
              >
                {t("govBadge")}
              </div>
              <div
                style={{
                  marginTop: 5,
                  fontSize: 14,
                  fontWeight: 650,
                  color: "#f5d76e",
                  letterSpacing: 0.35,
                }}
              >
                {t("appName")} · {t("govPortalHint")}
              </div>
            </div>
          </div>
          <LanguageSwitcher emphasize />
        </header>
        <section style={{ padding: "1.25rem 1.5rem", minWidth: 0 }}>{children}</section>
      </div>
    </div>
  );
}
