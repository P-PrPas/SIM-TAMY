// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FamilySimulator } from "@/components/family-simulator";
import { LESSON_ART_3, LESSON_UNITS_3 } from "@/components/pixel/art/lesson-stage3";
import { STAGE3_BACKDROPS, STAGE3_ITEMS, STAGE3_ITEM_OF } from "@/components/pixel/art/scene-stage3";
import { CASTS, sceneSetup } from "@/components/pixel/cast";
import { NurseryHouse } from "@/components/pixel/house";
import { ART_H, ART_W, claimArt } from "@/components/pixel/lesson-art";
import { PIXEL_LESSONS, PIXEL_STORIES, isPixelLesson, isPixelStory } from "@/components/pixel/registry";
import { BACKDROPS, ICONS, ITEM_OF, SCENE_H, SCENE_W, itemShownOn } from "@/components/pixel/scene-art";
import { characterOf } from "@/components/pixel/scene-view";
import { t } from "@/lib/i18n";

const STORY = "gs-a-postpartum-warning";
const UNIT = "KB-PP-WARN-001";
const ROOT = resolve(__dirname, "../../..");
const story = readFileSync(resolve(ROOT, "content/family/gs-a-postpartum-warning.yaml"), "utf8");
const unit = readFileSync(resolve(ROOT, "content/knowledge/units/KB-PP-WARN-001.yaml"), "utf8");
const squash = (s: string) => s.replace(/\s+/g, "");

// Tiny extractors for the two yaml files (no yaml dependency in the web app).
const claims = unit.split(/^ {2}- id: (c\d+)$/m).slice(1).reduce<{ id: string; text: string; spots: { label: string; text: string }[] }[]>((out, part, i, all) => {
  if (i % 2 === 1) return out;
  const body = all[i + 1]!;
  out.push({
    id: part, text: /^ {4}text_th: (.+)$/m.exec(body)![1]!,
    spots: [...body.matchAll(/^ {6}- \{id: h\d+, label_th: ([^,]+), text_th: (.+)\}$/gm)].map((m) => ({ label: m[1]!, text: m[2]! })),
  });
  return out;
}, []);
const steps = story.slice(story.indexOf("\nsteps:")).split(/^ {2}- id: (\S+)$/m).slice(1).reduce<{ id: string; speaker: string; choices: { id: string; short: string; icon: string }[] }[]>((out, part, i, all) => {
  if (i % 2 === 1) return out;
  const body = all[i + 1]!;
  const parts = (body.split("\n    choices:")[1] ?? "").split(/^ {6}- id: (\S+)$/m).slice(1); // intents sit before `choices:`
  const list: { id: string; short: string; icon: string }[] = [];
  for (let k = 0; k < parts.length; k += 2) {
    list.push({ id: parts[k]!, short: /^ {8}short_th: (.+)$/m.exec(parts[k + 1]!)?.[1] ?? "", icon: /^ {8}icon: (\w+)$/m.exec(parts[k + 1]!)?.[1] ?? "" });
  }
  out.push({ id: part, speaker: /^ {4}speaker_th: (.+)$/m.exec(body)![1]!, choices: list });
  return out;
}, []);
const realChoices = steps.flatMap((s) => s.choices.map((c) => ({ ...c, step: s.id })));

describe("lesson hotspots and art", () => {
  it("covers every claim and quotes it contiguously", () => {
    expect(claims.map((c) => c.id)).toEqual(["c1", "c2", "c3", "c4"]);
    for (const c of claims) {
      expect(c.spots.length).toBeGreaterThan(0);
      for (const s of c.spots) {
        expect(squash(c.text)).toContain(squash(s.text));
        expect(s.text.length).toBeLessThanOrEqual(60);
        expect(s.label.trim().split(/\s+/).length).toBeLessThanOrEqual(3);
      }
    }
  });

  it("has an illustration per claim with at least as many taps as hotspots, and tap i lights spot i", () => {
    expect(LESSON_UNITS_3[UNIT]).toHaveLength(claims.length);
    claims.forEach((c, i) => {
      const kind = claimArt(UNIT, i);
      expect(kind).not.toBe("book");
      expect(kind in LESSON_ART_3).toBe(true);
      const art = LESSON_ART_3[kind as keyof typeof LESSON_ART_3];
      expect(art.taps).toBeGreaterThanOrEqual(c.spots.length);
      const off = art.draw(Array(art.taps).fill(false));
      expect(off).toHaveLength(ART_H);
      expect(off.every((row) => row.length === ART_W)).toBe(true);
      c.spots.forEach((_, j) => {
        const on = Array(art.taps).fill(false) as boolean[];
        on[j] = true;
        expect(art.draw(on)).not.toEqual(off);
      });
    });
  });
});

describe("story choices", () => {
  it("gives every choice a short label (<= 30 chars) and a known icon", () => {
    expect(realChoices.length).toBe(15);
    for (const c of realChoices) {
      expect(c.short.length, `${c.step}/${c.id}`).toBeGreaterThan(0);
      expect(c.short.length).toBeLessThanOrEqual(30);
      expect(Object.keys(ICONS)).toContain(c.icon);
    }
  });

  it("leaves no prop behind for the stalling options, only for calm ones", () => {
    const icon = (step: string, id: string) => steps.find((s) => s.id === step)!.choices.find((c) => c.id === id)!.icon;
    for (const [step, id] of [["joint-help-decision", "wait-until-morning"], ["joint-help-decision", "tradition-first"], ["share-with-partner", "say-fine"]] as const) {
      const item = ITEM_OF[icon(step, id) as keyof typeof ICONS];
      expect(!item || !itemShownOn(item, CASTS[STORY]!.backdrops.choice)).toBe(true);
    }
    expect(ITEM_OF[icon("joint-help-decision", "contact-health-service") as keyof typeof ICONS]).toBe("gsPhone");
  });
});

describe("scene cast and art", () => {
  it("resolves both roles over every speaker with the partner on the left when the speaker is the player", () => {
    const cast = CASTS[STORY]!;
    expect([cast.mother, cast.father]).toEqual(["mali", "non"]);
    for (const s of steps) {
      const speaker = characterOf(s.speaker);
      expect(speaker, s.speaker).not.toBe("neutral");
      for (const role of ["mother", "father"] as const) {
        for (const kind of ["discover", "choice"] as const) {
          const setup = sceneSetup(STORY, role, kind, speaker);
          expect(setup.left).not.toBe(speaker); // never the same sprite twice
          expect(Object.keys(BACKDROPS)).toContain(setup.backdrop);
        }
      }
    }
    expect(sceneSetup(STORY, "mother", "discover", "mali").left).toBe("non");
    expect(sceneSetup(STORY, "father", "discover", "non").left).toBe("mali");
    expect(sceneSetup(STORY, "mother", "choice", "yai").left).toBe("mali");
  });

  it("names every backdrop and keeps backdrops and props inside the scene", () => {
    for (const key of Object.keys(STAGE3_BACKDROPS)) {
      expect(t(`pixelSim.backdrop.${key}`)).not.toBe(`pixelSim.backdrop.${key}`);
      for (const [x, y, w, h] of STAGE3_BACKDROPS[key as keyof typeof STAGE3_BACKDROPS]) {
        expect(x).toBeGreaterThanOrEqual(0); expect(y).toBeGreaterThanOrEqual(0);
        expect(x + w).toBeLessThanOrEqual(SCENE_W); expect(y + h).toBeLessThanOrEqual(SCENE_H);
      }
    }
    for (const item of Object.values(STAGE3_ITEMS)) expect(new Set(item.art.map((r) => r.length)).size).toBe(1);
    for (const key of Object.values(STAGE3_ITEM_OF)) expect(key in STAGE3_ITEMS).toBe(true);
  });
});

describe("registry and house", () => {
  it("registers the stage 3 pair and opens house zone 3", () => {
    expect(isPixelStory(STORY)).toBe(true);
    expect(isPixelLesson(UNIT)).toBe(true);
    expect(PIXEL_STORIES.has(STORY) && PIXEL_LESSONS.has(UNIT)).toBe(true);
    render(<NurseryHouse attempts={null} />);
    expect(document.querySelector("[data-zone='3']")!.getAttribute("data-open")).toBe("true");
    cleanup();
  });
});

// ---- play views (mocked API) ----
const ROOM = "66666666-6666-6666-6666-666666666666";
const mine = [{ id: "m-bleed", role: "mother", text_th: "Mine one", shared: false }];
const shortOf = (id: string) => steps.find((s) => s.id === "joint-help-decision")!.choices.find((c) => c.id === id)!.short;
const joint = (extra = {}) => ({
  id: "joint-help-decision", chapter_th: "Ch", role: "mother", speaker_th: t("pixelSim.name.yaisai"), prompt_th: "Decide together", joint: true,
  vote: { my_choice_id: null, waiting_for_partner: false, disagreement: null }, card: null, kind: "choice", character_th: null,
  accepts_text: false, can_continue: false, examples_th: [],
  choices: [
    { id: "contact-health-service", text_th: "Full contact sentence", short_th: shortOf("contact-health-service"), icon: "phone" },
    { id: "wait-until-morning", text_th: "Full wait sentence", short_th: shortOf("wait-until-morning"), icon: "pause" },
    { id: "tradition-first", text_th: "Full tradition sentence", short_th: shortOf("tradition-first"), icon: "pot" },
  ], ...extra,
});
const view = (extra = {}) => ({
  room_id: ROOM, story_id: STORY, title_th: "GS-A", role: "mother", private_brief_th: "Brief", partner_joined: true, partner_online: true,
  state_version: 4, completed_steps: 5, total_steps: 8, transcript: [], report: null, my_facts: mine, shared_facts: [], dialogue: [], scene: joint(), ...extra,
});
function serve(handler: () => Response) {
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/stories")
    ? Response.json([{ id: STORY, title_th: "t", description_th: "d", mode: "coop", chapters_th: [] }]) : handler()));
}
beforeEach(() => {
  sessionStorage.setItem(`sim-tamy-family:${STORY}`, JSON.stringify({ room_id: ROOM, token: "tok" }));
  vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener() {}, removeEventListener() {} }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear(); });

describe("co-op play on the real stage 3 registration", () => {
  it("draws the joint critical step with icon cards, the hall backdrop and the partner on the left", async () => {
    serve(() => Response.json(view()));
    const { container } = render(<FamilySimulator storyId={STORY} />);
    for (const short of ["contact-health-service", "wait-until-morning", "tradition-first"].map(shortOf)) expect(await screen.findByText(short)).toBeTruthy();
    expect(screen.getAllByRole("radio")).toHaveLength(3);
    expect(container.querySelector(".pixel-scene-stage")!.getAttribute("data-backdrop")).toBe("postpartumHall");
    const who = [...container.querySelectorAll(".pixel-char")].map((el) => el.getAttribute("data-who"));
    expect(who).toEqual(["mali", "yai"]); // mother view, the elder speaks
    expect(container.querySelector(".pixel-panel > details.pixel-know")).not.toBeNull();
  });

  it("shows the father with Mali on the left when the speaker is Non, on the room backdrop for a discover step", async () => {
    serve(() => Response.json(view({ role: "father", scene: joint({ role: "father", kind: "discover", joint: false, vote: null, speaker_th: t("pixelSim.name.non"),
      accepts_text: true, can_continue: true, examples_th: ["e1"], choices: [{ id: "continue", text_th: "Go on", short_th: "Go", icon: "arrow" }] }) })));
    const { container } = render(<FamilySimulator storyId={STORY} />);
    await screen.findByText("Decide together", { selector: ".pixel-line p" });
    expect(container.querySelector(".pixel-scene-stage")!.getAttribute("data-backdrop")).toBe("postpartumRoom");
    expect([...container.querySelectorAll(".pixel-char")].map((el) => el.getAttribute("data-who"))).toEqual(["mali", "non"]);
  });

  it("hides the cards and the partner's vote after I vote on the critical step", async () => {
    let voted = false;
    serve(() => Response.json(voted ? view({ state_version: 5, scene: joint({ choices: [], vote: { my_choice_id: "wait-until-morning", waiting_for_partner: true, disagreement: null } }) }) : view()));
    const { container } = render(<FamilySimulator storyId={STORY} />);
    fireEvent.click(await screen.findByRole("radio", { name: new RegExp(shortOf("wait-until-morning")) }));
    voted = true;
    fireEvent.click(screen.getByRole("button", { name: t("experience.commit") }));
    await waitFor(() => expect(screen.queryByRole("radio")).toBeNull());
    expect(await screen.findByText(t("family.cosim.joint.waiting"), { selector: ".family-vote-waiting" })).not.toBeNull();
    expect(container.querySelector(".pixel-cards")).toBeNull();
    expect(screen.queryByText("Full contact sentence")).toBeNull();
    expect(container.querySelector(".pixel-item")).toBeNull(); // no prop for the stalling option
  });
});
