"use client";

import { useState } from "react";
import type { components } from "@/lib/api/schema";
import { parentProfile } from "@/lib/parent-profile";
import { t } from "@/lib/i18n";
import { FamilyIcon } from "./family-art";

const icons = { communication: "chat", responsibility: "journey", safety: "shield", support: "heart", balanced: "bridge", explorer: "leaf" };

export function ParentProfileCard({ report, coop }: { report: components["schemas"]["FamilyReport"]; coop: boolean }) {
  const type = parentProfile(report.competencies);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "manual">("idle");
  const shared = [t("app.title"), t(coop ? "profiles.team" : "profiles.personal"), t(`profiles.${type}.title`), t(`profiles.${type}.description`), t("profiles.scope"), ...(report.safety_status === "SAFETY_NOT_MET" ? [t("family.safetyReview")] : [])].join("\n");
  async function copy() {
    try { await navigator.clipboard.writeText(shared); setCopyState("copied"); }
    catch { setCopyState("manual"); }
  }
  return <section className={`parent-profile profile-${type}`} aria-labelledby="parent-profile-title">
    <div className="parent-profile-seal" aria-hidden="true"><span /><FamilyIcon name={icons[type]} /><span /></div>
    <div className="parent-profile-copy">
      <p className="parent-profile-eyebrow">{t(coop ? "profiles.team" : "profiles.personal")}</p>
      <h3 id="parent-profile-title">{t(`profiles.${type}.title`)}</h3>
      <p>{t(`profiles.${type}.description`)}</p><p className="parent-profile-scope">{t("profiles.scope")}</p>
      <details><summary>{t("profiles.method")}</summary><p>{t("profiles.methodHelp")}</p>
        <ul>{report.competencies.map((item) => <li key={item.skill}><span>{t(`family.skills.${item.skill}`)}</span><strong>{item.observed} / {item.opportunities}</strong><span>{t(item.opportunities ? "family.observed" : "family.noOpportunity")}</span></li>)}</ul>
        <p>{t(type === "balanced" ? "profiles.tie" : type === "explorer" ? "profiles.noSignal" : "profiles.leading")}</p>
      </details>
      <button type="button" onClick={() => void copy()}><FamilyIcon name={copyState === "copied" ? "check" : "copy"} />{t("profiles.copy")}</button>
      <p role="status">{copyState === "copied" ? t("profiles.copied") : copyState === "manual" ? t("profiles.manual") : ""}</p>
      {copyState === "manual" && <textarea aria-label={t("profiles.copyText")} readOnly value={shared} onFocus={(event) => event.target.select()} />}
    </div>
  </section>;
}
