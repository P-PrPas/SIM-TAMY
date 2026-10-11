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
      <body className="min-h-screen bg-white text-slate-900">
        {/* AGENTS.md rule 9: education-only banner on every surface */}
        <div role="note" className="bg-amber-100 px-4 py-2 text-center text-base text-amber-950">
          {t("banner.educationOnly")}
        </div>
        {children}
      </body>
    </html>
  );
}
