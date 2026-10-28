"use client";

import Link from "next/link";

import { t } from "@/lib/i18n";
import { CORE_PATH, storyReady, unitReady } from "@/lib/learning-path";
import { useDemoAccount } from "@/lib/use-demo-account";
import { useV2 } from "@/lib/use-v2";
import { storyHref, v2, type Attempt, type LearningPaths, type PathObjective } from "@/lib/v2-api";

import { NurseryHouse } from "../pixel/house";
import { Disabled } from "./not-ready";
import { Async, DemoBadge, labelOr } from "./shared";

export function StageCards() {
  const account = useDemoAccount();
  const paths = useV2((s) => v2.learningPaths(s), "paths");
  const passport = useV2(account ? (s) => v2.passport(account, s) : null, `passport:${account ?? ""}`);
  return <main className="pf-page">
    <header><h1>{t("platform.learn.title")}</h1><p className="pf-lead">{t("platform.learn.intro")}</p></header>
    {account ? <Async r={passport}>{(data) => <NurseryHouse attempts={data.attempts} lessons={data.lessons} />}</Async>
      : <NurseryHouse attempts={null} />}
    <Async r={paths}>{(data) => data.stages.length === 0
      ? <p className="pf-note">{t("platform.learn.empty")}</p>
      : <ol className="pf-grid pf-list">
        {data.stages.map((s) => <li key={s.stage} className="pf-card">
          <span className="pf-kicker">{t("platform.learn.stageLabel")} {s.stage}</span>
          <h2>{s.title_th}</h2>
          <p className="pf-muted">{s.summary_th}</p>
          <Link href={`/learn/${encodeURIComponent(String(s.stage))}`} className="pf-link">{t("platform.learn.openStage")}<span aria-hidden="true"> →</span></Link>
        </li>)}
      </ol>}</Async>
  </main>;
}

/** Finished attempts that touched an objective. Completed means finished, nothing else (LP-03). */
function finishedFor(objectiveId: string, attempts: Attempt[]): number {
  return attempts.filter((a) => a.finished_at && a.objective_ids.includes(objectiveId)).length;
}

function Objective({ o, attempts, account }: {
  o: PathObjective; attempts: Attempt[] | null; account: boolean;
}) {
  const done = attempts ? finishedFor(o.id, attempts) : 0;
  return <li className="pf-card" id={o.id}>
    <h3>{o.title_th}</h3>
    <p className="pf-meta">{t("platform.learn.dimension")}: {labelOr(`platform.learn.dim_${o.dimension}`, o.dimension)}</p>
    <p className="pf-progress" data-done={done > 0}>
      {!account ? t("platform.learn.progressPick")
        : attempts === null ? t("platform.common.loading")
        : done > 0 ? `${t("platform.learn.progressDone")} ${done} ${t("platform.learn.progressTimes")}` : t("platform.learn.progressNone")}
    </p>
  </li>;
}

export function StageDetail({ stage }: { stage: string }) {
  const account = useDemoAccount();
  const paths = useV2((s) => v2.learningPaths(s), "paths");
  const units = useV2((s) => v2.units(s), "units");
  const stories = useV2((s) => v2.stories(s), "stories");
  const passport = useV2(account ? (s) => v2.passport(account, s) : null, `passport:${account ?? ""}`);

  // Only published units and playable scenarios are linked (LP-04): anything the APIs do not list stays hidden.
  const unitTitles = new Map((units.data?.items ?? []).map((u) => [u.id, u.title_th]));
  const scenarios = new Map<string, { title: string; href: string }>();
  for (const s of stories.data ?? []) scenarios.set(s.id, { title: s.title_th, href: storyHref(s.id) });

  const render = (data: LearningPaths) => {
    const current = data.stages.find((s) => String(s.stage) === stage);
    if (!current) return <p className="pf-note">{t("platform.learn.notFound")}</p>;
    const core = CORE_PATH.find((s) => s.stage === current.stage);
    // Ready items first, then the rest of the stage greyed out so the roadmap stays visible.
    const inStage = (ids: string[], first: string[]) => [...new Set([...first, ...ids])];
    const unitIds = inStage(current.objectives.flatMap((o) => o.unit_ids), core?.units ?? []).filter((id) => unitTitles.has(id));
    const storyIds = inStage(current.objectives.flatMap((o) => o.story_ids), core?.stories ?? []).filter((id) => scenarios.has(id));
    const readings = (ids: string[]) => <ul className="pf-list pf-stack">{ids.map((id) => <li key={id}>{unitReady(id)
      ? <Link href={`/knowledge/${encodeURIComponent(id)}`} className="pf-link">{unitTitles.get(id)}</Link>
      : <Disabled>{unitTitles.get(id)}</Disabled>}</li>)}</ul>;
    return <>
      <header>
        <p className="pf-kicker">{t("platform.learn.stageLabel")} {current.stage}</p>
        <h1>{current.title_th}</h1><p className="pf-lead">{current.summary_th}</p>
      </header>
      <section className="pf-section" aria-labelledby="read-title">
        <h2 id="read-title">{t("platform.learn.units")}</h2>
        <Async r={units}>{() => unitIds.length ? readings(unitIds) : <p className="pf-note">{t("platform.learn.noUnits")}</p>}</Async>
      </section>
      <section className="pf-section" aria-labelledby="practice-title">
        <h2 id="practice-title">{t("platform.learn.scenarios")}</h2>
        <Async r={stories}>{() => storyIds.length ? <ul className="pf-list pf-stack">{storyIds.map((id) => <li key={id}>{storyReady(id)
          ? <Link href={scenarios.get(id)!.href} className="pf-link">{scenarios.get(id)!.title}</Link>
          : <Disabled>{scenarios.get(id)!.title}</Disabled>}</li>)}</ul>
          : <p className="pf-note">{t("platform.learn.noScenarios")}</p>}</Async>
      </section>
      <details className="pf-section pf-disclosure">
        <summary>{t("platform.learn.objectives")}</summary>
        {account && <DemoBadge />}
        <p className="pf-muted">{t("platform.learn.progressNote")}</p>
        {passport.error && <Async r={passport}>{() => null}</Async>}
        <ol className="pf-list pf-stack">
          {current.objectives.map((o) => <Objective key={o.id} o={o} account={Boolean(account)}
            attempts={passport.data ? passport.data.attempts : null} />)}
        </ol>
      </details>
    </>;
  };
  return <main className="pf-page">
    <Link href="/learn" className="pf-link"><span aria-hidden="true">← </span>{t("platform.learn.allStages")}</Link>
    <Async r={paths}>{render}</Async>
  </main>;
}
