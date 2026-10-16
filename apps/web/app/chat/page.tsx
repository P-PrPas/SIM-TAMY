"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { appendOptimistic, failPending, resolvePending, retryPending, type ChatMessage } from "@/lib/chat-state";
import { readSession, sanitizeMessage } from "@/lib/flow";
import { t } from "@/lib/i18n";

type CaseBrief = components["schemas"]["CaseBrief"];
type SessionView = components["schemas"]["SessionView"];
const quickPromptKeys = ["chat.quickPromptReason", "chat.quickPromptWhen", "chat.quickPromptMore"] as const;

export default function ChatPage() {
  const { push, replace } = useRouter();
  const [brief, setBrief] = useState<CaseBrief | null>(null);
  const [session, setSession] = useState<SessionView | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState("");
  const messageRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const active = readSession();
    if (!active) { replace("/"); return; }
    let cancelled = false;
    void api().GET("/v1/sessions/{session_id}", { params: { path: { session_id: active.id } } })
      .then((sessionResult) => {
      if (cancelled) return;
      if (!sessionResult.data) { setError(t("chat.loadError")); return; }
      if (sessionResult.data.phase === "COMPLETED") { replace("/report"); return; } // nothing to send; the report is next
      setSession(sessionResult.data);
      setBrief(active.brief); // the version this session was created with, not the latest case
      setMessages(sessionResult.data.history.map((message, position) => ({
        id: `history-${position}`,
        idx: message.idx,
        speaker: message.speaker,
        text: message.text,
        delivery: "sent" as const,
      })));
    }).catch(() => { if (!cancelled) setError(t("chat.loadError")); });
    return () => { cancelled = true; };
  }, [replace]);

  async function send(text: string, id: string) {
    const active = readSession();
    if (!active) { setError(t("chat.expired")); return; }
    setInFlight(true);
    setError("");
    try {
      const { data } = await api().POST("/v1/sessions/{session_id}/turns", {
        params: { path: { session_id: active.id } },
        body: { text, client_turn_id: id },
      });
      if (!data || typeof data !== "object" || !("turn_idx" in data)) throw new Error("Missing turn response");
      setMessages((current) => resolvePending(current, id, data.turn_idx, data.replies));
      setSession((current) => current ? { ...current, turn_idx: data.turn_idx, turns_remaining: data.turns_remaining, phase: data.phase } : current);
    } catch {
      setMessages((current) => failPending(current, id));
      setError(t("chat.sendError"));
    } finally {
      setInFlight(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight || messages.some((item) => item.delivery === "failed")) return;
    const text = sanitizeMessage(draft);
    if (!text) { setError(t("chat.invalidMessage")); return; }
    const id = crypto.randomUUID();
    setMessages((current) => appendOptimistic(current, text, id));
    setDraft("");
    void send(text, id);
  }

  function retry(message: ChatMessage) {
    if (inFlight) return;
    setMessages((current) => retryPending(current, message.id));
    void send(message.text, message.id);
  }

  if (!brief || !session) return <main className="mx-auto max-w-5xl px-4 py-8">
    {error ? <p role="alert" className="rounded-xl bg-rose-50 p-4 text-rose-950">{error}</p> : <p role="status">{t("chat.loading")}</p>}
  </main>;

  const canSend = session.phase === "PRESSURE" || (session.phase === "INTERVIEW" && session.turns_remaining > 0);
  const canCompose = canSend && !inFlight && !messages.some((item) => item.delivery === "failed");
  const canChoosePrompt = canCompose && draft.trim().length === 0;
  return <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-sm font-bold tracking-wide text-teal-800">{t("chat.eyebrow")}</p>
        <h1 className="mt-2 text-2xl font-bold text-slate-950 sm:text-3xl">{t("chat.title")}</h1>
        <p className="mt-1 text-slate-700">{brief.title_th}</p>
        {session.phase === "PRESSURE" && <p role="status" className="mt-2 font-semibold text-amber-900">{t("chat.pressure")}</p>}
      </div>
      <StatusBadge status={session.case.status} />
    </header>
    <div className="grid gap-5 lg:grid-cols-[1fr_18rem]">
      <section aria-label={t("chat.title")} className="flex min-h-[60vh] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {session.phase !== "PRESSURE" && <div className="border-b border-slate-200 bg-slate-50 px-5 py-3 font-semibold text-slate-800">
          {t("chat.turnsRemaining")}: {session.turns_remaining}
        </div>}
        <ol aria-live="polite" aria-relevant="additions" className="flex-1 space-y-4 p-4 sm:p-6">
          {messages.map((message) => <li key={message.id} className={`max-w-[90%] rounded-2xl p-4 shadow-sm ${message.speaker === "learner" ? "ml-auto bg-teal-900 text-white" : "border border-slate-200 bg-slate-50 text-slate-950"}`}>
            <p className="mb-1 text-sm font-bold">{t(`chat.${message.speaker}`)}</p>
            <p className="whitespace-pre-wrap break-words">{message.text}</p>
            {message.delivery === "failed" && <button type="button" onClick={() => retry(message)} disabled={inFlight} className="mt-3 rounded-lg bg-amber-300 px-3 py-2 text-sm font-bold text-slate-950 disabled:opacity-50">{t("chat.retry")}</button>}
          </li>)}
        </ol>
        {inFlight && <p role="status" className="px-5 pb-3 text-slate-700">{t("chat.typing")}</p>}
        {error && <p role="alert" className="mx-4 mb-3 rounded-lg bg-rose-50 p-3 text-rose-950">{error}</p>}
        <form onSubmit={submit} className="border-t border-slate-200 p-4 sm:p-5">
          <details className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <summary className="cursor-pointer text-base font-semibold text-teal-900">{t("chat.quickPromptsTitle")}</summary>
            <p className="mt-2 text-base text-slate-700">{t("chat.quickPromptsHelp")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {quickPromptKeys.map((key) => <button
                key={key}
                type="button"
                disabled={!canChoosePrompt}
                onClick={() => { setDraft(t(key)); setError(""); messageRef.current?.focus(); }}
                className="rounded-lg border border-teal-700 bg-white px-3 py-2 text-left text-base text-teal-950 hover:bg-teal-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:opacity-50"
              >{t(key)}</button>)}
            </div>
          </details>
          <label htmlFor="message" className="mb-2 block font-semibold">{t("chat.messageLabel")}</label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <textarea ref={messageRef} id="message" value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={500} rows={2} placeholder={t("chat.messagePlaceholder")} disabled={!canCompose} className="min-w-0 flex-1 resize-y rounded-xl border border-slate-400 px-4 py-3 focus:outline-teal-700 disabled:bg-slate-100" />
            <button type="submit" disabled={!canCompose} className="rounded-xl bg-teal-900 px-5 py-3 font-bold text-white hover:bg-teal-800 disabled:opacity-50">{t("chat.send")}</button>
          </div>
          <p className="mt-2 text-sm font-semibold text-amber-900">{t("chat.privacy")}</p>
        </form>
      </section>
      <aside className="space-y-5">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-bold">{t("chat.initialInfo")}</h2>
          <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-700">{brief.patient_display_th}</p>
        </section>
        {session.phase === "INTERVIEW" && <button type="button" onClick={() => push("/decision")} disabled={inFlight || messages.some((item) => item.delivery === "failed")} className="w-full rounded-xl bg-teal-900 px-5 py-3 font-bold text-white disabled:opacity-50">{t("chat.decide")}</button>}
        {session.phase === "CLOSING" && <Link href="/closing" className="block rounded-xl bg-teal-900 px-5 py-3 text-center font-bold text-white">{t("chat.toClosing")}</Link>}
      </aside>
    </div>
  </main>;
}
