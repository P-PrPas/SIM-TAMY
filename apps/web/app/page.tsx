import { t } from "@/lib/i18n";

export default function Home() {
  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-bold">{t("app.title")}</h1>
      <p className="mt-2">{t("home.scaffold")}</p>
    </main>
  );
}
