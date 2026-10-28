import Link from "next/link";
import type { ReactNode } from "react";

import { t } from "@/lib/i18n";
import { storyReady } from "@/lib/learning-path";

/** Small label next to a greyed-out item. Availability status only; it says nothing about the content's review. */
export const NotReadyTag = () => <span className="pf-notready">{t("platform.notReady")}</span>;

/** A greyed-out, non-interactive stand-in for a link. */
export const Disabled = ({ children }: { children: ReactNode }) =>
  <span className="pf-disabled" aria-disabled="true">{children} <NotReadyTag /></span>;

/** Shown instead of a page opened by direct URL while its content is not ready. */
export function NotReadyPage() {
  return <main className="pf-page">
    <header><h1>{t("platform.notReadyTitle")}</h1><p className="pf-lead">{t("platform.notReadyBody")}</p></header>
    <Link href="/learn" className="button-primary">{t("platform.notReadyBack")}<span aria-hidden="true"> →</span></Link>
  </main>;
}

/** Wraps a story page: renders it only when the story is ready. */
export const StoryGate = ({ id, children }: { id: string; children: ReactNode }) =>
  storyReady(id) ? <>{children}</> : <NotReadyPage />;
