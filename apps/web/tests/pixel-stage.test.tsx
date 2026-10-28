// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { FamilySimulator } from "@/components/family-simulator";
import { t } from "@/lib/i18n";

const ROOM = "44444444-4444-4444-4444-444444444444";
const STORY = "thai-elements-family";
const FULL = "full sentence that is long and verbatim";
const choiceScene = {
  id: "plan", chapter_th: "Ch", role: "mother", speaker_th: t("pixelSim.name.ton"), prompt_th: "Which way", joint: false, vote: null, card: null,
  kind: "choice", character_th: null, accepts_text: true, can_continue: true, examples_th: [],
  choices: [{ id: "a", text_th: FULL, short_th: "short a", icon: "pot" }, { id: "b", text_th: "plain b" }],
};
const view = (extra = {}) => ({
  room_id: ROOM, story_id: STORY, title_th: "HeroTitle", role: "mother", private_brief_th: "Brief", partner_joined: true, partner_online: true,
  state_version: 2, completed_steps: 1, total_steps: 3, transcript: [], report: null, my_facts: [], shared_facts: [], dialogue: [], scene: choiceScene, ...extra,
});
const turn = { idx: 2, role: "mother", speaker_th: t("pixelSim.name.ton"), prompt_th: "P", text_th: FULL, reply_th: "Reply text", mood: "warm" };

function serve(story = STORY, decided = false) {
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/stories")
    ? Response.json([{ id: story, title_th: "HeroTitle", description_th: "DescText", mode: "solo", chapters_th: [] }])
    : request.url.endsWith("/decisions") ? Response.json(view({ state_version: 3, completed_steps: 2, transcript: [turn], scene: { ...choiceScene, id: "next" } }))
      : Response.json(decided ? view({ transcript: [turn] }) : view())));
}
const reduce = (on: boolean) => vi.stubGlobal("matchMedia", (q: string) => ({ matches: on && q.includes("reduce"), addEventListener() {}, removeEventListener() {} }));

beforeEach(() => { sessionStorage.setItem(`sim-tamy-family:${STORY}`, JSON.stringify({ room_id: ROOM, token: "tok" })); reduce(false); });
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear(); });

it("hides hero and progress text during play and keeps text equivalents", async () => {
  serve();
  const { container } = render(<FamilySimulator storyId={STORY} />);
  await screen.findByText(t("pixelSim.choose"));
  expect(container.querySelector(".family-hero")).toBeNull();
  expect(container.querySelector(".family-session-bar")).toBeNull();
  expect(container.querySelector("progress")).toBeNull();
  expect(screen.queryByText("HeroTitle")).toBeNull();
  expect(container.querySelector(".pixel-hud .sr-only")?.textContent).toContain("1 / 3");
  expect(screen.getByLabelText(t("pixelSim.notebook.count").replace("{n}", "0"))).not.toBeNull();
  expect(container.querySelector(".pixel-bubble.is-speaker")?.textContent).toContain("Which way");
  expect(Array.from(container.querySelectorAll("[aria-live='polite'].sr-only")).some((n) => n.textContent === "Which way")).toBe(true);
});

it("shows short labels on cards and the verbatim sentence before committing", async () => {
  serve();
  render(<FamilySimulator storyId={STORY} />);
  const card = await screen.findByLabelText("short a") as HTMLInputElement;
  expect(screen.queryByText(FULL, { selector: ".pixel-card-label" })).toBeNull();
  expect(card.getAttribute("aria-describedby")).not.toBeNull();
  expect(document.getElementById(card.getAttribute("aria-describedby")!)?.textContent).toBe(FULL);
  expect(screen.getByText("plain b")).not.toBeNull(); // no short label: falls back to text_th
  fireEvent.click(card);
  expect(document.querySelector(".pixel-card-detail")?.textContent).toContain(FULL);
});

it("runs a skippable consequence beat that changes the scene", async () => {
  serve();
  const { container } = render(<FamilySimulator storyId={STORY} />);
  fireEvent.click(await screen.findByLabelText("short a"));
  fireEvent.click(screen.getByRole("button", { name: t("experience.commit") }));
  const skip = await screen.findByRole("button", { name: t("pixelSim.skip") });
  expect(container.querySelector(".pixel-scene.is-beat")).not.toBeNull();
  expect(container.querySelector(".pixel-item.is-new")).not.toBeNull(); // pot appears on the table
  expect(container.querySelector(".pixel-bubble.is-speaker")?.textContent).toContain("Reply text");
  expect(container.querySelector(".pixel-bubble.is-you")?.textContent).toContain(FULL);
  fireEvent.click(skip);
  expect(container.querySelector(".pixel-scene.is-beat")).toBeNull();
  expect(container.querySelector(".pixel-item")).not.toBeNull(); // the table keeps the item
});

it("ends the beat by itself", async () => {
  serve();
  render(<FamilySimulator storyId={STORY} />);
  fireEvent.click(await screen.findByLabelText("short a"));
  fireEvent.click(screen.getByRole("button", { name: t("experience.commit") }));
  await screen.findByRole("button", { name: t("pixelSim.skip") });
  await vi.waitFor(() => expect(screen.queryByRole("button", { name: t("pixelSim.skip") })).toBeNull(), { timeout: 4000 });
});

it("shows the final frame at once with reduced motion", async () => {
  reduce(true);
  serve();
  const { container } = render(<FamilySimulator storyId={STORY} />);
  fireEvent.click(await screen.findByLabelText("short a"));
  fireEvent.click(screen.getByRole("button", { name: t("experience.commit") }));
  await vi.waitFor(() => expect(container.querySelector(".pixel-item")).not.toBeNull());
  expect(screen.queryByRole("button", { name: t("pixelSim.skip") })).toBeNull();
  expect(container.querySelector(".pixel-scene.is-beat")).toBeNull();
});

it("keeps the old layout for other stories", async () => {
  sessionStorage.setItem("sim-tamy-family:gs-a-postpartum-warning", JSON.stringify({ room_id: ROOM, token: "tok" }));
  serve("gs-a-postpartum-warning");
  const { container } = render(<FamilySimulator storyId="gs-a-postpartum-warning" />);
  await screen.findByText("Which way");
  expect(container.querySelector(".family-hero")).not.toBeNull();
  expect(container.querySelector(".family-session-bar progress")).not.toBeNull();
  expect(container.querySelector(".pixel-stage-frame")).toBeNull();
  expect(container.querySelector(".pixel-cards")).toBeNull();
  expect(container.querySelector(".practice-activity")).not.toBeNull();
});
