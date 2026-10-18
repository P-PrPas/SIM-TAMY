"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";

import { createApi, ApiError } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";
import { FamilyArtwork, FamilyIcon } from "./family-art";
import { FamilyReportPanel } from "./family-report";

type View = components["schemas"]["FamilyView"];
type Role = View["role"];
type Credentials = { room_id: string; token: string; invite?: string };
type Decision = components["schemas"]["FamilyDecision"];

function newClientId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  // getRandomValues remains available on HTTP LAN demos; never use Math.random for tokens.
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function FamilySimulator({ storyId, children }: { storyId: string; children?: ReactNode }) {
  const storageKey = `sim-tamy-family:${storyId}`;
  const [credentials, setCredentials] = useState<Credentials | null>(null);
  const [view, setView] = useState<View | null>(null);
  const [role, setRole] = useState<Role>("mother");
  const [invitation, setInvitation] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<Decision | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const [card, setCard] = useState<components["schemas"]["FamilyStoryCard"] | null>(null);
  const requestInFlight = useRef(false);
  const completed = Boolean(view?.report);
  const inviteLink = ready && credentials?.invite
    ? `${window.location.origin}${window.location.pathname}${window.location.search}#room=${credentials.room_id}&invite=${credentials.invite}` : "";
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
    if (!credentials || completed) return;
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
  }, [credentials, completed]);

  async function start(join: boolean) {
    setBusy(true); setError("");
    try {
      if (join) {
        const params = new URLSearchParams(new URL(invitation).hash.slice(1));
        const room_id = params.get("room") ?? "";
        const tokenKey = `${storageKey}:join-token`;
        const token = sessionStorage.getItem(tokenKey) ?? newClientId();
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
    const body = pending ?? { choice_id: choiceId, state_version: view.state_version, client_turn_id: newClientId() };
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
    setCopied(false); setCopyFailed(false);
  }

  async function copyInvitation() {
    try { await navigator.clipboard.writeText(inviteLink); setCopied(true); setCopyFailed(false); }
    catch { setCopyFailed(true); }
  }

  const experience = storyId === "first-night" ? "coop" : storyId === "parenthood" ? "journey" : "bridge";
  const lastTurn = view?.transcript.at(-1);
  const earlierTurns = view?.transcript.slice(0, -1) ?? [];
  const waiting = view && (!view.partner_joined || view.scene?.role !== view.role);

  return <main className={`family-page ${view ? "is-active" : ""}`}>
    <Link href="/" className="family-back"><span aria-hidden="true">←</span>{t("family.home")}</Link>
    <nav aria-label={t("family.courses")} className="family-course-nav">
      {([['first-night', '/family', 'family', 'link'], ['parenthood', '/parenthood', 'journey', 'journey'], ['bridge', '/bridge', 'bridge', 'bridge']] as const).map(([id, href, icon, label]) => <Link key={id} href={href} aria-current={(storyId === id || (id === 'bridge' && experience === 'bridge')) ? "page" : undefined}>
        <FamilyIcon name={icon} /><span>{t(`family.design.nav.${label}`)}</span>
      </Link>)}
    </nav>
    <header className="family-hero">
      <div className="family-hero-copy">
        <p className="family-kicker">{t(`family.design.${experience}.kicker`)}</p>
        <h1>{card?.title_th ?? t(`family.design.${experience}.title`)}</h1>
        <p className="family-description">{card?.description_th ?? t("family.description")}</p>
        {!view && <><div className="family-meta"><span><FamilyIcon name={experience === 'bridge' ? 'leaf' : 'family'} />{t(`family.design.${experience}.format`)}</span><span><FamilyIcon name="heart" />{t("family.design.noCompetition")}</span></div>
          <a href="#family-enrollment" className="button-primary family-hero-cta">{t("family.design.begin")}<FamilyIcon name="arrow" /></a>
        </>}
      </div>
      {!view && <div className="family-hero-art"><FamilyArtwork grandmother={experience === 'bridge'} /><p>{t(`family.design.${experience}.caption`)}</p></div>}
    </header>
    {children}
    {experience === "journey" && card && card.chapters_th.length > 1 && <ol aria-label={t("family.chapters")} className="family-chapters">
      {card.chapters_th.map((chapter, index) => <li key={chapter} aria-current={view?.scene?.chapter_th === chapter ? "step" : undefined}>
        <span aria-hidden="true">{index + 1}</span><p>{chapter}</p>
      </li>)}
    </ol>}
    {error && <div role="alert" className="family-error"><FamilyIcon name="shield" /><p>{error}</p></div>}
    {!ready ? <p role="status" className="family-loading">{t("family.loading")}</p> : !credentials ? <div id="family-enrollment" className="family-enrollment">
      <form onSubmit={(event) => { event.preventDefault(); void start(false); }} className="family-start-panel">
        <span className="family-symbol"><FamilyIcon name={experience === 'bridge' ? 'bridge' : 'family'} /></span>
        <h2>{t(card?.mode === "solo" ? "family.startSolo" : "family.create")}</h2>
        <p className="family-muted">{t(`family.design.${experience}.startHelp`)}</p>
        <fieldset className="family-role-picker"><legend>{t("family.role")}</legend>
          {(["mother", "father"] as const).map((item) => <label key={item} className={role === item ? "is-selected" : ""}>
            <input type="radio" name="family-role" value={item} checked={role === item} onChange={() => setRole(item)} />
            <span className="family-role-avatar" aria-hidden="true">{t(`family.design.${item}Initial`)}</span>
            <span><strong>{t(`family.${item}`)}</strong><small>{t(`family.design.${item}Help`)}</small></span>
          </label>)}
        </fieldset>
        <button disabled={busy || !card} className="button-primary family-start-button" type="submit">{busy ? t("family.loading") : t(card?.mode === "solo" ? "family.startSolo" : "family.create")}<FamilyIcon name="arrow" /></button>
        <p className="family-start-note"><FamilyIcon name="book" />{t("family.design.chooseAndReflect")}</p>
      </form>
      {card?.mode !== "solo" ? <form onSubmit={(event) => { event.preventDefault(); void start(true); }} className="family-join-panel">
        <FamilyIcon name="chat" /><h2>{t("family.join")}</h2><p>{t("family.design.joinHelp")}</p>
        <label htmlFor="family-invite">{t("family.invitation")}</label>
        <input id="family-invite" type="url" required value={invitation} onChange={(event) => setInvitation(event.target.value)} placeholder={t("family.design.invitePlaceholder")} />
        <button disabled={busy || !invitation} type="submit" className="family-button-light">{busy ? t("family.loading") : t("family.join")}<FamilyIcon name="arrow" /></button>
        <p className="family-join-note"><FamilyIcon name="lock" />{t("family.design.twoDevices")}</p>
      </form> : <aside className="family-learning-note">
        <FamilyIcon name={experience === 'bridge' ? 'leaf' : 'journey'} /><h2>{t("family.design.learnTitle")}</h2>
        <ul>{["listen", "decide", "reflect"].map((item) => <li key={item}><FamilyIcon name="check" /><span>{t(`family.design.learn.${item}`)}</span></li>)}</ul>
        <p>{t("family.design.yourPace")}</p>
      </aside>}
    </div> : !view ? <div className="family-loading"><p role="status">{t("family.loading")}</p><button onClick={leave} className="button-text">{t("family.leave")}</button></div> : <>
      <div className="family-session-bar">
        <span className="family-role-badge"><FamilyIcon name="family" />{t(`family.${view.role}`)}</span>
        <div className="family-session-progress"><span>{view.state_version} / {view.total_steps} {t("family.decisions")}</span><progress value={view.state_version} max={view.total_steps} aria-label={t("family.decisions")} /></div>
        <button onClick={leave} disabled={busy} className="family-leave">{t("family.leave")}</button>
      </div>
      <div className="family-room-grid">
        <aside className="family-room-sidebar">
          <details open className="family-private"><summary><FamilyIcon name="lock" /><span>{t("family.private")}</span><span className="family-disclosure" aria-hidden="true"><FamilyIcon name="chevron" /></span></summary><p>{view.private_brief_th}</p></details>
          {experience === 'coop' && <section className="family-participants" aria-label={t("family.design.participants")}>
            {([view.role, view.role === 'mother' ? 'father' : 'mother'] as const).map((item, index) => <div key={item}><span className="family-role-avatar" aria-hidden="true">{t(`family.design.${item}Initial`)}</span><p><strong>{t(`family.${item}`)}</strong><small>{t(index === 0 ? 'family.design.you' : view.partner_joined ? 'family.design.joined' : 'family.design.notJoined')}</small></p><span className={`family-presence ${index === 0 || view.partner_joined ? 'has-joined' : ''}`} aria-hidden="true" /></div>)}
          </section>}
          {!view.partner_joined && <section className="family-invite-panel"><h2>{t("family.waitPartner")}</h2><p>{t("family.shareHelp")}</p>
            <label htmlFor="family-share" className="sr-only">{t("family.invitation")}</label>
            <input id="family-share" readOnly value={inviteLink} onFocus={(event) => event.target.select()} />
            <button onClick={() => void copyInvitation()} className="button-primary"><FamilyIcon name={copied ? 'check' : 'copy'} />{t(copied ? 'family.design.copied' : 'family.design.copy')}</button>
            <p role="status">{copyFailed ? t('family.design.copyManual') : copied ? t('family.design.copySuccess') : ''}</p>
          </section>}
        </aside>
        <div className="family-room-main">
          {earlierTurns.length > 0 && <details className="family-history"><summary><FamilyIcon name="chat" />{t("family.design.history")}<span>{earlierTurns.length}</span><span className="family-disclosure" aria-hidden="true"><FamilyIcon name="chevron" /></span></summary><div>{earlierTurns.map((turn) => <Exchange key={turn.idx} turn={turn} includePrompt />)}</div></details>}
          <section role="log" aria-live="polite" aria-relevant="additions" aria-label={t("family.conversation")}>
            {lastTurn && <Exchange key={lastTurn.idx} turn={lastTurn} />}
            {pending && <div role="status" className="family-pending"><FamilyIcon name="chat" /><div><p>{view.scene?.choices.find((choice) => choice.id === pending.choice_id)?.text_th}</p><small>{t("family.sending")}</small></div></div>}
          </section>
          <p aria-live="polite" aria-atomic="true" className="family-turn-status"><span className={`family-status-dot ${waiting ? 'is-waiting' : ''}`} aria-hidden="true" />{view.report ? t("family.finished") : !view.partner_joined ? t("family.waitPartner") : view.scene?.role === view.role ? t("family.yourTurn") : t("family.partnerTurn")}</p>
          {view.scene && <section className="family-scene" aria-labelledby="family-scene-title">
            <div className="family-scene-header"><span className="family-symbol"><FamilyIcon name={experience === 'bridge' ? 'leaf' : 'chat'} /></span><div><p className="family-kicker">{view.scene.chapter_th}</p><h2 id="family-scene-title">{view.scene.speaker_th}</h2></div></div>
            <p className="family-scene-prompt">{view.scene.prompt_th}</p>
            {view.scene.choices.length > 0 && <div className="family-choices">{view.scene.choices.map((choice) => <button key={choice.id} disabled={busy || !view.partner_joined || !!pending} onClick={() => void decide(choice.id)}><span className="family-choice-mark" aria-hidden="true" /><span>{choice.text_th}</span><FamilyIcon name="arrow" /></button>)}</div>}
            {pending && !busy && <button className="button-primary family-retry" onClick={() => void decide(pending.choice_id)}>{t("family.retry")}</button>}
          </section>}
        </div>
      </div>
      {view.report && <FamilyReportPanel report={view.report} />}
    </>}
  </main>;
}

function Exchange({ turn, includePrompt = false }: { turn: View["transcript"][number]; includePrompt?: boolean }) {
  return <article className="family-exchange">
    {includePrompt && <p className="family-earlier-prompt"><strong>{turn.speaker_th}</strong>{turn.prompt_th}</p>}
    <div className="family-bubble family-bubble-learner"><strong>{t(`family.${turn.role}`)}</strong><p>{turn.text_th}</p></div>
    <div className="family-bubble family-bubble-relative"><strong>{turn.speaker_th}</strong><p>{turn.reply_th}</p></div>
  </article>;
}
