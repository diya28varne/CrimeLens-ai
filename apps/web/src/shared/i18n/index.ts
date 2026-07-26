import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enCommon from "@/messages/en/common.json";
import enDashboard from "@/messages/en/dashboard.json";
import enAnalytics from "@/messages/en/analytics.json";
import enReports from "@/messages/en/reports.json";
import enAi from "@/messages/en/ai.json";
import enAuth from "@/messages/en/auth.json";
import enSettings from "@/messages/en/settings.json";

import knCommon from "@/messages/kn/common.json";
import knDashboard from "@/messages/kn/dashboard.json";
import knAnalytics from "@/messages/kn/analytics.json";
import knReports from "@/messages/kn/reports.json";
import knAi from "@/messages/kn/ai.json";
import knAuth from "@/messages/kn/auth.json";
import knSettings from "@/messages/kn/settings.json";

export const LOCALE_STORAGE_KEY = "cl_locale";
export const LOCALES = ["en", "kn"] as const;
export type AppLocale = (typeof LOCALES)[number];

export function isAppLocale(value: string | null | undefined): value is AppLocale {
  return value === "en" || value === "kn";
}

export function readStoredLocale(): AppLocale {
  if (typeof window === "undefined") return "en";
  try {
    const raw = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    if (isAppLocale(raw)) return raw;
  } catch {
    /* ignore */
  }
  return "en";
}

export function persistLocale(locale: AppLocale) {
  try {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    document.cookie = `${LOCALE_STORAGE_KEY}=${locale};path=/;max-age=31536000;samesite=lax`;
    document.documentElement.lang = locale === "kn" ? "kn" : "en";
  } catch {
    /* ignore */
  }
}

const resources = {
  en: {
    common: enCommon,
    dashboard: enDashboard,
    analytics: enAnalytics,
    reports: enReports,
    ai: enAi,
    auth: enAuth,
    settings: enSettings,
  },
  kn: {
    common: knCommon,
    dashboard: knDashboard,
    analytics: knAnalytics,
    reports: knReports,
    ai: knAi,
    auth: knAuth,
    settings: knSettings,
  },
};

void i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  defaultNS: "common",
  ns: ["common", "dashboard", "analytics", "reports", "ai", "auth", "settings"],
  interpolation: { escapeValue: false },
  returnNull: false,
});

export default i18n;
