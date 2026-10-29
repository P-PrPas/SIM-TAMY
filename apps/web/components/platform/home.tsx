"use client";

import Link from "next/link";

import { t } from "@/lib/i18n";
import { useLogin } from "@/lib/use-login";
import { useV2 } from "@/lib/use-v2";
import { v2 } from "@/lib/v2-api";

import { Async, DemoBadge, formatDate } from "./shared";
import { LearningStages, StageArt } from "./stages";

function Continue() {
  const { account: profile } = useLogin();
  const account = profile?.role === "learner" ? profile.id : undefined;
  const passport = useV2(account ? (s) => v2.passport(account, s) : null, `passport:${account ?? ""}`);
  const latest = account
    ? [...(passport.data?.attempts ?? [])].filter((a) => a.finished_at)
      .sort((a, b) => (b.finished_at ?? "").localeCompare(a.finished_at ?? ""))[0]
    : undefined;
  return <section className="pf-card" aria-labelledby="continue-title">
    <div className="pf-row"><h2 id="continue-title">{t("platform.home.continueTitle")}</h2>{account && <DemoBadge />}</div>
    {!account && <><p className="pf-muted">{t("platform.home.continuePick")}</p><Link href="/login" className="pf-link">{t("platform.login.submit")}</Link></>}
    {account && <Async r={passport}>{() => latest
      ? <>
        <p className="pf-muted">{t("platform.home.continueLast")}</p>
        <p><strong>{latest.title_th}</strong>{latest.finished_at && <> <span className="pf-muted">({formatDate(latest.finished_at)})</span></>}</p>
        <Link href="/profile" className="pf-link">{t("platform.login.viewProgress")}<span aria-hidden="true"> →</span></Link>
      </>
      : <>
        <p className="pf-muted">{t("platform.home.continueNone")}</p>
        <Link href="/lab" className="pf-link">{t("platform.home.ctaLab")}<span aria-hidden="true"> →</span></Link>
      </>}</Async>}
  </section>;
}

export function Home() {
  return <main className="pf-page pf-home">
    <section className="pf-hero pf-home-hero">
      <div>
        <p className="eyebrow"><span className="eyebrow-dot" aria-hidden="true" />{t("platform.home.eyebrow")}</p>
        <h1>{t("platform.home.title")}</h1>
        <p className="pf-lead">{t("platform.home.description")}</p>
        <div className="pf-actions">
          <a href="#stages" className="button-primary">{t("platform.home.ctaStart")}</a>
        </div>
      </div>
      <figure className="pf-home-preview">
        <StageArt stage={1} />
        <figcaption><strong>{t("platform.home.previewTitle")}</strong><p>{t("platform.home.previewText")}</p></figcaption>
      </figure>
    </section>

    <section id="stages" aria-labelledby="stages-title" className="pf-section">
      <div className="section-heading"><div><h2 id="stages-title">{t("platform.home.stagesTitle")}</h2><p className="pf-muted">{t("platform.home.stagesIntro")}</p></div></div>
      <LearningStages />
    </section>

    <div className="pf-section pf-home-account">
      <Continue />
    </div>
    <aside className="pf-institution pf-section">
      <div><h2>{t("platform.home.pillar4Title")}</h2><p className="pf-muted">{t("platform.home.pillar4Text")}</p></div>
      <Link href="/institution" className="button-secondary">{t("platform.home.pillar4Cta")}</Link>
    </aside>
  </main>;
}
