"use client";

import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";
import { FamilyFacts } from "../family-cosim";
import { FamilyIcon } from "../family-art";

type View = components["schemas"]["FamilyView"];

/**
 * "What you know" inside the dialogue panel: the role-private brief plus my facts (share action) and the
 * shared timeline. A plain disclosure, never a modal, so it cannot interrupt play. Open while I still hold
 * unshared facts, collapsed otherwise. Renders nothing when there is no brief and no facts.
 */
export function PixelKnow({ view, busy, onShare }: { view: View; busy: boolean; onShare: (factId: string) => void }) {
  const mine = view.my_facts ?? [];
  const unshared = mine.filter((fact) => !fact.shared).length;
  if (!view.private_brief_th && mine.length === 0 && (view.shared_facts ?? []).length === 0) return null;
  return <details className="pixel-know" open={unshared > 0}>
    <summary>
      <FamilyIcon name="lock" /><span>{t("pixelSim.know.title")}</span>
      {unshared > 0 && <b className="pixel-know-count">{unshared}<span className="sr-only"> {t("pixelSim.know.unshared")}</span></b>}
      <span className="family-disclosure" aria-hidden="true"><FamilyIcon name="chevron" /></span>
    </summary>
    <div className="pixel-know-body">
      {view.private_brief_th && <section aria-label={t("family.private")}><h3>{t("family.private")}</h3><p>{view.private_brief_th}</p></section>}
      <FamilyFacts view={view} busy={busy} onShare={onShare} />
    </div>
  </details>;
}
