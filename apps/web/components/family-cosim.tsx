"use client";

import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";
import { FamilyIcon } from "./family-art";

type View = components["schemas"]["FamilyView"];
type Scene = NonNullable<View["scene"]>;

/** Own private facts (share buttons) and the shared timeline. The partner's unshared facts never arrive. */
export function FamilyFacts({ view, busy, onShare }: { view: View; busy: boolean; onShare: (factId: string) => void }) {
  const mine = view.my_facts ?? [];
  const shared = view.shared_facts ?? [];
  if (mine.length === 0 && shared.length === 0) return null;
  return <section className="family-facts" aria-labelledby="family-facts-title">
    <h2 id="family-facts-title"><FamilyIcon name="lock" />{t("family.cosim.facts.title")}</h2>
    {mine.length > 0 && <>
      <p className="family-muted">{t("family.cosim.facts.help")}</p>
      <ul className="family-fact-list">{mine.map((fact) => <li key={fact.id}>
        <p>{fact.text_th}</p>
        {fact.shared
          ? <span className="family-fact-shared"><FamilyIcon name="check" />{t("family.cosim.facts.shared")}</span>
          : <button type="button" className="family-button-light" disabled={busy || !view.partner_joined || view.report !== null} onClick={() => onShare(fact.id)}>{t("family.cosim.facts.share")}</button>}
      </li>)}</ul>
    </>}
    <h3>{t("family.cosim.timeline.title")}</h3>
    {shared.length ? <ol className="family-timeline" aria-live="polite">{shared.map((fact) => <li key={fact.id}>
      <strong>{t(`family.${fact.role}`)}</strong><p>{fact.text_th}</p>
    </li>)}</ol> : <p className="family-muted">{t("family.cosim.timeline.empty")}</p>}
  </section>;
}

/** Joint-step state: nothing about the partner until both have voted, then both choices side by side. */
export function FamilyVoteStatus({ scene }: { scene: Scene }) {
  const vote = scene.vote;
  if (!scene.joint || !vote) return null;
  return <div className="family-vote" role="status">
    <p><strong>{t("family.cosim.joint.title")}</strong> {t("family.cosim.joint.help")}</p>
    {vote.waiting_for_partner && <p className="family-vote-waiting">{t("family.cosim.joint.waiting")}</p>}
    {vote.disagreement && <div role="alert" className="family-vote-split">
      <p><strong>{t("family.cosim.joint.needAgree")}</strong></p>
      <ul>{vote.disagreement.map((item) => <li key={item.role}><strong>{t(`family.${item.role}`)}</strong><p>{item.text_th}</p></li>)}</ul>
    </div>}
  </div>;
}

/** Expandable tradition card: separates the cultural practice from its evidence status. */
export function FamilyKnowledgeCard({ card }: { card: NonNullable<Scene["card"]> }) {
  return <details className={`family-card family-card-${card.evidence_status}`}>
    <summary><FamilyIcon name="book" /><span>{t("family.cosim.card.title")}</span><span className="family-disclosure" aria-hidden="true"><FamilyIcon name="chevron" /></span></summary>
    {card.lens && <section className="family-lens" aria-label={t("lab.lens.title")}>
      <h3>{t("lab.lens.title")}</h3>
      <div><h4>{t("lab.lens.wisdom")}</h4><p>{card.lens.wisdom_th}</p></div>
      <div><h4>{t("lab.lens.safety")}</h4><p>{card.lens.safety_th}</p></div>
      <div><h4>{t("lab.lens.rights")}</h4><p>{card.lens.rights_th}</p></div>
    </section>}
    <dl>
      <dt>{t("family.cosim.card.tradition")}</dt><dd>{card.tradition_th}</dd>
      <dt>{t("family.cosim.card.evidence")}</dt><dd><span className="family-card-status">{t(`family.cosim.card.status.${card.evidence_status}`)}</span></dd>
      <dt>{t("family.cosim.card.learning")}</dt><dd>{card.learning_point_th}</dd>
      {card.precautions_th.length > 0 && <><dt>{t("family.cosim.card.precautions")}</dt>
        <dd><ul>{card.precautions_th.map((item) => <li key={item}>{item}</li>)}</ul></dd></>}
      {card.when_to_consult_th && <><dt>{t("family.cosim.card.consult")}</dt><dd>{card.when_to_consult_th}</dd></>}
      <dt>{t("family.cosim.card.sources")}</dt>
      <dd><ul>{card.sources.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{source.title_th}</a></li>)}</ul></dd>
    </dl>
  </details>;
}
