// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { FamilySimulator } from "@/components/family-simulator";
import { LESSON_UNITS_4 } from "@/components/pixel/art/lesson-stage4";
import { sceneSetup } from "@/components/pixel/cast";
import { ART, claimArt } from "@/components/pixel/lesson-art";
import { isPixelLesson, isPixelStory } from "@/components/pixel/registry";
import { BACKDROPS, CARD_SLOTS, ICONS, ITEMS, ITEM_OF } from "@/components/pixel/scene-art";
import { characterOf } from "@/components/pixel/scene-view";
import { t } from "@/lib/i18n";

const STORY = "thai-milk-family";
const UNIT = "KB-BF-COLOSTRUM-001";
const read = (file: string) => fs.readFileSync(path.resolve(__dirname, "../../../content", file), "utf-8");
const storyYaml = read(`family/${STORY}.yaml`);
const unitYaml = read(`knowledge/units/${UNIT}.yaml`);

// The yaml is authored in one-line flow maps, so a line-level read is enough (no yaml dependency in the web app).
const claims = unitYaml.split(/^ {2}- id: (c\d+)$/m).slice(1).reduce<{ id: string; hotspots: number }[]>((out, part, i, all) =>
  i % 2 === 0 ? [...out, { id: part, hotspots: (all[i + 1]!.match(/^ {6}- \{id: h\d+, label_th: .+, text_th: .+\}$/gm) ?? []).length }] : out, []);
const choices = [...storyYaml.matchAll(/^ {6}- \{id: ([a-z-]+), text_th: .*\}$/gm)].map((m) => ({
  id: m[1]!, short: m[0].match(/short_th: ([^,}]+)/)?.[1], icon: m[0].match(/icon: ([a-z]+)\}$/)?.[1],
}));
const speakers = [...new Set([...storyYaml.matchAll(/^ {4}speaker_th: (.+)$/gm)].map((m) => m[1]!))];

it("has hotspots for every claim and art with at least as many taps", () => {
  expect(claims.map((c) => c.id)).toEqual(["c1", "c2", "c3", "c4", "c5"]);
  const kinds = LESSON_UNITS_4[UNIT]!;
  expect(kinds).toHaveLength(claims.length);
  claims.forEach((c, i) => {
    expect(c.hotspots).toBeGreaterThan(0);
    expect(claimArt(UNIT, i)).toBe(kinds[i]);
    expect(ART[claimArt(UNIT, i)].taps).toBeGreaterThanOrEqual(c.hotspots);
    const lit = ART[claimArt(UNIT, i)].draw(Array(ART[claimArt(UNIT, i)].taps).fill(true));
    expect(lit).toHaveLength(64);
    expect(lit.every((row) => row.length === 96)).toBe(true);
  });
});

it("gives every choice a short label of at most 30 characters and a known icon", () => {
  expect(choices.length).toBeGreaterThanOrEqual(7);
  for (const c of choices) {
    expect(c.short, c.id).toBeTruthy();
    expect(c.short!.length, c.id).toBeLessThanOrEqual(30);
    expect(Object.keys(ICONS), c.id).toContain(c.icon);
  }
});

it("resolves a cast for both roles over every speaker, including the joint line", () => {
  expect(speakers).toEqual(expect.arrayContaining([t("pixelSim.name.counselor"), t("pixelSim.name.yai"), t("pixelSim.name.ton"), t("pixelSim.name.pair")]));
  expect(characterOf(t("pixelSim.name.pair"))).toBe("ton");
  for (const role of ["mother", "father"] as const) for (const kind of ["discover", "choice"] as const) for (const speaker of speakers) {
    const { left, backdrop } = sceneSetup(STORY, role, kind, characterOf(speaker));
    expect(characterOf(speaker)).not.toBe("neutral");
    expect(["ploy", "ton"]).toContain(left);
    expect(left).not.toBe(characterOf(speaker)); // two different people on stage
    expect(BACKDROPS[backdrop]).toBeDefined();
    expect(t(`pixelSim.backdrop.${backdrop}`).length).toBeGreaterThan(0);
  }
  // the joint line shows the couple in both views
  expect(sceneSetup(STORY, "mother", "choice", characterOf(t("pixelSim.name.pair"))).left).toBe("ploy");
  expect(sceneSetup(STORY, "father", "choice", characterOf(t("pixelSim.name.pair"))).left).toBe("ploy");
});

it("only maps icons to props that exist and shows them on its own backdrop; cards have slots", () => {
  for (const c of choices) {
    const item = ITEM_OF[c.icon as keyof typeof ITEM_OF];
    if (item && (ITEMS[item] as { on?: string[] }).on) expect((ITEMS[item] as { on: string[] }).on).toContain("livingroom");
  }
  expect(CARD_SLOTS.consult!.length).toBeGreaterThan(0);
  expect(CARD_SLOTS.livingroom!.length).toBeGreaterThan(0);
});

it("registers the lesson and the scenario", () => {
  expect(isPixelStory(STORY)).toBe(true);
  expect(isPixelLesson(UNIT)).toBe(true);
});

const ROOM = "77777777-7777-7777-7777-777777777777";
const joint = (extra = {}) => ({
  id: "agree-family-support", chapter_th: "Ch", role: "mother", speaker_th: t("pixelSim.name.pair"), prompt_th: "Decide together", joint: true,
  vote: { my_choice_id: null, waiting_for_partner: false, disagreement: null }, card: null, kind: "choice", character_th: null,
  accepts_text: false, can_continue: false, examples_th: [],
  choices: [{ id: "a", text_th: "Full A", short_th: "Short A", icon: "house" }, { id: "b", text_th: "Full B", short_th: "Short B", icon: "pause" }], ...extra,
});
const view = (role: "mother" | "father", scene = joint()) => ({
  room_id: ROOM, story_id: STORY, title_th: "Milk", role, private_brief_th: "Brief", partner_joined: true, partner_online: true, state_version: 3,
  completed_steps: 2, total_steps: 4, transcript: [], report: null, my_facts: [], shared_facts: [], dialogue: [], scene,
});
const serve = (handler: (request: Request) => Response) => vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/stories")
  ? Response.json([{ id: STORY, title_th: "t", description_th: "d", mode: "coop", chapters_th: [] }]) : handler(request)));

beforeEach(() => {
  sessionStorage.setItem(`sim-tamy-family:${STORY}`, JSON.stringify({ room_id: ROOM, token: "tok" }));
  vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener() {}, removeEventListener() {} }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear(); });

it("draws the joint step with the couple on stage in both roles", async () => {
  for (const role of ["mother", "father"] as const) {
    serve(() => Response.json(view(role)));
    const { container } = render(<FamilySimulator storyId={STORY} />);
    await screen.findByText("Decide together", { selector: ".pixel-line p" });
    expect(container.querySelector(".pixel-stage")).not.toBeNull();
    expect(container.querySelectorAll(".pixel-card-item")).toHaveLength(2);
    expect(container.querySelector("[data-backdrop='livingroom']")).not.toBeNull();
    expect(container.querySelector(".pixel-char[data-who='ploy']")).not.toBeNull();
    expect(container.querySelector(".pixel-char.is-speaker, .pixel-char[data-state][data-who='ton']")).not.toBeNull();
    cleanup();
  }
});

it("hides the cards and the partner's vote after I vote on the joint step", async () => {
  let voted = false;
  serve((request) => {
    if (request.url.endsWith("/decisions")) voted = true;
    return Response.json(voted ? view("mother", joint({ choices: [], vote: { my_choice_id: "a", waiting_for_partner: true, disagreement: null } })) : view("mother"));
  });
  const { container } = render(<FamilySimulator storyId={STORY} />);
  fireEvent.click(await screen.findByRole("radio", { name: "Short A" }));
  expect(screen.getByText("Full A", { selector: ".pixel-card-detail" })).not.toBeNull();
  fireEvent.click(screen.getByRole("button", { name: t("experience.commit") }));
  await waitFor(() => expect(container.querySelector(".pixel-panel .family-vote")).not.toBeNull());
  expect(screen.queryByRole("radio")).toBeNull();
  expect(screen.queryByText("Short B")).toBeNull();
  expect(screen.queryByText("Full B")).toBeNull();
});
