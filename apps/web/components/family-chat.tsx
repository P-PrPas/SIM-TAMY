"use client";

import { useRef, useState } from "react";

import { ApiError, createApi } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";
import { FamilyIcon } from "./family-art";

type View = components["schemas"]["FamilyView"];
type Reply = components["schemas"]["FamilyReply"];
type Clarification = components["schemas"]["FamilyClarification"];
type Pending = { text: string; client_turn_id: string; state_version: number };
type Entry = { key: string; text: string; reply: Reply | null };

function newId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/**
 * Typed chat for one scene (AI-01/02). The learner's message shows at once; a failed send keeps the
 * text and the same client_turn_id so Retry never duplicates a turn. Critical and joint steps only
 * accept questions here: decisions stay on the buttons.
 */
export function FamilyChat({ view, credentials, onView, onChoice }: {
  view: View; credentials: { room_id: string; token: string };
  onView: (next: View) => void; onChoice: (choiceId: string) => void;
}) {
  const scene = view.scene!;
  const [draft, setDraft] = useState("");
  const [log, setLog] = useState<Entry[]>(() => (view.dialogue ?? [])
    .filter((turn) => turn.step_id === scene.id)
    .map((turn, i) => ({ key: `saved-${i}`, text: turn.text_th, reply: { speaker_th: turn.speaker_th, text_th: turn.reply_th, citations: [] } })));
  const [pending, setPending] = useState<Pending | null>(null);
  const [failed, setFailed] = useState(false);
  const [clarify, setClarify] = useState<Clarification | null>(null);
  const flying = useRef(false);

  async function send(body: Pending) {
    if (flying.current) return;
    flying.current = true; setPending(body); setFailed(false); setClarify(null);
    try {
      const { data } = await createApi({
        baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000", getToken: () => credentials.token,
      }).POST("/v1/family/rooms/{room_id}/messages", {
        params: { path: { room_id: credentials.room_id } },
        body: { text: body.text, state_version: body.state_version, client_turn_id: body.client_turn_id },
      });
      if (!data) throw new Error("Missing reply");
      setLog((prior) => [...prior, { key: body.client_turn_id, text: body.text, reply: data.reply ?? null }]);
      setClarify(data.clarification ?? null);
      setPending(null);
      onView(data.view);
    } catch (cause) {
      // a stale or invalid turn will never succeed on replay: drop it, keep the learner's words
      if (cause instanceof ApiError && cause.status < 500 && cause.code !== "NETWORK_ERROR") {
        setDraft(body.text); setPending(null);
      }
      setFailed(true);
    } finally { flying.current = false; }
  }

  function submit() {
    const text = draft.trim();
    if (!text || pending) return;
    setDraft("");
    void send({ text, client_turn_id: newId(), state_version: view.state_version });
  }

  const discover = scene.kind === "discover";
  return <section className="family-chat" aria-labelledby="family-chat-title">
    <h3 id="family-chat-title"><FamilyIcon name="chat" />{t("lab.chat.title")}</h3>
    <p className="family-muted">{t("lab.chat.hint")}</p>
    {(scene.joint || scene.choices.length > 0 && !discover) && <p className="family-muted">{t("lab.chat.buttonsOnly")}</p>}
    <div role="log" aria-live="polite" aria-relevant="additions" aria-label={t("lab.chat.log")} className="family-chat-log">
      {log.map((entry) => <article key={entry.key} className="family-exchange">
        <div className="family-bubble family-bubble-learner"><strong>{t("lab.chat.you")}</strong><p>{entry.text}</p></div>
        {entry.reply && <div className="family-bubble family-bubble-relative"><strong>{entry.reply.speaker_th}</strong><p>{entry.reply.text_th}</p>
          {entry.reply.citations.length > 0 && <ul className="family-citations" aria-label={t("lab.chat.citations")}>
            {entry.reply.citations.map((c) => <li key={`${c.knowledge_id}:${c.claim_id}`}><span className="family-source-category">{c.source_id}</span> {c.title} <small>{c.locator}</small></li>)}
          </ul>}
        </div>}
      </article>)}
      {pending && <article className="family-exchange is-pending">
        <div className="family-bubble family-bubble-learner"><strong>{t("lab.chat.you")}</strong><p>{pending.text}</p></div>
        {!failed && <p role="status" className="family-typing">{t("lab.chat.typing")}</p>}
      </article>}
    </div>
    {failed && <div role="alert" className="family-error"><FamilyIcon name="shield" /><p>{t("lab.chat.error")}</p>
      {pending && <button type="button" className="button-primary family-retry" onClick={() => void send(pending)}>{t("lab.chat.retry")}</button>}
    </div>}
    {clarify && <div className="family-clarify" role="group" aria-label={t("lab.chat.clarifyTitle")}>
      <p><strong>{t("lab.chat.clarifyTitle")}</strong></p>
      {clarify.options.map((option) => <button key={option.id} type="button" className="family-button-light"
        onClick={() => {
          if (discover) void send({ text: option.text_th, client_turn_id: newId(), state_version: view.state_version });
          else { setClarify(null); onChoice(option.id); }
        }}>{option.text_th}</button>)}
    </div>}
    <form className="family-chat-form" onSubmit={(event) => { event.preventDefault(); submit(); }}>
      <label htmlFor="family-chat-input">{t("lab.chat.label")}</label>
      <textarea id="family-chat-input" rows={2} maxLength={500} value={draft} placeholder={t("lab.chat.placeholder")}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); } }} />
      <button className="button-primary" type="submit" disabled={!draft.trim() || Boolean(pending)}>{t("lab.chat.send")}<FamilyIcon name="arrow" /></button>
    </form>
  </section>;
}
