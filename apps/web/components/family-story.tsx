"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";
import { FamilyArtwork, FamilyIcon } from "./family-art";

type View = components["schemas"]["FamilyView"];

export function FamilyChapterGate({ chapter, active = true, children }: { chapter: string; active?: boolean; children: ReactNode }) {
  const [entered, setEntered] = useState(chapter);
  const content = useRef<HTMLDivElement>(null);
  const continuing = useRef(false);
  useEffect(() => {
    if (continuing.current && chapter === entered) { content.current?.focus(); continuing.current = false; }
  }, [chapter, entered]);
  if (!active || chapter === entered) return <div ref={content} tabIndex={-1} role="group" aria-label={chapter}>{children}</div>;
  return <section className="practice-chapter" aria-label={t("experience.nextChapter")}>
    <FamilyIcon name="journey" /><p>{t("experience.nextChapter")}</p><h2>{chapter}</h2>
    <p>{t("experience.chapterHelp")}</p>
    <button type="button" className="button-primary" onClick={() => { continuing.current = true; setEntered(chapter); }}>{t("experience.enterChapter")}<FamilyIcon name="arrow" /></button>
  </section>;
}

export function FamilyJournal({ turns, coop, waiting }: { turns: View["transcript"]; coop: boolean; waiting: string }) {
  return <details className="practice-journal">
    <summary><FamilyIcon name="book" /><span>{t(coop ? "experience.sharedPlan" : "experience.journal")}</span><span>{turns.length}</span><FamilyIcon name="chevron" /></summary>
    <p>{t("experience.journalHelp")}</p>
    {turns.length ? <ol>{turns.map((turn) => <li key={turn.idx}>
      <span>{turn.idx}</span><div><strong>{t(coop ? `family.${turn.role}` : "experience.youChose")}</strong><p>{turn.text_th}</p></div>
    </li>)}</ol> : <p>{t("experience.emptyPlan")}</p>}
    <p className="practice-journal-next">{waiting}</p>
  </details>;
}

export function FamilyStoryboard({ turns, report, grandmother, onRestart }: {
  turns: View["transcript"]; report: NonNullable<View["report"]>; grandmother: boolean; onRestart: () => void;
}) {
  const [position, setPosition] = useState(0);
  const turn = turns[position];
  if (!turn) return null;
  const evidence = report.evidence.find((item) => item.idx === turn.idx);
  return <section className="practice-storyboard" aria-labelledby="family-storyboard-heading">
    <header><div><p>{t("experience.storyboardKicker")}</p><h3 id="family-storyboard-heading">{t("experience.storyboard")}</h3></div><FamilyIcon name="journey" /></header>
    <ol className="practice-story-pages" aria-label={t("experience.moments")}>{turns.map((item, i) => <li key={item.idx}>
      <button type="button" aria-current={position === i ? "step" : undefined} aria-label={`${t("experience.moment")} ${item.idx}`} onClick={() => setPosition(i)}>{item.idx}</button>
    </li>)}</ol>
    <div className="practice-story-frame" key={turn.idx} aria-live="polite" aria-atomic="true">
      <div className="practice-story-picture"><FamilyArtwork grandmother={grandmother} /><p><strong>{turn.speaker_th}</strong>{turn.prompt_th}</p></div>
      <div className="practice-story-beats">
        <article><span><FamilyIcon name="chat" />{t("experience.youChose")}</span><p>{turn.text_th}</p></article>
        <article><span><FamilyIcon name="heart" />{t("experience.theReply")}</span><p>{turn.reply_th}</p></article>
        {evidence && <article className={evidence.safe ? "" : "needs-review"}><span><FamilyIcon name="book" />{t("experience.reflect")}</span><p>{evidence.feedback_th}</p>
          <ul>{evidence.source_ids.map((id) => {
            const source = report.sources.find((item) => item.id === id);
            return source ? <li key={id}><a href={`#source-${id}`}>{source.title_th}</a></li> : null;
          })}</ul>
        </article>}
      </div>
    </div>
    <nav className="practice-story-controls" aria-label={t("experience.storyboard")}>
      <button type="button" disabled={position === 0} onClick={() => setPosition(position - 1)}>{t("experience.previous")}</button>
      <span>{position + 1} / {turns.length}</span>
      <button type="button" disabled={position === turns.length - 1} onClick={() => setPosition(position + 1)}>{t("experience.next")}</button>
    </nav>
    <button type="button" className="button-primary practice-restart" onClick={onRestart}>{t("experience.restart")}<FamilyIcon name="arrow" /></button>
  </section>;
}
