"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { getDemoAccount, setDemoAccount } from "@/lib/demo-account";
import { t } from "@/lib/i18n";

type Account = components["schemas"]["DemoAccount"];
type Staff = Account & { org_id: string };

const StaffContext = createContext<Staff | null>(null);

/** The picked staff profile; only available below <InstitutionShell>, which gates on a pick. */
export function useStaff(): Staff {
  const staff = useContext(StaffContext);
  if (!staff) throw new Error("useStaff needs a picked staff account");
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

function isStaff(account: Account): account is Staff {
  return account.org_id !== null && ["educator", "org_admin"].includes(account.role);
}

export function InstitutionShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [staff, setStaff] = useState<Staff[]>([]);
  const [picked, setPicked] = useState("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api()
      .GET("/v1/demo/accounts")
      .then(({ data }) => {
        if (cancelled) return;
        const list = (data?.items ?? []).filter(isStaff);
        setStaff(list);
        const saved = getDemoAccount();
        setPicked(list.some((a) => a.id === saved) ? (saved ?? "") : "");
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const current = staff.find((a) => a.id === picked) ?? null;

  function pick(id: string) {
    setDemoAccount(id || null);
    setPicked(id);
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 sm:py-10">
      <header className="mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-stone-950 sm:text-3xl">{t("institution.title")}</h1>
          <DemoBadge />
        </div>
        <p className="mt-2 text-stone-700">{t("institution.demoNote")}</p>
        <div className="mt-4 max-w-md">
          <label htmlFor="staff-picker" className="block font-semibold">
            {t("institution.picker.label")}
          </label>
          <select
            id="staff-picker"
            value={picked}
            onChange={(event) => pick(event.target.value)}
            className="mt-2 min-h-11 w-full rounded-lg border border-stone-500 bg-white px-3"
          >
            <option value="">{t("institution.picker.placeholder")}</option>
            {staff.map((a) => (
              <option key={a.id} value={a.id}>
                {a.display_name_th} ({t(`institution.picker.role.${a.role}`)})
              </option>
            ))}
          </select>
        </div>
        {current && (
          <nav aria-label={t("institution.nav.label")} className="mt-5">
            <ul className="flex flex-wrap gap-2">
              {links.map(([suffix, key]) => {
                const href = `/institution${suffix}`;
                const active = suffix === "" ? path === href : path.startsWith(href);
                return (
                  <li key={key}>
                    <Link
                      href={href}
                      aria-current={active ? "page" : undefined}
                      className={`inline-flex min-h-11 items-center rounded-lg border px-4 font-semibold ${
                        active
                          ? "border-brand-900 bg-brand-900 text-white"
                          : "border-stone-500 text-stone-900 hover:bg-stone-100"
                      }`}
                    >
                      {t(`institution.nav.${key}`)}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        )}
      </header>
      {failed && (
        <p role="alert" className="rounded-lg border border-red-800 bg-red-50 p-4 text-red-950">
          {t("institution.loadError")}
        </p>
      )}
      {!failed && !current && <p>{t("institution.picker.required")}</p>}
      {current && <StaffContext.Provider value={current}>{children}</StaffContext.Provider>}
    </main>
  );
}
