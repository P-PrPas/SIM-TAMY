"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { t } from "@/lib/i18n";
import { useV2 } from "@/lib/use-v2";
import { v2, type Claim, type Lens, type Source, type UnitDetail, type UnitSummary } from "@/lib/v2-api";

import { Async, formatDate, labelOr } from "./shared";

const STAGE_ORDER = ["pregnancy", "intrapartum", "postpartum", "newborn"];

function groupByStage(items: UnitSummary[]): Array<[string, UnitSummary[]]> {
  const groups = new Map<string, UnitSummary[]>();
  for (const u of items) {
    const stage = ["preconception", "antenatal"].includes(u.care_stage) ? "pregnancy" : u.care_stage;
    groups.set(stage, [...(groups.get(stage) ?? []), u]);
  }
  const rank = (s: string) => (STAGE_ORDER.includes(s) ? STAGE_ORDER.indexOf(s) : STAGE_ORDER.length);
  return [...groups].sort((a, b) => rank(a[0]) - rank(b[0]));
}

const stageLabel = (stage: string) => labelOr(`platform.knowledge.stage_${stage}`, stage);

function ExternalLink({ url, children }: { url: string; children: ReactNode }) {
  return <a href={url} target="_blank" rel="noopener noreferrer" className="pf-link">
    {children}<span className="sr-only"> ({t("platform.common.opensNewTab")})</span><span aria-hidden="true"> ↗</span>
  </a>;
}

function SourceRegistry() {
  const sources = useV2((s) => v2.sources(s), "sources");
  return <details className="pf-section pf-disclosure">
    <summary>{t("platform.knowledge.registry")}</summary>
    <p className="pf-muted">{t("platform.knowledge.registryIntro")}</p>
    <Async r={sources}>{({ items }) => items.length === 0
      ? <p className="pf-note">{t("platform.knowledge.noSources")}</p>
      : <ul className="pf-list pf-stack">{items.map((s: Source) => <li key={s.id} className="pf-card pf-source">
        <p><strong>{s.id}</strong> · {s.title}</p>
        <p className="pf-meta">
          {labelOr(`platform.knowledge.kind_${s.kind}`, s.kind)}
          {s.publisher && <> · {t("platform.knowledge.publisher")}: {s.publisher}</>}
          {s.year !== null && <> · {t("platform.knowledge.year")}: {s.year}</>}
        </p>
        <p className="pf-meta">{t("platform.knowledge.rights")}: {labelOr(`platform.knowledge.rights_${s.rights_status}`, s.rights_status)}</p>
        {s.url && <ExternalLink url={s.url}>{t("platform.knowledge.sourceLink")}</ExternalLink>}
      </li>)}</ul>}</Async>
  </details>;
}

export function KnowledgeIndex() {
  const units = useV2((s) => v2.units(s), "units");
  return <main className="pf-page">
    <header><h1>{t("platform.knowledge.title")}</h1><p className="pf-lead">{t("platform.knowledge.intro")}</p></header>
    <Async r={units}>{({ items }) => items.length === 0
      ? <p className="pf-note">{t("platform.knowledge.noUnits")}</p>
      : <>{groupByStage(items).map(([stage, group]) => <section key={stage} className="pf-section" aria-labelledby={`stage-${stage}`}>
        <h2 id={`stage-${stage}`}>{stageLabel(stage)}</h2>
        <ul className="pf-grid pf-list">{group.map((u) => <li key={u.id} className="pf-card">
          <h3><Link href={`/knowledge/${encodeURIComponent(u.id)}`} className="pf-link">{u.title_th}</Link></h3>
          <p className="pf-meta">{u.id}{u.has_lens && <> · {t("platform.knowledge.hasLens")}</>}</p>
        </li>)}</ul>
      </section>)}</>}</Async>
    <SourceRegistry />
  </main>;
}

function ClaimCard({ c }: { c: Claim }) {
  return <li className="pf-card">
    <p className="pf-meta">{t("platform.knowledge.claimType")}: {labelOr(`platform.knowledge.type_${c.type}`, c.type)}</p>
    <p>{c.text_th}</p>
    <h4>{t("platform.knowledge.sources")}</h4>
    <ul className="pf-list">{c.sources.map((s, i) => <li key={`${s.source_id}-${i}`} className="pf-meta">
      <strong>{s.source_id}</strong> · {s.title}
      {s.locator && <> · {t("platform.knowledge.locator")}: {s.locator}</>}
      {s.url && <> · <ExternalLink url={s.url}>{t("platform.knowledge.sourceLink")}</ExternalLink></>}
    </li>)}</ul>
  </li>;
}

function WisdomLens({ lens }: { lens: Lens }) {
  return <section aria-labelledby="lens-title" className="pf-section pf-lens">
    <h2 id="lens-title">{t("platform.knowledge.lensTitle")}</h2>
    <div className="pf-grid">
      {([["lensWisdom", lens.wisdom_th], ["lensSafety", lens.safety_th], ["lensRights", lens.rights_th]] as const).map(([key, text]) =>
        <section key={key} className="pf-card"><h3>{t(`platform.knowledge.${key}`)}</h3><p>{text}</p></section>)}
    </div>
  </section>;
}

function Detail({ u }: { u: UnitDetail }) {
  return <>
    <header>
      <p className="pf-kicker">{stageLabel(u.care_stage)}</p>
      <h1>{u.title_th}</h1>
      <p className="pf-meta">{u.id} · {t("platform.knowledge.version")} {u.version} · {t("platform.knowledge.domain")} {u.domain}</p>
      <p className="pf-note">
        <strong>{t("platform.knowledge.provenance")}:</strong>{" "}
        {labelOr(`platform.knowledge.provenance_${u.review_basis}`, u.review_basis)}
        {" · "}{t("platform.knowledge.evidenceStatus")}: {labelOr(`platform.knowledge.evidence_${u.evidence_status}`, u.evidence_status)}
        {u.reviewed_on && <> · {t("platform.knowledge.updatedOn")} {formatDate(u.reviewed_on)}</>}
      </p>
    </header>
    <section aria-labelledby="claims-title" className="pf-section">
      <h2 id="claims-title">{t("platform.knowledge.claims")}</h2>
      <ul className="pf-list pf-stack">{u.claims.map((c) => <ClaimCard key={c.id} c={c} />)}</ul>
    </section>
    {u.lens && <WisdomLens lens={u.lens} />}
    {u.contraindications_th.length > 0 && <section aria-labelledby="contra-title" className="pf-section">
      <h2 id="contra-title">{t("platform.knowledge.contraindications")}</h2>
      <ul>{u.contraindications_th.map((c) => <li key={c}>{c}</li>)}</ul>
    </section>}
    {u.escalation_th && <section aria-labelledby="escalation-title" className="pf-section pf-card">
      <h2 id="escalation-title">{t("platform.knowledge.escalation")}</h2>
      <p>{u.escalation_th}</p>
    </section>}
  </>;
}

export function KnowledgeUnit({ id }: { id: string }) {
  const unit = useV2((s) => v2.unit(id, s), `unit:${id}`);
  return <main className="pf-page">
    <Link href="/knowledge" className="pf-link"><span aria-hidden="true">← </span>{t("platform.knowledge.allUnits")}</Link>
    {unit.error?.status === 404 ? <p role="alert" className="pf-alert">{t("platform.knowledge.notFound")}</p>
      : <Async r={unit}>{(u) => <Detail u={u} />}</Async>}
  </main>;
}
