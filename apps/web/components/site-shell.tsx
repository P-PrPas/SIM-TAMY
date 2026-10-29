"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { t } from "@/lib/i18n";
import { useLogin } from "@/lib/use-login";
import { isInstitution } from "@/lib/demo-login";
import { AccountMenu } from "./account-menu";

const NAV = [
  ["/", "platform.nav.home"], ["/learn", "platform.nav.learn"], ["/lab", "platform.nav.lab"],
  ["/knowledge", "platform.nav.knowledge"],
] as const;
const isCurrent = (path: string, href: string) => (href === "/" ? path === "/" : path === href || path.startsWith(`${href}/`));

const steps = ["briefing", "chat", "decision", "closing", "report"] as const;

export function SiteHeader() {
  const path = usePathname();
  const current = steps.findIndex((step) => path === `/${step}`);
  const [open, setOpen] = useState(false);
  const { account, ready } = useLogin();
  const staff = account ? isInstitution(account) : false;

  return <>
    <header className={`site-header${current >= 0 ? " is-focused" : ""}`}>
      <div className="site-nav">
        <Link href={staff ? "/institution" : "/"} className="brand">
          <Image src="/brand/logo.png" width={48} height={48} alt="" priority />
          <span><strong>SIM-TAMY<span className="brand-dot">.</span></strong><small>{t("brand.tagline")}</small></span>
        </Link>
        {!ready || path === "/login" ? null : current >= 0 ? <Link href="/learn" className="button-text">{t("platform.nav.exit")}</Link> : <>
        <button type="button" className="nav-toggle" aria-expanded={open} aria-controls="site-menu" onClick={() => setOpen(!open)}>{t(open ? "platform.nav.closeMenu" : "platform.nav.openMenu")}<span aria-hidden="true">{open ? " ×" : " ☰"}</span></button>
        <nav id="site-menu" className={open ? "is-open" : ""} aria-label={t("nav.label")} onClick={() => setOpen(false)} onKeyDown={(event) => {
          if (event.key === "Escape") { setOpen(false); event.currentTarget.parentElement?.querySelector<HTMLButtonElement>(".nav-toggle")?.focus(); }
        }}>
          {staff ? <Link href="/institution" aria-current={path.startsWith("/institution") ? "page" : undefined}>{t("institution.title")}</Link>
            : NAV.map(([href, key]) => <Link key={href} href={href} aria-current={isCurrent(path, href) ? "page" : undefined}>{t(key)}</Link>)}
        </nav>
        </>}
        {path !== "/login" && <AccountMenu />}
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
  const { account, ready } = useLogin();
  if (!ready || (account && isInstitution(account))) return null;
  return <footer className="site-footer"><div><strong>SIM-TAMY<span className="brand-dot">.</span></strong><p>{t("brand.footer")}</p><Link href="/validation" className="inline-flex py-3 font-semibold">{t("validation.link")}</Link></div></footer>;
}
