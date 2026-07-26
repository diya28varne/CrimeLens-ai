"use client";

import { useEffect, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";

import i18n, { persistLocale, readStoredLocale } from "@/shared/i18n";

export function I18nProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    const locale = readStoredLocale();
    if (i18n.language !== locale) {
      void i18n.changeLanguage(locale);
    }
    persistLocale(locale);
  }, []);

  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
