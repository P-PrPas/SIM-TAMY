import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";
import { FamilyIcon } from "./family-art";

type Report = components["schemas"]["FamilyReport"];
const icons = { communication: "chat", responsibility: "family", safety: "shield", support: "heart" };

export function FamilyReportPanel({ report }: { report: Report }) {
  const needsReview = report.safety_status === "SAFETY_NOT_MET";
  return <section className="family-report" aria-labelledby="family-report-title">
    <header className="family-report-heading">
      <span className="family-symbol"><FamilyIcon name="book" /></span>
      <div><p className="family-kicker">{t("family.design.reflect")}</p><h2 id="family-report-title">{t("family.report")}</h2></div>
    </header>
    <div className={`family-safety ${needsReview ? "needs-review" : ""}`}>
      <FamilyIcon name={needsReview ? "shield" : "check"} />
      <p>{t(needsReview ? "family.safetyReview" : "family.safetyObserved")}</p>
    </div>
    <p className="family-report-note">{t("family.reportNote")}</p>
    <div className="family-competencies">{report.competencies.map((item) => <article key={item.skill}>
      <FamilyIcon name={icons[item.skill]} /><h3>{t(`family.skills.${item.skill}`)}</h3>
      {item.opportunities ? <>
        <p><strong>{item.observed}</strong><span> / {item.opportunities} {t("family.observed")}</span></p>
        <progress value={item.observed} max={item.opportunities} aria-label={t(`family.skills.${item.skill}`)} />
      </> : <p className="family-muted">{t("family.noOpportunity")}</p>}
    </article>)}</div>
    <div className="family-report-body">
      <section aria-labelledby="family-evidence-title"><h3 id="family-evidence-title">{t("family.design.evidence")}</h3>
        <ol className="family-evidence">{report.evidence.map((item) => <li key={item.idx}>
          <span className="family-evidence-number" aria-hidden="true">{item.idx}</span>
          <div><blockquote>“{item.text_th}”</blockquote><p>{item.feedback_th}</p>
            <div className="family-evidence-links">{item.source_ids.map((id) => <a key={id} href={`#source-${id}`}><FamilyIcon name="book" />{report.sources.find((source) => source.id === id)?.title_th}</a>)}</div>
          </div>
        </li>)}</ol>
      </section>
      <section className="family-sources" aria-labelledby="family-sources-title"><h3 id="family-sources-title">{t("family.sources")}</h3>
        <ul>{report.sources.map((source) => <li key={source.id} id={`source-${source.id}`}>
          <span className="family-source-category">{t(`family.categories.${source.category}`)}</span>
          <a href={source.url} target="_blank" rel="noreferrer">{source.title_th}<FamilyIcon name="arrow" /></a>
          <p>{source.summary_th}</p>
        </li>)}</ul>
      </section>
    </div>
  </section>;
}
