"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { t } from "@/lib/i18n";

const NAV = [
  ["/", "platform.nav.home"], ["/learn", "platform.nav.learn"], ["/lab", "platform.nav.lab"],
  ["/passport", "platform.nav.passport"], ["/knowledge", "platform.nav.knowledge"],
] as const;
const isCurrent = (path: string, href: string) => (href === "/" ? path === "/" : path === href || path.startsWith(`${href}/`));

const steps = ["briefing", "chat", "decision", "closing", "report"] as const;

export function SiteHeader() {
  const path = usePathname();
  const current = steps.findIndex((step) => path === `/${step}`);

  return <>
    <header className="site-header">
      <div className="site-nav">
        <Link href="/" className="brand">
          <Image src="/brand/logo.png" width={48} height={48} alt="" priority />
          <span><strong>SIM-TAMY<span className="brand-dot">.</span></strong><small>{t("brand.tagline")}</small></span>
        </Link>
        <nav aria-label={t("nav.label")}>
          {NAV.map(([href, key]) => <Link key={href} href={href} aria-current={isCurrent(path, href) ? "page" : undefined}>{t(key)}</Link>)}
          <Link href="/institution" className="nav-instructor" aria-current={isCurrent(path, "/institution") ? "page" : undefined}>{t("platform.nav.institution")}</Link>
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
  return <footer className="site-footer"><div><strong>SIM-TAMY<span className="brand-dot">.</span></strong><p>{t("brand.footer")}</p><Link href="/validation" className="inline-flex py-3 font-semibold">{t("validation.link")}</Link></div></footer>;
}
