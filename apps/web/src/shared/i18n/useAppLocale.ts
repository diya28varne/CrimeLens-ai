"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { isAppLocale, type AppLocale } from "@/shared/i18n";

/** Current UI locale — updates instantly when LanguageSwitcher changes language. */
export function useAppLocale(): AppLocale {
  const { i18n } = useTranslation();
  const [locale, setLocale] = useState<AppLocale>(
    i18n.language?.startsWith("kn") ? "kn" : "en",
  );

  useEffect(() => {
    const sync = (lng?: string) => {
      const next = lng?.startsWith("kn") ? "kn" : "en";
      setLocale(next);
    };
    sync(i18n.language);
    const onLang = (lng: string) => sync(lng);
    const onCustom = (e: Event) => {
      const detail = (e as CustomEvent<{ locale?: string }>).detail?.locale;
      if (isAppLocale(detail)) setLocale(detail);
    };
    i18n.on("languageChanged", onLang);
    window.addEventListener("cl:locale", onCustom);
    return () => {
      i18n.off("languageChanged", onLang);
      window.removeEventListener("cl:locale", onCustom);
    };
  }, [i18n]);

  return locale;
}
