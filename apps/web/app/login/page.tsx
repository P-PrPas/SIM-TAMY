"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { canLogin, DEMO_PASSWORD, loginDestination, setLogin } from "@/lib/demo-login";
import { t } from "@/lib/i18n";
import { useV2 } from "@/lib/use-v2";
import { v2 } from "@/lib/v2-api";
import { Async, DemoBadge } from "@/components/platform/shared";
import { StageArt } from "@/components/platform/stages";

export default function LoginPage() {
  const router = useRouter();
  const accounts = useV2((s) => v2.accounts(s), "login-accounts");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const account = accounts.data?.items.find((a) => a.id === username.trim() && canLogin(a));
    if (!account || password !== DEMO_PASSWORD) { setError(t("platform.login.invalid")); input.current?.focus(); return; }
    setBusy(true);
    setLogin(account);
    router.replace(loginDestination(account, new URLSearchParams(window.location.search).get("next")));
  }
  return <main className="pf-page login-page">
    <section className="login-form" aria-labelledby="login-title">
      <DemoBadge />
      <h1 id="login-title">{t("platform.login.title")}</h1>
      <p className="pf-lead">{t("platform.login.intro")}</p>
      <form onSubmit={submit} className="pf-stack">
        <div><label htmlFor="username">{t("platform.login.username")}</label>
          <input ref={input} id="username" autoComplete="username" required value={username} onChange={(e) => { setUsername(e.target.value); setError(""); }} aria-invalid={Boolean(error)} aria-describedby={error ? "login-error" : undefined} /></div>
        <div><label htmlFor="password">{t("platform.login.password")}</label>
          <div className="password-field"><input id="password" type={show ? "text" : "password"} autoComplete="current-password" required value={password} onChange={(e) => { setPassword(e.target.value); setError(""); }} />
            <button type="button" onClick={() => setShow(!show)} aria-pressed={show}>{t(show ? "platform.login.hide" : "platform.login.show")}</button></div></div>
        {error && <p id="login-error" role="alert" className="pf-alert">{error}</p>}
        <button type="submit" className="button-primary" disabled={busy || accounts.loading || !accounts.data} aria-busy={busy}>{t("platform.login.submit")}</button>
      </form>
      <p className="pf-meta login-note">{t("platform.login.demoNote")}</p>
    </section>
    <aside className="login-demo" aria-labelledby="demo-login-title">
      <StageArt stage={1} />
      <div className="login-demo-body"><h2 id="demo-login-title">{t("platform.login.tryTitle")}</h2>
        <p className="pf-muted">{t("platform.login.tryText")}</p>
        <details className="demo-accounts"><summary>{t("platform.login.choose")}</summary>
          <Async r={accounts}>{({ items }) => <>
            <label htmlFor="demo-account">{t("platform.login.account")}</label>
            <select id="demo-account" value="" onChange={(e) => {
              if (!e.target.value) return;
              setUsername(e.target.value); setPassword(DEMO_PASSWORD); setError(""); input.current?.focus();
            }}><option value="">{t("platform.login.choosePlaceholder")}</option>
              {["learner", "institution"].map((group) => <optgroup key={group} label={t(`platform.login.${group}`)}>
                {items.filter((a) => canLogin(a) && (a.role === "learner") === (group === "learner")).map((a) => <option key={a.id} value={a.id}>{a.display_name_th}</option>)}
              </optgroup>)}
            </select>
            {items.filter(canLogin).length === 0 && <p className="pf-note">{t("platform.login.empty")}</p>}
          </>}</Async>
        </details>
      </div>
    </aside>
  </main>;
}
