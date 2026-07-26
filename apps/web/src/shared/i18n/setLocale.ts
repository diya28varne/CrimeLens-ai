"use client";

import i18n, { persistLocale, type AppLocale } from "@/shared/i18n";

export async function setAppLocale(locale: AppLocale) {
  await i18n.changeLanguage(locale);
  persistLocale(locale);
  window.dispatchEvent(new CustomEvent("cl:locale", { detail: { locale } }));
}

export type { AppLocale };
