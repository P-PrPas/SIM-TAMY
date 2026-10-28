"use client";

import { t } from "@/lib/i18n";
import { pickDemoAccount, useDemoAccount } from "@/lib/use-demo-account";
import { useV2 } from "@/lib/use-v2";
import { v2 } from "@/lib/v2-api";

import { Async, DemoBadge } from "./shared";

/** Mock-account picker (ADR-15): learner profiles only, labeled as demo. */
export function ProfilePicker() {
  const current = useDemoAccount();
  const accounts = useV2((s) => v2.accounts(s), "accounts");
  return <section id="profile" className="pf-card" aria-labelledby="profile-title">
    <div className="pf-row"><h2 id="profile-title">{t("platform.profile.title")}</h2><DemoBadge /></div>
    <p className="pf-muted">{t("platform.profile.intro")}</p>
    <Async r={accounts}>{({ items }) => {
      const learners = items.filter((a) => a.role === "learner");
      if (learners.length === 0) return <p className="pf-note">{t("platform.profile.empty")}</p>;
      return <ul className="pf-list" aria-label={t("platform.profile.list")}>
        {learners.map((a) => <li key={a.id}>
          <button type="button" className="pf-profile-btn" aria-pressed={current === a.id}
            onClick={() => pickDemoAccount(a.id)}>
            <span>{a.display_name_th}</span>
            <small>{current === a.id ? t("platform.profile.current") : t("platform.profile.pick")}</small>
          </button>
        </li>)}
      </ul>;
    }}</Async>
    {current && <button type="button" className="pf-link pf-link-btn" onClick={() => pickDemoAccount(null)}>{t("platform.profile.clear")}</button>}
  </section>;
}
