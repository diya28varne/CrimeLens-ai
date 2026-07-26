"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";

import { setAppLocale } from "@/shared/i18n/setLocale";
import { LOCALES, type AppLocale } from "@/shared/i18n";
import { KspLogo } from "@/shared/ui/KspLogo";

export function LanguageSwitcher({
  compact = false,
  emphasize = false,
}: {
  compact?: boolean;
  /** Larger, header-prominent control with Translation label */
  emphasize?: boolean;
}) {
  const { t, i18n } = useTranslation("common");
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const current = (i18n.language?.startsWith("kn") ? "kn" : "en") as AppLocale;
  const big = emphasize || !compact;

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  async function select(locale: AppLocale) {
    await setAppLocale(locale);
    setOpen(false);
  }

  return (
    <div ref={rootRef} style={{ position: "relative", display: "inline-flex", alignItems: "center", gap: 10 }}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`${t("translation")}: ${current === "kn" ? t("kannada") : t("english")}`}
        onClick={() => setOpen((v) => !v)}
        style={emphasize ? emphasizeTriggerStyle : big ? triggerStyle : compactTriggerStyle}
      >
        {emphasize ? (
          <KspLogo size={36} />
        ) : (
          <span aria-hidden style={{ fontSize: big ? 18 : 15 }}>
            🌐
          </span>
        )}
        <span
          style={{
            color: "#fff",
            fontWeight: 800,
            fontSize: emphasize ? 18 : big ? 14 : 13,
            letterSpacing: 0.2,
          }}
        >
          {current === "kn" ? t("kannada") : t("english")}
        </span>
        <span
          style={{
            padding: emphasize ? "5px 10px" : "3px 8px",
            borderRadius: 8,
            background: emphasize ? "rgba(245, 215, 110, 0.18)" : "rgba(61,139,253,0.12)",
            border: emphasize ? "1px solid rgba(245, 215, 110, 0.45)" : "1px solid rgba(61,139,253,0.35)",
            color: emphasize ? "#f5d76e" : "#9ec1ff",
            fontSize: emphasize ? 13 : 11,
            fontWeight: 800,
            letterSpacing: 0.4,
            textTransform: "uppercase",
          }}
        >
          {t("translation")}
        </span>
        <span aria-hidden style={{ color: "#9ec1ff", fontSize: emphasize ? 14 : 11 }}>
          ▾
        </span>
      </button>
      {open ? (
        <ul role="listbox" style={{ ...menuStyle, minWidth: emphasize ? 240 : 180 }}>
          <li style={{ padding: "6px 12px 8px", fontSize: 11, color: "var(--cl-muted)", textTransform: "uppercase", letterSpacing: 0.5 }}>
            {t("translation")} — {t("language")}
          </li>
          {LOCALES.map((locale) => (
            <li key={locale}>
              <button
                type="button"
                role="option"
                aria-selected={current === locale}
                onClick={() => void select(locale)}
                style={{
                  ...itemStyle,
                  fontSize: emphasize ? 15 : 14,
                  padding: emphasize ? "12px 14px" : "10px 12px",
                  background: current === locale ? "rgba(61,139,253,0.18)" : "transparent",
                }}
              >
                <span style={{ width: 20, fontWeight: 700 }}>{current === locale ? "✓" : ""}</span>
                {locale === "en" ? t("english") : t("kannada")}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

const emphasizeTriggerStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 12,
  background: "linear-gradient(180deg, rgba(40,70,120,0.95), rgba(18,36,64,0.98))",
  color: "var(--cl-text)",
  border: "2px solid rgba(245, 215, 110, 0.55)",
  borderRadius: 14,
  padding: "10px 16px 10px 12px",
  cursor: "pointer",
  fontSize: 15,
  boxShadow: "0 0 0 1px rgba(61,139,253,0.25), 0 8px 24px rgba(0,0,0,0.35)",
  minHeight: 60,
};

const triggerStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 10,
  background: "rgba(28, 48, 82, 0.95)",
  color: "var(--cl-muted)",
  border: "1.5px solid rgba(61,139,253,0.55)",
  borderRadius: 12,
  padding: "10px 14px",
  cursor: "pointer",
  fontSize: 14,
  minHeight: 44,
};

const compactTriggerStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  background: "rgba(18, 26, 43, 0.9)",
  color: "var(--cl-muted)",
  border: "1px solid var(--cl-border)",
  borderRadius: 10,
  padding: "8px 12px",
  cursor: "pointer",
  fontSize: 13,
};

const menuStyle: CSSProperties = {
  position: "absolute",
  right: 0,
  top: "calc(100% + 8px)",
  margin: 0,
  padding: 6,
  listStyle: "none",
  background: "var(--cl-surface)",
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  boxShadow: "0 12px 40px rgba(0,0,0,0.45)",
  zIndex: 50,
};

const itemStyle: CSSProperties = {
  width: "100%",
  display: "flex",
  alignItems: "center",
  gap: 8,
  border: "none",
  background: "transparent",
  color: "var(--cl-text)",
  borderRadius: 8,
  cursor: "pointer",
  textAlign: "left",
};
