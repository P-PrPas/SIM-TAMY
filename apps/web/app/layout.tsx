import type { Metadata } from "next";
import type { ReactNode } from "react";
import localFont from "next/font/local";

import { SiteFooter, SiteHeader } from "@/components/site-shell";
import { t } from "@/lib/i18n";

import "./globals.css";

const thaiFont = localFont({ src: "./fonts/NotoSansThai.ttf", display: "swap", variable: "--font-thai", weight: "100 900" });

export const metadata: Metadata = {
  title: t("app.title"),
  description: t("app.description"),
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="th" data-scroll-behavior="smooth">
      <body className={`${thaiFont.variable} min-h-screen text-ink`}>
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-brand-950 focus:px-4 focus:py-3 focus:text-white">
          {t("app.skipToContent")}
        </a>
        <SiteHeader />
        <div role="note" className="education-banner">
          {t("banner.educationOnly")}
        </div>
        <div id="main-content" tabIndex={-1}>{children}</div>
        <SiteFooter />
      </body>
    </html>
  );
}
