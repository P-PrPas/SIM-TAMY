// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { FamilySimulator } from "@/components/family-simulator";
import { PixelScene, characterOf } from "@/components/pixel/scene-view";
import { t } from "@/lib/i18n";

const ROOM = "44444444-4444-4444-4444-444444444444";
const STORY = "thai-elements-family";
const scene = {
  id: "ask-the-teacher", chapter_th: "Ch", role: "mother", speaker_th: t("pixelSim.name.teacher"), prompt_th: "Ask", joint: false, vote: null, card: null,
  kind: "discover", character_th: t("pixelSim.name.teacher"), accepts_text: true, can_continue: false, choices: [],
  examples_th: ["example one", "example two", "example three"],
};
const view = (story: string) => ({
  room_id: ROOM, story_id: story, title_th: "T", role: "mother", private_brief_th: "Brief", partner_joined: true, partner_online: true,
  state_version: 0, completed_steps: 0, total_steps: 3, transcript: [], report: null, my_facts: [], shared_facts: [], dialogue: [], scene,
});
const citation = { knowledge_id: "KB-TM-ELEMENT-001", claim_id: "c1", source_id: "S41", title: "Element book", locator: "p.1" };

beforeEach(() => {
  for (const id of [STORY, "gs-b-thai-recovery"]) sessionStorage.setItem(`sim-tamy-family:${id}`, JSON.stringify({ room_id: ROOM, token: "tok" }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear(); });

function serve(story: string, onMessage?: () => Response) {
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/stories")
    ? Response.json([{ id: story, title_th: "T", description_th: "d", mode: "solo", chapters_th: [] }])
    : request.url.endsWith("/messages") && onMessage ? onMessage() : Response.json(view(story))));
}

it("maps the story mood to a reaction class and announces it in text", () => {
  const speaker = t("pixelSim.name.ton");
  const { container, rerender } = render(<PixelScene speaker={speaker} backdrop="kitchen" mood="warm" />);
  expect(container.querySelectorAll(".pixel-char.is-warm").length).toBe(2);
  expect(container.querySelector(".pixel-heart")).not.toBeNull();
  expect(screen.getByRole("status").textContent).toContain(speaker);
  rerender(<PixelScene speaker={speaker} backdrop="kitchen" mood="open" />);
  expect(container.querySelectorAll(".pixel-char.is-open").length).toBe(2);
  expect(container.querySelector(".pixel-heart")).toBeNull();
  rerender(<PixelScene speaker={speaker} backdrop="kitchen" mood={null} talking />);
  expect(container.querySelector("[data-who='ton']")?.getAttribute("data-state")).toBe("talk");
  expect(container.querySelector(".pixel-scene")?.getAttribute("aria-hidden")).toBe("true");
});

it("falls back to a neutral sprite for unknown speakers", () => {
  expect(characterOf("somebody else")).toBe("neutral");
  const { container } = render(<PixelScene speaker="somebody else" backdrop="sala" />);
  expect(container.querySelector("[data-who='neutral']")).not.toBeNull();
});

it("rotates the example question 1, 2, 3 and back", async () => {
  serve(STORY);
  render(<FamilySimulator storyId={STORY} />);
  const input = await screen.findByLabelText(t("lab.chat.label")) as HTMLTextAreaElement;
  const button = screen.getByRole("button", { name: t("pixelSim.dontKnow") });
  const seen: string[] = [];
  for (let i = 0; i < 4; i++) { fireEvent.click(button); seen.push(input.value); }
  expect(seen).toEqual(["example one", "example two", "example three", "example one"]);
});

it("flies a reply citation into the notebook as a card", async () => {
  serve(STORY, () => Response.json({
    view: { ...view(STORY), state_version: 1 }, clarification: null,
    reply: { speaker_th: "Teacher", text_th: "Books differ", citations: [citation, citation] },
  }));
  const { container } = render(<FamilySimulator storyId={STORY} />);
  expect(await screen.findByText(t("pixelSim.notebook.empty"))).not.toBeNull();
  fireEvent.change(await screen.findByLabelText(t("lab.chat.label")), { target: { value: "why differ" } });
  fireEvent.click(screen.getByRole("button", { name: t("lab.chat.send") }));
  const notebook = await screen.findByRole("region", { name: t("pixelSim.notebook.title") });
  await vi.waitFor(() => expect(notebook.querySelectorAll("li").length).toBe(1)); // duplicate citation = one card
  expect(notebook.textContent).toContain("S41");
  expect(notebook.textContent).toContain("Element book");
  expect(container.querySelector(".pixel-fly")).not.toBeNull();
  expect((await screen.findAllByText("Books differ")).length).toBeGreaterThan(0); // full text is available at once
});

it("leaves every other story without the pixel scene or the example button", async () => {
  serve("gs-b-thai-recovery");
  const { container } = render(<FamilySimulator storyId="gs-b-thai-recovery" />);
  await screen.findByLabelText(t("lab.chat.label"));
  expect(container.querySelector(".pixel-scene")).toBeNull();
  expect(container.querySelector(".is-rpg")).toBeNull();
  expect(screen.queryByRole("button", { name: t("pixelSim.dontKnow") })).toBeNull();
});

it.each([
  ["ton", "warm"],
  ["mom", "idle"],
])("keeps the last reaction with its speaker when the next scene shows %s", async (speaker, expected) => {
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/stories")
    ? Response.json([{ id: STORY, title_th: "T", description_th: "d", mode: "solo", chapters_th: [] }])
    : Response.json({ ...view(STORY), completed_steps: 2, state_version: 2,
      scene: { ...scene, kind: "choice", speaker_th: t(`pixelSim.name.${speaker}`) },
      transcript: [{ idx: 2, role: "mother", speaker_th: t("pixelSim.name.ton"), prompt_th: "P", text_th: "C", reply_th: "R", mood: "warm" }],
    })));
  const { container } = render(<FamilySimulator storyId={STORY} />);
  await screen.findByLabelText(t("lab.chat.label"));
  expect(container.querySelector(`[data-who="${speaker}"]`)?.getAttribute("data-state")).toBe(expected);
});

it("clears notebook cards when leaving and starting a new room", async () => {
  serve(STORY, () => Response.json({
    view: { ...view(STORY), state_version: 1 }, clarification: null,
    reply: { speaker_th: "Teacher", text_th: "Books differ", citations: [citation] },
  }));
  render(<FamilySimulator storyId={STORY} />);
  fireEvent.change(await screen.findByLabelText(t("lab.chat.label")), { target: { value: "why differ" } });
  fireEvent.click(screen.getByRole("button", { name: t("lab.chat.send") }));
  await vi.waitFor(() => expect(screen.getByRole("region", { name: t("pixelSim.notebook.title") }).textContent).toContain("S41"));
  fireEvent.click(screen.getByRole("button", { name: t("family.leave") }));
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/rooms")
    ? Response.json({ room_id: ROOM, token: "new-token" }) : Response.json(view(STORY))));
  fireEvent.click(await screen.findByRole("button", { name: t("family.startSolo") }));
  await screen.findByLabelText(t("lab.chat.label"));
  const notebook = screen.getByRole("region", { name: t("pixelSim.notebook.title") });
  expect(notebook.textContent).not.toContain("S41");
  expect(notebook.textContent).toContain(t("pixelSim.notebook.empty"));
});
