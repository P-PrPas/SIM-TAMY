"use client";

import Link from "next/link";

import { t } from "@/lib/i18n";
import { storyReady } from "@/lib/learning-path";
import { useDemoAccount } from "@/lib/use-demo-account";
import { useV2 } from "@/lib/use-v2";
import { GOLDEN_STORY_IDS, storyHref, v2 } from "@/lib/v2-api";

import { ProfilePicker } from "./profile-picker";
import { DemoBadge, formatDate } from "./shared";

const PILLARS = [
  { n: 1, href: "/learn" }, { n: 2, href: "/lab" }, { n: 3, href: "/passport" }, { n: 4, href: "/institution" },
] as const;

function Continue() {
  const account = useDemoAccount();
  const passport = useV2(account ? (s) => v2.passport(account, s) : null, `passport:${account ?? ""}`);
  const latest = account
    ? [...(passport.data?.attempts ?? [])].filter((a) => a.finished_at)
      .sort((a, b) => (b.finished_at ?? "").localeCompare(a.finished_at ?? ""))[0]
    : undefined;
  return <section className="pf-card" aria-labelledby="continue-title">
    <div className="pf-row"><h2 id="continue-title">{t("platform.home.continueTitle")}</h2>{account && <DemoBadge />}</div>
    {!account && <p className="pf-muted">{t("platform.home.continuePick")}</p>}
    {account && passport.loading && <p role="status" className="pf-note">{t("platform.common.loading")}</p>}
    {account && !passport.loading && (latest
      ? <>
        <p className="pf-muted">{t("platform.home.continueLast")}</p>
        <p><strong>{latest.title_th}</strong>{latest.finished_at && <> <span className="pf-muted">({formatDate(latest.finished_at)})</span></>}</p>
        <Link href="/learn" className="pf-link">{t("platform.home.continueNext")}<span aria-hidden="true"> →</span></Link>
      </>
      : <>
        <p className="pf-muted">{t("platform.home.continueNone")}</p>
        <Link href="/lab" className="pf-link">{t("platform.home.ctaLab")}<span aria-hidden="true"> →</span></Link>
      </>)}
  </section>;
}

export function Home() {
  const stories = useV2((s) => v2.stories(s), "stories");
  const featured = GOLDEN_STORY_IDS.filter(storyReady).map((id) => stories.data?.find((s) => s.id === id)).filter((s) => s !== undefined);
  return <main className="pf-page">
    <section className="pf-hero">
      <p className="eyebrow"><span className="eyebrow-dot" aria-hidden="true" />{t("platform.home.eyebrow")}</p>
      <h1>{t("platform.home.title")}</h1>
      <p className="pf-lead">{t("platform.home.description")}</p>
      <div className="pf-actions">
        <Link href="/learn" className="button-primary">{t("platform.home.ctaStart")}<span aria-hidden="true"> →</span></Link>
        <Link href="/lab" className="button-text">{t("platform.home.ctaLab")}<span aria-hidden="true"> →</span></Link>
      </div>
    </section>

    <section aria-labelledby="pillars-title" className="pf-section">
      <h2 id="pillars-title">{t("platform.home.pillarsTitle")}</h2>
      <ol className="pf-grid pf-list">
        {PILLARS.map(({ n, href }) => <li key={n} className="pf-card">
          <span className="pf-kicker" aria-hidden="true">0{n}</span>
          <h3>{t(`platform.home.pillar${n}Title`)}</h3>
          <p className="pf-muted">{t(`platform.home.pillar${n}Text`)}</p>
          <Link href={href} className="pf-link">{t(`platform.home.pillar${n}Cta`)}<span aria-hidden="true"> →</span></Link>
        </li>)}
      </ol>
    </section>

    {featured.length > 0 && <section aria-labelledby="golden-title" className="pf-section">
      <h2 id="golden-title">{t("platform.home.goldenTitle")}</h2>
      <p className="pf-muted">{t("platform.home.goldenIntro")}</p>
      <ul className="pf-grid pf-list">
        {featured.map((story) => <li key={story.id} className="pf-card">
          <span className="pf-kicker">{t(story.id === GOLDEN_STORY_IDS[0] ? "platform.home.goldenAKicker" : "platform.home.goldenBKicker")}</span>
          <h3>{story.title_th}</h3>
          <p className="pf-muted">{story.description_th}</p>
          <Link href={storyHref(story.id)} className="button-gold">{t("platform.home.goldenCta")}<span aria-hidden="true"> →</span></Link>
        </li>)}
      </ul>
    </section>}

    <div className="pf-grid pf-section">
      <Continue />
      <ProfilePicker />
    </div>
  </main>;
}
