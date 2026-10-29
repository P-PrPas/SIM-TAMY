"use client";

import Link from "next/link";

import { t } from "@/lib/i18n";
import { useDemoAccount } from "@/lib/use-demo-account";
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
  const account = useDemoAccount();
  const passport = useV2(account ? (s) => v2.passport(account, s) : null, `passport:${account ?? ""}`);
  const paths = useV2((s) => v2.learningPaths(s), "paths");

  const titles = new Map<string, string>();
  for (const stage of paths.data?.stages ?? []) for (const o of stage.objectives) titles.set(o.id, o.title_th);
  const objectiveTitle = (id: string) => titles.get(id) ?? id;

  return <main className="pf-page">
    <header>
      <div className="pf-row"><h1>{t("platform.passport.title")}</h1><DemoBadge /></div>
      <p className="pf-lead">{t("platform.passport.intro")}</p>
      <p className="pf-note">{t("platform.common.demoNote")}</p>
    </header>
    {!account ? <>
      <p className="pf-note">{t("platform.passport.pickFirst")}</p>
      <Link href="/login?next=/profile" className="pf-link">{t("platform.login.submit")}</Link>
    </> : <Async r={passport}>{(data) => {
      const attempts = data.attempts.filter((a) => a.finished_at)
        .sort((a, b) => (b.finished_at ?? "").localeCompare(a.finished_at ?? ""));
      if (attempts.length === 0) {
        return <section className="pf-card"><p>{data.account.display_name_th}</p>
          <p className="pf-muted">{t("platform.passport.empty")}</p>
          <Link href="/lab" className="button-gold">{t("platform.passport.emptyCta")}<span aria-hidden="true"> →</span></Link></section>;
      }
      const counts = new Map<string, number>();
      for (const a of attempts) for (const id of new Set(a.objective_ids)) counts.set(id, (counts.get(id) ?? 0) + 1);
      return <>
        <p className="pf-meta">{data.account.display_name_th}</p>
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
          <ul className="pf-grid pf-list">{attempts.map((a) => <AttemptCard key={a.room_id} a={a} objectiveTitle={objectiveTitle} />)}</ul>
          {attempts.some((a) => a.score_total !== null) && <p className="pf-meta">{t("platform.passport.scoreNote")}</p>}
        </section>

      </>;
    }}</Async>}
  </main>;
}
