"use client";

import { createContext, useContext, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import type { components } from "@/lib/api/schema";
import { isInstitution } from "@/lib/demo-login";
import { useLogin } from "@/lib/use-login";
import { t } from "@/lib/i18n";

type Account = components["schemas"]["DemoAccount"];
type Staff = Account & { org_id: string };

const StaffContext = createContext<Staff | null>(null);

/** The institution account from demo login; only available below its workspace shell. */
export function useStaff(): Staff {
  const staff = useContext(StaffContext);
  if (!staff) throw new Error("useStaff needs an institution login");
  return staff;
}

export function DemoBadge() {
  return (
    <span className="inline-flex min-h-8 items-center rounded-full border border-amber-800 bg-amber-100 px-3 text-sm font-semibold text-amber-950">
      {t("institution.demoLabel")}
    </span>
  );
}

const links = [
  ["", "overview"],
  ["/cohorts", "cohorts"],
  ["/analytics", "analytics"],
  ["/library", "library"],
  ["/staff", "staff"],
] as const;

export function InstitutionShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const { account } = useLogin();
  const current = account && isInstitution(account) ? account : null;

  return (
    <main className="pf-page institution-workspace">
      <header className="mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-stone-950 sm:text-3xl">{t("institution.title")}</h1>
          <DemoBadge />
        </div>
        <p className="mt-2 text-stone-700">{t("institution.demoNote")}</p>
      </header>
      {current ? <StaffContext.Provider value={current}>
        <aside className="institution-sidebar"><p className="pf-meta">{current.display_name_th}</p>
          <nav aria-label={t("institution.nav.label")}>
            <ul className="pf-list">
              {links.map(([suffix, key]) => {
                const href = `/institution${suffix}`;
                const active = suffix === "" ? path === href : path.startsWith(href);
                return (
                  <li key={key}>
                    <Link
                      href={href}
                      aria-current={active ? "page" : undefined}
                    >
                      {t(`institution.nav.${key}`)}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </aside>
        <div className="institution-content" key={current.id}>{children}</div>
      </StaffContext.Provider> : <div className="pf-card"><p>{t("platform.login.staffRequired")}</p><Link href="/login" className="pf-link">{t("platform.login.submit")}</Link></div>}
    </main>
  );
}
