import { t } from "@/lib/i18n";

export type ValidationReport = {
  generated_at: string; source_revision: string; fingerprint: string; scope: string;
  groups: { id: string; passed: number; failed: number; errors: number; skipped: number }[];
};

export function ValidationDashboard({ report }: { report: ValidationReport }) {
  return <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
    <p className="font-bold text-brand-800">{t("validation.eyebrow")}</p>
    <h1 className="mt-2 text-3xl font-bold">{t("validation.title")}</h1>
    <p className="mt-4 max-w-3xl leading-7 text-stone-700">{t("validation.scope")}</p>
    <p className="mt-4 text-sm">{t("validation.measuredAt")} <time dateTime={report.generated_at}>{new Date(report.generated_at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}</time></p>
    <div className="mt-7 grid gap-4 sm:grid-cols-2">
      {report.groups.map((group) => {
        const failed = group.failed + group.errors;
        const status = failed ? "failed" : group.skipped || group.passed === 0 ? "unverified" : "passed";
        return <section key={group.id} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">{t(`validation.groups.${group.id}`)}</h2>
          <p className={`mt-3 font-bold ${status === "failed" ? "text-rose-900" : "text-brand-900"}`}>{t(`validation.${status}`)}</p>
          <dl className="mt-4 grid grid-cols-3 gap-3">
            {[["passed", group.passed], ["failed", failed], ["skipped", group.skipped]].map(([key, value]) => <div key={key}><dt className="text-sm text-stone-700">{t(`validation.${key}`)}</dt><dd className="mt-1 text-2xl font-bold">{value}</dd></div>)}
          </dl>
        </section>;
      })}
    </div>
    <details className="mt-6 rounded-xl border border-stone-200 bg-white p-4">
      <summary className="cursor-pointer py-2 font-bold">{t("validation.provenance")}</summary>
      <p className="mt-3 break-all">{t("validation.revision")}: {report.source_revision}</p>
      <p className="mt-2 break-all">SHA-256: {report.fingerprint}</p>
      <p className="mt-3 leading-7">{t("validation.snapshot")}</p>
    </details>
    <a href="/validation-results.json" download className="mt-6 inline-flex rounded-lg bg-brand-900 px-5 py-3 font-bold text-white">{t("validation.download")}</a>
  </main>;
}
