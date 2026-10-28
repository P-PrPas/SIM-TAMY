"use client";

import Link from "next/link";

import { t } from "@/lib/i18n";
import { useDemoAccount } from "@/lib/use-demo-account";
import { useV2 } from "@/lib/use-v2";
import { storyHref, v2, type Attempt, type LearningPaths, type PathObjective } from "@/lib/v2-api";

import { Async, DemoBadge, labelOr } from "./shared";

export function StageCards() {
  const paths = useV2((s) => v2.learningPaths(s), "paths");
  return <main className="pf-page">
    <header><h1>{t("platform.learn.title")}</h1><p className="pf-lead">{t("platform.learn.intro")}</p></header>
    <Async r={paths}>{(data) => data.stages.length === 0
      ? <p className="pf-note">{t("platform.learn.empty")}</p>
      : <ol className="pf-grid pf-list">
        {data.stages.map((s) => <li key={s.stage} className="pf-card">
          <span className="pf-kicker">{t("platform.learn.stageLabel")} {s.stage}</span>
          <h2>{s.title_th}</h2>
          <p className="pf-muted">{s.summary_th}</p>
          <p className="pf-meta">{t("platform.learn.objectiveCount")}: {s.objectives.length}</p>
          <Link href={`/learn/${encodeURIComponent(String(s.stage))}`} className="pf-link">{t("platform.learn.openStage")}<span aria-hidden="true"> →</span></Link>
        </li>)}
      </ol>}</Async>
  </main>;
}

/** Finished attempts that touched an objective. Completed means finished, nothing else (LP-03). */
function finishedFor(objectiveId: string, attempts: Attempt[]): number {
  return attempts.filter((a) => a.finished_at && a.objective_ids.includes(objectiveId)).length;
}

function Objective({ o, attempts, account, units, scenarios }: {
  o: PathObjective; attempts: Attempt[] | null; account: boolean;
  units: Map<string, string>; scenarios: Map<string, { title: string; href: string }>;
}) {
  const linkedUnits = o.unit_ids.filter((id) => units.has(id));
  const linkedScenarios = o.story_ids.filter((id) => scenarios.has(id));
  const done = attempts ? finishedFor(o.id, attempts) : 0;
  return <li className="pf-card" id={o.id}>
    <h3>{o.title_th}</h3>
    <p className="pf-meta">{t("platform.learn.dimension")}: {labelOr(`platform.learn.dim_${o.dimension}`, o.dimension)}</p>
    <p className="pf-progress" data-done={done > 0}>
      {!account ? t("platform.learn.progressPick")
        : attempts === null ? t("platform.common.loading")
        : done > 0 ? `${t("platform.learn.progressDone")} ${done} ${t("platform.learn.progressTimes")}` : t("platform.learn.progressNone")}
    </p>
    <h4>{t("platform.learn.units")}</h4>
    {linkedUnits.length === 0 ? <p className="pf-muted">{t("platform.learn.noUnits")}</p>
      : <ul className="pf-list">{linkedUnits.map((id) => <li key={id}><Link href={`/knowledge/${encodeURIComponent(id)}`} className="pf-link">{units.get(id)}</Link></li>)}</ul>}
    <h4>{t("platform.learn.scenarios")}</h4>
    {linkedScenarios.length === 0 ? <p className="pf-muted">{t("platform.learn.noScenarios")}</p>
      : <ul className="pf-list">{linkedScenarios.map((id) => {
        const s = scenarios.get(id);
        return <li key={id}><Link href={s?.href ?? "/lab"} className="pf-link">{s?.title}</Link></li>;
      })}</ul>}
  </li>;
}

export function StageDetail({ stage }: { stage: string }) {
  const account = useDemoAccount();
  const paths = useV2((s) => v2.learningPaths(s), "paths");
  const units = useV2((s) => v2.units(s), "units");
  const stories = useV2((s) => v2.stories(s), "stories");
  const cases = useV2((s) => v2.cases(s), "cases");
  const passport = useV2(account ? (s) => v2.passport(account, s) : null, `passport:${account ?? ""}`);

  // Only published units and playable scenarios are linked (LP-04): anything the APIs do not list stays hidden.
  const unitTitles = new Map((units.data?.items ?? []).map((u) => [u.id, u.title_th]));
  const scenarios = new Map<string, { title: string; href: string }>();
  for (const c of cases.data?.items ?? []) scenarios.set(c.case_id, { title: `${c.title_th} (${t("platform.learn.soloCase")})`, href: "/lab/solo" });
  for (const s of stories.data ?? []) scenarios.set(s.id, { title: s.title_th, href: storyHref(s.id) });

  const render = (data: LearningPaths) => {
    const current = data.stages.find((s) => String(s.stage) === stage);
    if (!current) return <p className="pf-note">{t("platform.learn.notFound")}</p>;
    return <>
      <header>
        <p className="pf-kicker">{t("platform.learn.stageLabel")} {current.stage}</p>
        <h1>{current.title_th}</h1><p className="pf-lead">{current.summary_th}</p>
      </header>
      <section aria-labelledby="objectives-title" className="pf-section">
        <div className="pf-row"><h2 id="objectives-title">{t("platform.learn.objectives")}</h2>{account && <DemoBadge />}</div>
        <p className="pf-muted">{t("platform.learn.progressNote")}</p>
        <ol className="pf-list pf-stack">
          {current.objectives.map((o) => <Objective key={o.id} o={o} account={Boolean(account)} units={unitTitles} scenarios={scenarios}
            attempts={passport.data ? passport.data.attempts : null} />)}
        </ol>
      </section>
    </>;
  };
  return <main className="pf-page">
    <Link href="/learn" className="pf-link"><span aria-hidden="true">← </span>{t("platform.learn.allStages")}</Link>
    <Async r={paths}>{render}</Async>
  </main>;
}
