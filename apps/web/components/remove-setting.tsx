"use client";

import { useId, useState } from "react";
import { t } from "@/lib/i18n";

export function RemoveSetting({ name, remove, onRemoved }: { name: string; remove: () => Promise<unknown>; onRemoved: () => void }) {
  const id = useId();
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  async function submit() {
    setBusy(true); setError(false);
    try { await remove(); setConfirm(false); onRemoved(); }
    catch { setError(true); }
    finally { setBusy(false); }
  }
  return <div>
    <button type="button" className="delete-button" aria-expanded={confirm} aria-controls={id} aria-label={`${t("institution.manage.remove")} ${name}`} onClick={() => setConfirm(!confirm)} disabled={busy}>{t("institution.manage.remove")}</button>
    {confirm && <div id={id} className="delete-confirm">
      <p>{t("institution.manage.confirm")} <strong>{name}</strong></p><p className="pf-meta">{t("institution.manage.keepHistory")}</p>
      <div className="pf-actions"><button type="button" className="delete-button" disabled={busy} onClick={() => void submit()}>{t("institution.manage.confirmButton")}</button>
        <button type="button" className="button-secondary" disabled={busy} onClick={() => setConfirm(false)}>{t("institution.manage.cancel")}</button></div>
      {error && <p role="alert" className="pf-alert">{t("institution.actionError")}</p>}
    </div>}
  </div>;
}
