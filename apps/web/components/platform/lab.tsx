"use client";

import Link from "next/link";

import { t } from "@/lib/i18n";
import { useV2 } from "@/lib/use-v2";
import { GOLDEN_STORY_IDS, storyHref, v2, type StoryCard } from "@/lib/v2-api";

import { Async } from "./shared";

function StoryItem({ story, kicker }: { story: StoryCard; kicker?: string }) {
  return <li className="pf-card">
    {kicker && <span className="pf-kicker">{kicker}</span>}
    <h3>{story.title_th}</h3>
    <p className="pf-muted">{story.description_th}</p>
    <p className="pf-meta">
      {t(story.mode === "coop" ? "platform.lab.modeCoop" : "platform.lab.modeSolo")}
      {story.chapters_th.length > 1 && <> · {story.chapters_th.length} {t("platform.lab.chapters")}</>}
    </p>
    <Link href={storyHref(story.id)} className="button-gold">{t("platform.lab.start")}<span aria-hidden="true"> →</span></Link>
  </li>;
}

export function Lab() {
  const stories = useV2((s) => v2.stories(s), "stories");
  const cases = useV2((s) => v2.cases(s), "cases");
  const soloCases = (cases.data?.items ?? []).filter((c) => c.case_id !== "DEV-001");
  return <main className="pf-page">
    <header><h1>{t("platform.lab.title")}</h1><p className="pf-lead">{t("platform.lab.intro")}</p></header>
    <p className="pf-note">{t("platform.lab.pairNote")}</p>

    <Async r={stories}>{(all) => {
      const featured = GOLDEN_STORY_IDS.map((id) => all.find((s) => s.id === id)).filter((s) => s !== undefined);
      const others = all.filter((s) => !(GOLDEN_STORY_IDS as readonly string[]).includes(s.id));
      return <>
        {featured.length > 0 && <section aria-labelledby="featured-title" className="pf-section">
          <h2 id="featured-title">{t("platform.lab.featured")}</h2>
          <ul className="pf-grid pf-list">
            {featured.map((s) => <StoryItem key={s.id} story={s}
              kicker={t(s.id === GOLDEN_STORY_IDS[0] ? "platform.lab.kickerA" : "platform.lab.kickerB")} />)}
          </ul>
        </section>}
        <section aria-labelledby="others-title" className="pf-section">
          <h2 id="others-title">{t("platform.lab.otherStories")}</h2>
          {others.length === 0 ? <p className="pf-note">{t("platform.lab.empty")}</p>
            : <ul className="pf-grid pf-list">{others.map((s) => <StoryItem key={s.id} story={s} />)}</ul>}
        </section>
      </>;
    }}</Async>

    <section aria-labelledby="more-title" className="pf-section">
      <h2 id="more-title">{t("platform.lab.moreModules")}</h2>
      <ul className="pf-grid pf-list">
        <li className="pf-card">
          <h3>{t("platform.lab.soloTitle")}</h3>
          <p className="pf-muted">{t("platform.lab.soloText")}</p>
          {soloCases.length > 0 && <ul className="pf-list" aria-label={t("platform.lab.soloCases")}>
            {soloCases.map((c) => <li key={c.case_id}>{c.title_th}</li>)}
          </ul>}
          <Link href="/lab/solo" className="button-gold">{t("platform.lab.soloCta")}<span aria-hidden="true"> →</span></Link>
        </li>
        <li className="pf-card">
          <h3>{t("platform.lab.replayTitle")}</h3>
          <p className="pf-muted">{t("platform.lab.replayText")}</p>
          <Link href="/replay" className="pf-link">{t("platform.lab.replayCta")}<span aria-hidden="true"> →</span></Link>
        </li>
        <li className="pf-card">
          <h3>{t("platform.lab.instructorTitle")}</h3>
          <p className="pf-muted">{t("platform.lab.instructorText")}</p>
          <Link href="/instructor" className="pf-link">{t("platform.lab.instructorCta")}<span aria-hidden="true"> →</span></Link>
        </li>
        <li className="pf-card">
          <h3>{t("platform.lab.validationTitle")}</h3>
          <p className="pf-muted">{t("platform.lab.validationText")}</p>
          <Link href="/validation" className="pf-link">{t("platform.lab.validationCta")}<span aria-hidden="true"> →</span></Link>
        </li>
      </ul>
    </section>
  </main>;
}
