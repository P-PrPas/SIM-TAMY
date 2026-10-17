import type { Metadata } from "next";
import type { ReactNode } from "react";

import { t } from "@/lib/i18n";

import "./globals.css";

export const metadata: Metadata = {
  title: t("app.title"),
  description: t("app.description"),
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="th">
      <body className="min-h-screen text-slate-900">
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-teal-950 focus:px-4 focus:py-3 focus:text-white">
          {t("app.skipToContent")}
        </a>
        {/* AGENTS.md rule 9: education-only banner on every surface */}
        <div role="note" className="bg-amber-100 px-4 py-2 text-center text-base text-amber-950">
          {t("banner.educationOnly")}
        </div>
        <div id="main-content" tabIndex={-1}>{children}</div>
      </body>
    </html>
  );
}
