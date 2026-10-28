// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { FamilySimulator } from "@/components/family-simulator";
import { t } from "@/lib/i18n";

const ROOM = "33333333-3333-3333-3333-333333333333";
const scene = {
  id: "discover-mother", chapter_th: "Ch", role: "mother", speaker_th: "Mali", prompt_th: "Ask yourself", joint: false, vote: null, card: null,
  kind: "discover", character_th: "Mali self", accepts_text: true, can_continue: false, choices: [],
};
const view = {
  room_id: ROOM, story_id: "gs-a-postpartum-warning", title_th: "GS-A", role: "mother", private_brief_th: "Brief", partner_joined: true,
  partner_online: true, state_version: 0, completed_steps: 0, total_steps: 3, transcript: [], report: null, my_facts: [], shared_facts: [],
  dialogue: [], scene,
};
const card = { id: "gs-a-postpartum-warning", title_th: "t", description_th: "d", mode: "coop", chapters_th: [] };

beforeEach(() => sessionStorage.setItem("sim-tamy-family:gs-a-postpartum-warning", JSON.stringify({ room_id: ROOM, token: "tok" })));
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear(); });

function serve(handler: (request: Request) => Response | Promise<Response>) {
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/stories") ? Response.json([card]) : handler(request)));
}

it("shows the typed message at once, then the reply with its citation, and the answer stays in the log", async () => {
  const sent: Record<string, unknown>[] = [];
  serve(async (request) => {
    if (request.url.endsWith("/messages")) {
      sent.push(await request.json());
      return Response.json({
        view: { ...view, state_version: 1, scene: { ...scene, can_continue: true, choices: [{ id: "continue", text_th: "Next" }] } },
        reply: { speaker_th: "Mali self", text_th: "Heavier than usual", citations: [{ knowledge_id: "KB-PP-WARN-001", claim_id: "c1", source_id: "S36", title: "WHO warning signs", locator: "KB p.9" }] },
        clarification: null,
      });
    }
    return Response.json(view);
  });
  render(<FamilySimulator storyId="gs-a-postpartum-warning" />);
  const input = await screen.findByLabelText(t("lab.chat.label"));
  fireEvent.change(input, { target: { value: "ask about bleeding" } });
  fireEvent.click(screen.getByRole("button", { name: t("lab.chat.send") }));
  expect(await screen.findByText("ask about bleeding")).not.toBeNull(); // optimistic
  expect(await screen.findByText("Heavier than usual")).not.toBeNull();
  expect(screen.getByText("WHO warning signs")).not.toBeNull();
  expect(screen.getByText("S36")).not.toBeNull();
  expect(sent[0]).toMatchObject({ text: "ask about bleeding", state_version: 0 });
  expect(await screen.findByRole("button", { name: "Next" })).not.toBeNull();
  expect(screen.queryByText(t("lab.chat.askMore"))).toBeNull();
  expect(document.querySelector('[role="log"][aria-live="polite"]')).not.toBeNull();
});

it("keeps the text and the same client_turn_id on a failed send, so Retry never duplicates the turn", async () => {
  const turns: unknown[] = [];
  let fail = true;
  serve(async (request) => {
    if (request.url.endsWith("/messages")) {
      const body = await request.json();
      turns.push(body.client_turn_id);
      if (fail) { fail = false; return Response.json({ error: { code: "INTERNAL_ERROR", message: "x", details: {}, request_id: "r" } }, { status: 500 }); }
      return Response.json({ view, reply: { speaker_th: "Mali self", text_th: "Answer", citations: [] }, clarification: null });
    }
    return Response.json(view);
  });
  render(<FamilySimulator storyId="gs-a-postpartum-warning" />);
  fireEvent.change(await screen.findByLabelText(t("lab.chat.label")), { target: { value: "question" } });
  fireEvent.click(screen.getByRole("button", { name: t("lab.chat.send") }));
  expect(await screen.findByText(t("lab.chat.error"), {}, { timeout: 8000 })).not.toBeNull();
  expect(screen.getByText("question")).not.toBeNull();
  fireEvent.click(screen.getByRole("button", { name: t("lab.chat.retry") }));
  expect(await screen.findByText("Answer", {}, { timeout: 8000 })).not.toBeNull();
  expect(new Set(turns).size).toBe(1);
}, 20_000);

it("offers clarification options as buttons that resend the option text on a discover step", async () => {
  const sent: string[] = [];
  serve(async (request) => {
    if (request.url.endsWith("/messages")) {
      const body = await request.json();
      sent.push(body.text);
      return Response.json(sent.length === 1
        ? { view, reply: null, clarification: { options: [{ id: "ASK_CHEST", text_th: "Ask about chest" }] } }
        : { view, reply: { speaker_th: "Mali self", text_th: "Chest answer", citations: [] }, clarification: null });
    }
    return Response.json(view);
  });
  render(<FamilySimulator storyId="gs-a-postpartum-warning" />);
  fireEvent.change(await screen.findByLabelText(t("lab.chat.label")), { target: { value: "hmm" } });
  fireEvent.click(screen.getByRole("button", { name: t("lab.chat.send") }));
  fireEvent.click(await screen.findByRole("button", { name: "Ask about chest" }));
  expect(await screen.findByText("Chest answer")).not.toBeNull();
  expect(sent).toEqual(["hmm", "Ask about chest"]);
});

it("on a joint critical step clarification buttons commit through the decision endpoint, never by text", async () => {
  const decisions: Record<string, unknown>[] = [];
  const joint = {
    ...scene, id: "joint", kind: "choice", joint: true, can_continue: true, character_th: null,
    choices: [{ id: "contact", text_th: "Contact" }, { id: "wait", text_th: "Wait" }],
    vote: { my_choice_id: null, waiting_for_partner: false, disagreement: null },
  };
  serve(async (request) => {
    if (request.url.endsWith("/messages")) return Response.json({ view: { ...view, scene: joint }, reply: null, clarification: { options: [{ id: "contact", text_th: "Contact now" }] } });
    if (request.url.endsWith("/decisions")) { decisions.push(await request.json()); return Response.json({ ...view, scene: joint }); }
    return Response.json({ ...view, scene: joint });
  });
  render(<FamilySimulator storyId="gs-a-postpartum-warning" />);
  expect(await screen.findByText(t("lab.chat.buttonsOnly"))).not.toBeNull();
  fireEvent.change(screen.getByLabelText(t("lab.chat.label")), { target: { value: "contact them now" } });
  fireEvent.click(screen.getByRole("button", { name: t("lab.chat.send") }));
  const group = await screen.findByRole("group", { name: t("lab.chat.clarifyTitle") });
  fireEvent.click(group.querySelector("button")!);
  await waitFor(() => expect(decisions).toHaveLength(1));
  expect(decisions[0]).toMatchObject({ choice_id: "contact" });
});

it("renders the Thai Wisdom Lens as three parts and dimension scores without pass wording when the gate fails", async () => {
  const report = {
    safety_status: "SAFETY_NOT_MET", score_total: 62, competencies: [], evidence: [], sources: [],
    dimensions: [{ id: "discovery", weight: 25, earned: 3, possible: 4, score: 75 }, { id: "decision", weight: 35, earned: 0, possible: 1, score: 0 }],
  };
  const lensScene = {
    ...scene, kind: "choice", accepts_text: false, choices: [],
    card: { tradition_th: "Trad", learning_point_th: "L", evidence_status: "traditional_practice", precautions_th: [], when_to_consult_th: null, sources: [],
      lens: { wisdom_th: "Wisdom text", safety_th: "Safety text", rights_th: "Rights text" } },
  };
  let phase = 0;
  serve(async (request) => {
    if (request.url.endsWith("/debrief")) return Response.json({ attempt_id: "a", strengths: [{ text: "Good ask", event_ids: ["e"] }], improvements: [{ text: "Seek help", event_ids: ["e"] }], recommended_asset_ids: ["KB-PP-WARN-001"], fallback_used: true });
    phase += 1;
    return Response.json(phase === 1 ? { ...view, scene: lensScene } : { ...view, scene: null, completed_steps: 3, report });
  });
  render(<FamilySimulator storyId="gs-a-postpartum-warning" />);
  expect(await screen.findByText("Wisdom text")).not.toBeNull();
  expect(screen.getByText(t("lab.lens.safety"))).not.toBeNull();
  expect(screen.getByText("Rights text")).not.toBeNull();
  expect(await screen.findByText(t("lab.report.dimensions"), {}, { timeout: 8000 })).not.toBeNull();
  expect(screen.getByText(t("lab.report.dim.discovery"), { selector: "span" })).not.toBeNull();
  expect(await screen.findByText("Seek help")).not.toBeNull();
  expect(screen.getByText(t("lab.debrief.fallback"))).not.toBeNull();
  expect(screen.getAllByRole("alert").some((el) => el.textContent?.includes(t("family.safetyReview")))).toBe(true);
  expect(document.body.textContent).not.toContain(t("family.safetyObserved"));
}, 20_000);
