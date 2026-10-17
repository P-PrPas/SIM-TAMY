"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { t } from "@/lib/i18n";

const steps = ["briefing", "chat", "decision", "closing", "report"] as const;

export function SiteHeader() {
  const path = usePathname();
  const current = steps.findIndex((step) => path === `/${step}`);

  return <>
    <header className="site-header">
      <div className="site-nav">
        <Link href="/" className="brand" aria-label={t("app.title")}>
          <Image src="/brand/logo.png" width={48} height={48} alt="" priority />
          <span><strong>SIM-TAMY<span className="brand-dot">.</span></strong><small>{t("brand.tagline")}</small></span>
        </Link>
        <nav aria-label={t("nav.label")}>
          <Link href="/" aria-current={path === "/" ? "page" : undefined}>{t("nav.learn")}</Link>
          <Link href="/replay" aria-current={path === "/replay" ? "page" : undefined}>{t("nav.replay")}</Link>
          <Link href="/instructor" className="nav-instructor" aria-current={path === "/instructor" ? "page" : undefined}>{t("instructor.link")}<span aria-hidden="true"> ↗</span></Link>
        </nav>
      </div>
    </header>
    {current >= 0 && <nav className="learning-progress" aria-label={t("nav.progress")}>
      <ol>{steps.map((step, index) => <li key={step} aria-current={current === index ? "step" : undefined} className={index < current ? "is-complete" : ""}>
        <span className="step-number" aria-hidden="true">{index < current ? "✓" : String(index + 1).padStart(2, "0")}</span>
        <span>{t(`steps.${step}`)}</span>
      </li>)}</ol>
    </nav>}
  </>;
}

export function SiteFooter() {
  return <footer className="site-footer"><div><strong>SIM-TAMY<span className="brand-dot">.</span></strong><p>{t("brand.footer")}</p></div></footer>;
}
