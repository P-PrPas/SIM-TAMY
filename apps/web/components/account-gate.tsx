"use client";

import { Fragment, useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isInstitution, syncLearningSession } from "@/lib/demo-login";
import { useLogin } from "@/lib/use-login";
import { t } from "@/lib/i18n";

export function AccountGate({ children }: { children: ReactNode }) {
  const { account, ready } = useLogin();
  const path = usePathname();
  const router = useRouter();
  const publicPage = ["/", "/login", "/validation"].includes(path);
  const staffPage = path === "/institution" || path.startsWith("/institution/");
  const target = !ready ? null : account && isInstitution(account)
    ? (staffPage || path === "/login" ? null : "/institution")
    : staffPage ? (account ? "/profile" : "/login")
    : !account && !publicPage ? `/login?next=${encodeURIComponent(path + (typeof window === "undefined" ? "" : window.location.search))}` : null;
  useEffect(() => {
    if (!ready) return;
    syncLearningSession(account?.id ?? null);
    if (target) router.replace(target);
  }, [ready, account?.id, router, target]);
  if (target || !ready) return <main className="pf-page"><p role="status">{t("platform.common.loading")}</p></main>;
  return <Fragment key={account?.id ?? "guest"}>{children}</Fragment>;
}
