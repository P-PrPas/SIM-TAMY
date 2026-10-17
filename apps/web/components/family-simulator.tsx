"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

import { createApi, ApiError } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";

type View = components["schemas"]["FamilyView"];
type Role = View["role"];
type Credentials = { room_id: string; token: string; invite?: string };
type Decision = components["schemas"]["FamilyDecision"];

export function FamilySimulator({ storyId }: { storyId: string }) {
  const storageKey = `sim-tamy-family:${storyId}`;
  const [credentials, setCredentials] = useState<Credentials | null>(null);
  const [view, setView] = useState<View | null>(null);
  const [role, setRole] = useState<Role>("mother");
  const [invitation, setInvitation] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<Decision | null>(null);
  const [card, setCard] = useState<components["schemas"]["FamilyStoryCard"] | null>(null);
  const requestInFlight = useRef(false);
  const inviteLink = ready && credentials?.invite
    ? `${window.location.origin}${window.location.pathname}#room=${credentials.room_id}&invite=${credentials.invite}` : "";
  const client = (saved = credentials) => createApi({
    baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    getToken: () => saved?.token,
  });
  function message(cause: unknown) {
    setError(t(cause instanceof ApiError && cause.code === "UNAUTHORIZED" ? "family.unauthorized"
      : cause instanceof ApiError && cause.code === "SESSION_EXPIRED" ? "family.expired" : "family.error"));
  }
  function remember(saved: Credentials) {
    sessionStorage.setItem(storageKey, JSON.stringify(saved));
    setCredentials(saved);
  }

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      if (controller.signal.aborted) return;
      try {
        const saved = JSON.parse(sessionStorage.getItem(storageKey) ?? "null") as Credentials | null;
        if (saved?.room_id && saved.token) setCredentials(saved);
        if (window.location.hash) setInvitation(window.location.href);
      } catch { sessionStorage.removeItem(storageKey); }
      setReady(true);
    });
    void createApi({ baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" })
      .GET("/v1/family/stories", { signal: controller.signal })
      .then(({ data }) => setCard(data?.find((s) => s.id === storyId) ?? null))
      .catch((cause: unknown) => { if (!controller.signal.aborted) message(cause); });
    return () => controller.abort();
  }, [storageKey, storyId]);

  useEffect(() => {
    if (!credentials) return;
    const saved = credentials;
    const controller = new AbortController();
    let loading = false;
    async function refresh() {
      if (loading || requestInFlight.current) return;
      loading = true;
      try {
        const { data } = await createApi({
          baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000", getToken: () => saved.token,
        }).GET("/v1/family/rooms/{room_id}", { params: { path: { room_id: saved.room_id } }, signal: controller.signal });
        if (data && !controller.signal.aborted) setView((prior) => !prior || data.state_version >= prior.state_version ? data : prior);
      } catch (cause) { if (!controller.signal.aborted) message(cause); }
      finally { loading = false; }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [credentials]);

  async function start(join: boolean) {
    setBusy(true); setError("");
    try {
      if (join) {
        const params = new URLSearchParams(new URL(invitation).hash.slice(1));
        const room_id = params.get("room") ?? "";
        const tokenKey = `${storageKey}:join-token`;
        const token = sessionStorage.getItem(tokenKey) ?? crypto.randomUUID();
        sessionStorage.setItem(tokenKey, token);
        const { data } = await client(null).POST("/v1/family/rooms/{room_id}/join", {
          params: { path: { room_id } }, body: { invite: params.get("invite") ?? "", participant_token: token },
        });
        if (!data || data.story_id !== storyId) throw new Error("Wrong story invitation");
        remember({ room_id, token }); setView(data);
        window.history.replaceState(null, "", window.location.pathname);
      } else {
        const { data } = await client(null).POST("/v1/family/rooms", { body: { story_id: storyId, role } });
        if (!data) throw new Error("Missing room");
        remember(data);
      }
    } catch (cause) { message(cause); } finally { setBusy(false); }
  }

  async function decide(choiceId: string) {
    if (!view || !credentials || requestInFlight.current) return;
    const body = pending ?? { choice_id: choiceId, state_version: view.state_version, client_turn_id: crypto.randomUUID() };
    setPending(body); setBusy(true); setError(""); requestInFlight.current = true;
    try {
      const { data } = await client().POST("/v1/family/rooms/{room_id}/decisions", {
        params: { path: { room_id: credentials.room_id } }, body,
      });
      if (!data) throw new Error("Missing updated room");
      setView(data); setPending(null);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status < 500 && cause.code !== "NETWORK_ERROR") setPending(null);
      message(cause);
    } finally { setBusy(false); requestInFlight.current = false; }
  }

  function leave() {
    sessionStorage.removeItem(storageKey); sessionStorage.removeItem(`${storageKey}:join-token`);
    setCredentials(null); setView(null); setPending(null); setError("");
  }

  return <main className="mx-auto max-w-5xl px-4 py-10 sm:px-8">
    <Link href="/" className="button-text">← {t("family.home")}</Link>
    <p className="eyebrow mt-8">{t("family.eyebrow")}</p>
    <h1 className="mt-3 text-3xl font-bold sm:text-5xl">{card?.title_th ?? t("family.title")}</h1>
    <p className="mt-4 max-w-2xl text-lg leading-relaxed text-stone-600">{card?.description_th ?? t("family.description")}</p>
    <nav aria-label={t("family.courses")} className="my-6 flex flex-wrap gap-3">
      <Link href="/family" className="button-text" aria-current={storyId === "first-night" ? "page" : undefined}>{t("family.link")}</Link>
      <Link href="/parenthood" className="button-text" aria-current={storyId === "parenthood" ? "page" : undefined}>{t("family.journey")}</Link>
    </nav>
    {card && card.chapters_th.length > 1 && <ol aria-label={t("family.chapters")} className="my-6 grid gap-3 sm:grid-cols-3">
      {card.chapters_th.map((chapter) => <li key={chapter} aria-current={view?.scene?.chapter_th === chapter ? "step" : undefined} className={`rounded-2xl border p-4 ${view?.scene?.chapter_th === chapter ? "border-amber-600 bg-amber-50 font-semibold" : "border-stone-300"}`}>{chapter}</li>)}
    </ol>}
    {error && <div role="alert" className="my-5 rounded-xl border border-amber-600 bg-amber-50 p-4">{error}</div>}
    {!ready ? <p role="status">{t("family.loading")}</p> : !credentials ? <div className="mt-8 grid gap-6 md:grid-cols-2">
      <section className="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-bold">{t(card?.mode === "solo" ? "family.startSolo" : "family.create")}</h2>
        <label htmlFor="family-role" className="mb-2 mt-5 block">{t("family.role")}</label>
        <select id="family-role" className="w-full rounded-xl border border-stone-400 bg-white p-3" value={role} onChange={(e) => setRole(e.target.value as Role)}>
          <option value="mother">{t("family.mother")}</option><option value="father">{t("family.father")}</option>
        </select>
        <button disabled={busy || !card} onClick={() => void start(false)} className="button-primary mt-5 w-full">{busy ? t("family.loading") : t(card?.mode === "solo" ? "family.startSolo" : "family.create")}</button>
      </section>
      {card?.mode !== "solo" && <section className="rounded-3xl border border-stone-200 bg-amber-50 p-6">
        <h2 className="text-xl font-bold">{t("family.join")}</h2>
        <label htmlFor="family-invite" className="mb-2 mt-5 block">{t("family.invitation")}</label>
        <input id="family-invite" type="url" value={invitation} onChange={(e) => setInvitation(e.target.value)} className="w-full rounded-xl border border-stone-400 bg-white p-3" />
        <button disabled={busy || !invitation} onClick={() => void start(true)} className="button-primary mt-5 w-full">{t("family.join")}</button>
      </section>}
    </div> : !view ? <div className="mt-8"><p role="status">{t("family.loading")}</p><button onClick={leave} className="button-text mt-4">{t("family.leave")}</button></div> : <>
      <div className="my-7 flex flex-wrap items-center justify-between gap-4">
        <span className="rounded-full bg-amber-100 px-4 py-2 font-semibold">{t(`family.${view.role}`)}</span>
        <span>{view.state_version} / {view.total_steps} {t("family.decisions")}</span>
        <button onClick={leave} disabled={busy} className="button-text">{t("family.leave")}</button>
      </div>
      <aside className="mb-6 rounded-2xl border border-amber-300 bg-amber-50 p-5"><h2 className="font-bold">{t("family.private")}</h2><p className="mt-2 leading-relaxed">{view.private_brief_th}</p></aside>
      {!view.partner_joined && <section className="mb-6 rounded-2xl border border-stone-300 bg-white p-5">
        <h2 className="font-bold">{t("family.waitPartner")}</h2><p className="my-3">{t("family.shareHelp")}</p>
        <label htmlFor="family-share" className="sr-only">{t("family.invitation")}</label>
        <input id="family-share" readOnly value={inviteLink} onFocus={(e) => e.target.select()} className="w-full rounded-xl border border-stone-400 p-3" />
      </section>}
      <section role="log" aria-live="polite" aria-relevant="additions" aria-label={t("family.conversation")} className="space-y-4">
        {view.transcript.map((turn) => <article key={turn.idx} className="rounded-2xl border border-stone-200 bg-white p-5">
          <p className="font-semibold">{turn.speaker_th}</p><p className="mt-2">{turn.prompt_th}</p>
          <p className="mb-2 mt-4 font-semibold text-brand-800">{t(`family.${turn.role}`)}</p><p>{turn.text_th}</p>
          <p className="mt-4 rounded-xl bg-stone-100 p-4">{turn.reply_th}</p>
        </article>)}
        {pending && <p role="status" className="rounded-xl bg-amber-50 p-4">{view.scene?.choices.find((c) => c.id === pending.choice_id)?.text_th}<br />{t("family.sending")}</p>}
      </section>
      <div aria-live="polite" aria-atomic="true" className="my-5">{view.report ? t("family.finished") : !view.partner_joined ? t("family.waitPartner") : view.scene?.role === view.role ? t("family.yourTurn") : t("family.partnerTurn")}</div>
      {view.scene && <section className="rounded-3xl border border-stone-300 bg-white p-6 shadow-sm">
        <p className="eyebrow">{view.scene.chapter_th}</p><h2 className="mt-3 font-bold">{view.scene.speaker_th}</h2><p className="mt-3 text-lg leading-relaxed">{view.scene.prompt_th}</p>
        <div className="mt-5 grid gap-3">{view.scene.choices.map((choice) => <button key={choice.id} disabled={busy || !view.partner_joined || !!pending} onClick={() => void decide(choice.id)} className="rounded-2xl border border-stone-400 p-4 text-left leading-relaxed transition-colors hover:bg-amber-50 disabled:opacity-60">{choice.text_th}</button>)}</div>
        {pending && !busy && <button className="button-primary mt-4" onClick={() => void decide(pending.choice_id)}>{t("family.retry")}</button>}
      </section>}
      {view.report && <section className="mt-8 rounded-3xl border border-stone-300 bg-white p-6">
        <h2 className="text-2xl font-bold">{t("family.report")}</h2><p className="my-4">{t(view.report.safety_status === "SAFETY_NOT_MET" ? "family.safetyReview" : "family.safetyObserved")}</p>
        <p className="mb-5 text-stone-600">{t("family.reportNote")}</p>
        <div className="grid gap-3 sm:grid-cols-2">{view.report.competencies.map((item) => <div key={item.skill} className="rounded-xl bg-amber-50 p-4"><h3 className="font-semibold">{t(`family.skills.${item.skill}`)}</h3><p className="mt-2">{item.observed} / {item.opportunities} {t("family.observed")}</p></div>)}</div>
        <ol className="my-6 space-y-4">{view.report.evidence.map((item) => <li key={item.idx} className="border-b border-stone-200 pb-4"><blockquote className="font-semibold">“{item.text_th}”</blockquote><p className="my-2">{item.feedback_th}</p>{item.source_ids.map((id) => <a className="mr-4 underline" key={id} href={`#source-${id}`}>{view.report?.sources.find((source) => source.id === id)?.title_th}</a>)}</li>)}</ol>
        <h3 className="text-xl font-bold">{t("family.sources")}</h3><ul className="mt-4 space-y-4">{view.report.sources.map((source) => <li key={source.id} id={`source-${source.id}`} className="scroll-mt-24"><p className="text-sm font-semibold">{t(`family.categories.${source.category}`)}</p><a href={source.url} target="_blank" rel="noreferrer" className="underline">{source.title_th}</a><p className="mt-2">{source.summary_th}</p></li>)}</ul>
      </section>}
    </>}
  </main>;
}
