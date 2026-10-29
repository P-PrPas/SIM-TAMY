"use client";

import Link from "next/link";

import { t } from "@/lib/i18n";
import { useLogin } from "@/lib/use-login";
import { learningProgress } from "@/lib/learning-progress";
import { storyHref } from "@/lib/v2-api";
import { unitReady } from "@/lib/learning-path";
import { useV2 } from "@/lib/use-v2";
import { v2, type Attempt } from "@/lib/v2-api";

import { Async, DemoBadge, formatDate } from "./shared";

function AttemptCard({ a, objectiveTitle }: { a: Attempt; objectiveTitle: (id: string) => string }) {
  const notMet = a.safety_status === "SAFETY_NOT_MET";
  return <li className="pf-card">
    <h3>{a.title_th}</h3>
    {a.finished_at && <p className="pf-meta">{t("platform.passport.finishedOn")} {formatDate(a.finished_at)}</p>}
    <p className={notMet ? "pf-safety pf-safety-not-met" : "pf-safety pf-safety-met"} role={notMet ? "alert" : "status"}>
      <strong>{t("platform.passport.safety")}</strong>{" "}
      {t(notMet ? "report.safetyNotMet" : "report.safetyMet")}
    </p>
    {a.score_total !== null && <p className="pf-meta">{t("platform.passport.score")}: {a.score_total}</p>}
    {a.objective_ids.length > 0 && <p className="pf-meta">{t("platform.passport.objectives")}: {a.objective_ids.map(objectiveTitle).join(", ")}</p>}
  </li>;
}

export function Passport() {
  const { account: profile } = useLogin();
  const account = profile?.role === "learner" ? profile.id : undefined;
  const passport = useV2(account ? (s) => v2.passport(account, s) : null, `passport:${account ?? ""}`);
  const paths = useV2((s) => v2.learningPaths(s), "paths");
  const units = useV2((s) => v2.units(s), "profile-units");

  const titles = new Map<string, string>();
  for (const stage of paths.data?.stages ?? []) for (const o of stage.objectives) titles.set(o.id, o.title_th);
  const objectiveTitle = (id: string) => titles.get(id) ?? id;

  return <main className="pf-page">
    <header className="profile-header">
      <div className="account-avatar profile-avatar" aria-hidden="true">{profile?.display_name_th.slice(0, 1)}</div>
      <div><p className="pf-kicker">{t("platform.dashboard.profile")}</p><h1>{profile?.display_name_th ?? t("platform.dashboard.profile")}</h1>
      <p className="pf-muted">{t("platform.passport.intro")}</p></div><DemoBadge />
    </header>
    {!account ? <>
      <Link href="/login?next=/profile" className="button-primary">{t("platform.login.submit")}</Link>
    </> : <Async r={passport}>{(data) => {
      const attempts = data.attempts.filter((a) => a.finished_at)
        .sort((a, b) => (b.finished_at ?? "").localeCompare(a.finished_at ?? ""));
      const lessons = data.lessons ?? [];
      const progress = learningProgress(attempts, lessons);
      const counts = new Map<string, number>();
      for (const a of attempts) for (const id of new Set(a.objective_ids)) counts.set(id, (counts.get(id) ?? 0) + 1);
      return <>
        <section aria-label={t("platform.dashboard.overview")} className="dashboard-stats">
          {[["lessons", new Set(lessons.map((l) => l.unit_id)).size], ["simulations", attempts.length], ["stages", progress.filter((s) => s.completed === 2).length]].map(([key, value]) => <div key={key} className="pf-card"><p className="pf-muted">{t(`platform.dashboard.${key}`)}</p><strong className="dashboard-number">{value}</strong></div>)}
        </section>
        <div className="profile-layout">
        <div>
        <section aria-labelledby="progress-title" className="pf-card">
          <h2 id="progress-title">{t("platform.dashboard.progress")}</h2>
          <p className="pf-muted">{t("platform.dashboard.progressNote")}</p>
          <Async r={paths}>{(path) => <ol className="pf-list progress-list">{progress.map((s) => {
            const stage = path.stages.find((p) => String(p.stage) === String(s.stage));
            const title = stage?.title_th ?? `${t("platform.learn.stageLabel")} ${s.stage}`;
            return <li key={s.stage}>
              <div className="pf-row"><Link href={`/learn/${s.stage}`} className="pf-link">{title}</Link><span className="pf-meta">{s.completed}/2 {t("platform.dashboard.activities")}</span></div>
              <progress value={s.completed} max={2} aria-label={title} />
              <div className="progress-actions"><span>{t(s.lessonDone ? "platform.dashboard.lessonDone" : "platform.dashboard.lessonPending")}</span><span>{t(s.simulationDone ? "platform.dashboard.simulationDone" : "platform.dashboard.simulationPending")}</span>
                <Link href={s.lessonDone ? storyHref(s.stories[0]!) : `/knowledge/${s.units[0]}`} className="pf-link" aria-label={`${t("platform.dashboard.continue")} ${title}`}>{t("platform.dashboard.continue")}</Link></div>
            </li>;
          })}</ol>}</Async>
        </section>
        <section aria-labelledby="badges-title" className="pf-section">
          <h2 id="badges-title">{t("platform.passport.badges")}</h2>
          <p className="pf-muted">{t("platform.passport.badgesNote")}</p>
          {counts.size === 0 ? <p className="pf-note">{t("platform.passport.noBadges")}</p>
            : <ul className="pf-list pf-chips">{[...counts].map(([id, n]) => <li key={id} className="pf-chip">
              {objectiveTitle(id)} <small>{t("platform.passport.badgeTimes").replace("{n}", String(n))}</small>
            </li>)}</ul>}
        </section>
        <section aria-labelledby="history-title" className="pf-section">
          <h2 id="history-title">{t("platform.passport.history")}</h2>
          <p className="pf-muted">{t("platform.passport.safetyNote")}</p>
          {attempts.length === 0 ? <div className="pf-card"><p>{t("platform.passport.empty")}</p><Link href="/learn" className="pf-link">{t("platform.home.ctaStart")}</Link></div>
            : <ul className="pf-stack pf-list">{attempts.map((a) => <AttemptCard key={a.room_id} a={a} objectiveTitle={objectiveTitle} />)}</ul>}
          {attempts.some((a) => a.score_total !== null) && <p className="pf-meta">{t("platform.passport.scoreNote")}</p>}
        </section>
        <section className="pf-section" aria-labelledby="lessons-title"><h2 id="lessons-title">{t("platform.dashboard.lessonHistory")}</h2>
          <Async r={units}>{(catalog) => lessons.length === 0 ? <p className="pf-note">{t("platform.dashboard.noLessons")}</p> : <ul className="pf-list pf-stack">{lessons.map((lesson) => <li className="pf-card" key={lesson.unit_id}>
            {unitReady(lesson.unit_id) ? <Link className="pf-link" href={`/knowledge/${encodeURIComponent(lesson.unit_id)}`}>{catalog.items.find((u) => u.id === lesson.unit_id)?.title_th ?? lesson.unit_id}</Link> : <p>{catalog.items.find((u) => u.id === lesson.unit_id)?.title_th ?? lesson.unit_id}</p>}
            <p className="pf-meta">{formatDate(lesson.completed_at)}</p>
          </li>)}</ul>}</Async>
        </section>
        </div>
        <aside className="pf-card profile-info"><h2>{t("platform.dashboard.about")}</h2>
          <dl><dt>{t("platform.login.username")}</dt><dd>{profile?.id}</dd><dt>{t("platform.dashboard.role")}</dt><dd>{t("institution.staff.role.learner")}</dd></dl>
          <p className="pf-meta">{t("platform.common.demoNote")}</p>
        </aside>
        </div>
      </>;
    }}</Async>}
  </main>;
}
