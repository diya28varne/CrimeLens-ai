import type { Metadata } from "next";
import { Noto_Sans, Noto_Sans_Kannada } from "next/font/google";
import type { ReactNode } from "react";

import { AppProviders } from "@/shared/providers/AppProviders";

import "./globals.css";

const notoSans = Noto_Sans({
  subsets: ["latin"],
  variable: "--font-noto-sans",
  display: "swap",
});

const notoKannada = Noto_Sans_Kannada({
  subsets: ["kannada"],
  variable: "--font-noto-kannada",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CrimeLens AI",
  description: "AI-Powered Crime Intelligence & Decision Support Platform — Karnataka State Police",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${notoSans.variable} ${notoKannada.variable}`}>
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
