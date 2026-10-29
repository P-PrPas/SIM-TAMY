"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { isInstitution, setLogin } from "@/lib/demo-login";
import { useLogin } from "@/lib/use-login";
import { t } from "@/lib/i18n";

export function AccountMenu() {
  const { account, ready } = useLogin();
  const router = useRouter();
  if (!ready) return null;
  if (!account) return <Link href="/login" className="button-primary account-signin">{t("platform.login.submit")}</Link>;
  return <details className="account-menu" onKeyDown={(e) => {
    if (e.key === "Escape") { e.currentTarget.open = false; e.currentTarget.querySelector("summary")?.focus(); }
  }}>
    <summary aria-label={`${t("platform.login.accountMenu")} ${account.display_name_th}`}>
      <span className="account-avatar" aria-hidden="true"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"><circle cx="12" cy="8" r="3.5" /><path d="M5 21v-2a7 7 0 0 1 14 0v2" /></svg></span>
      <span className="account-name">{account.display_name_th}</span><svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75"><path d="m4 6 4 4 4-4" /></svg>
    </summary>
    <div className="account-popover">
      <strong>{account.display_name_th}</strong><p className="pf-meta">{t(`institution.staff.role.${account.role}`)}</p>
      <Link href={isInstitution(account) ? "/institution/staff" : "/profile"} onClick={(e) => { const menu = e.currentTarget.closest("details"); if (menu) menu.open = false; }}>{t("platform.login.viewProfile")}</Link>
      <button type="button" onClick={() => { setLogin(null); router.replace("/login"); }}>{t("platform.login.logout")}</button>
    </div>
  </details>;
}
