"use client";

import { useEffect, useState } from "react";

import { createApi } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";

type Report = components["schemas"]["FamilyReport"];
type Debrief = components["schemas"]["DebriefOutput"];
const DIMENSIONS = new Set(["discovery", "decision", "communication", "evidence_scope"]);

/** Dimension scores (finished report only) with the safety gate kept separate, then the AI-03 debrief. */
export function FamilyLabReport({ report, roomId, token }: { report: Report; roomId: string; token: string }) {
  const [debrief, setDebrief] = useState<Debrief | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void createApi({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000", getToken: () => token })
      .POST("/v1/family/rooms/{room_id}/debrief", { params: { path: { room_id: roomId } }, signal: controller.signal })
      .then(({ data }) => { if (data && !controller.signal.aborted) { setDebrief(data); setFailed(false); } })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [roomId, token, attempt]);

  const dimensions = report.dimensions ?? [];
  return <section className="family-lab-report" aria-labelledby="lab-dimensions-title">
    <h2 id="lab-dimensions-title">{t("lab.report.dimensions")}</h2>
    <p className="family-report-note">{t("lab.report.dimensionNote")}</p>
    {report.score_total != null && <p className="family-lab-total"><span>{t("lab.report.total")}</span> <strong>{report.score_total}</strong> {t("lab.report.outOf")}</p>}
    <ul className="family-dimensions">{dimensions.map((d) => <li key={d.id}>
      <span>{DIMENSIONS.has(d.id) ? t(`lab.report.dim.${d.id}`) : d.id}</span>
      <progress value={d.score} max={100} aria-label={DIMENSIONS.has(d.id) ? t(`lab.report.dim.${d.id}`) : d.id} />
      <small>{d.earned} / {d.possible} · {t("lab.report.weight")} {d.weight}</small>
    </li>)}</ul>
    <section className="family-debrief" aria-labelledby="lab-debrief-title" aria-live="polite">
      <h3 id="lab-debrief-title">{t("lab.debrief.title")}</h3>
      {!debrief && !failed && <p role="status">{t("lab.debrief.loading")}</p>}
      {failed && <div role="alert"><p>{t("lab.debrief.error")}</p><button type="button" className="family-button-light" onClick={() => setAttempt((n) => n + 1)}>{t("lab.debrief.retry")}</button></div>}
      {debrief && <>
        {debrief.fallback_used && <p className="family-muted">{t("lab.debrief.fallback")}</p>}
        {([["strengths", debrief.strengths ?? []], ["improvements", debrief.improvements ?? []]] as const).map(([kind, points]) => points.length > 0 && <div key={kind}>
          <h4>{t(`lab.debrief.${kind}`)}</h4>
          <ul>{points.map((p, i) => <li key={`${kind}-${i}`}>{p.text}</li>)}</ul>
        </div>)}
        {(debrief.recommended_asset_ids ?? []).length > 0 && <p className="family-muted">{t("lab.debrief.assets")}: {debrief.recommended_asset_ids?.join(", ")}</p>}
      </>}
    </section>
  </section>;
}
