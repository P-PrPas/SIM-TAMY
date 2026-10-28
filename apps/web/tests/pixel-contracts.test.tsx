// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LESSON_ART_2 } from "@/components/pixel/art/lesson-stage2";
import { CASTS, sceneSetup } from "@/components/pixel/cast";
import { NurseryHouse, houseItems } from "@/components/pixel/house";
import { ART, claimArt } from "@/components/pixel/lesson-art";
import { BACKDROPS, CHAR_H, CHAR_W, ICONS, ITEMS, ITEM_OF, characterFrames } from "@/components/pixel/scene-art";
import type { CharacterKey } from "@/components/pixel/scene-art";
import { characterOf } from "@/components/pixel/scene-view";
import { t } from "@/lib/i18n";
import type { Attempt } from "@/lib/v2-api";

afterEach(() => { cleanup(); vi.doUnmock("@/components/pixel/registry"); vi.resetModules(); });

const CAST: CharacterKey[] = ["ploy", "ton", "teacher", "mom", "mali", "non", "yai", "counselor", "neutral"];

describe("stage 2-4 contracts", () => {
  it("draws every character in every state at the shared sprite size", () => {
    for (const who of CAST) for (const state of ["idle", "talk", "warm", "open"] as const) {
      for (const frame of characterFrames(who, state)) {
        expect(frame).toHaveLength(CHAR_H);
        expect(frame.every((row) => row.length === CHAR_W)).toBe(true);
      }
    }
  });

  it("maps each speaker name to its sprite; unknown speakers stay neutral", () => {
    const keys: [string, CharacterKey][] = [["mali", "mali"], ["non", "non"], ["yai", "yai"], ["yaisai", "yai"], ["counselor", "counselor"], ["ton", "ton"]];
    for (const [key, who] of keys) expect(characterOf(t(`pixelSim.name.${key}`))).toBe(who);
    expect(characterOf("somebody else")).toBe("neutral");
  });

  it("puts the player's own character on the left, and the partner there when the speaker is the player's character", () => {
    expect(sceneSetup("gs-a-postpartum-warning", "mother", "choice", "yai")).toMatchObject({ left: "mali", backdrop: CASTS["gs-a-postpartum-warning"]!.backdrops.choice });
    expect(sceneSetup("gs-a-postpartum-warning", "father", "choice", "yai").left).toBe("non");
    expect(sceneSetup("gs-a-postpartum-warning", "mother", "discover", "mali").left).toBe("non");
    expect(sceneSetup("thai-elements-family", "mother", "discover", "teacher")).toEqual({ left: "ploy", backdrop: "sala" });
    expect(sceneSetup("not-registered", "mother", "choice", "neutral").left).toBe("ploy"); // default cast
  });

  it("only uses backdrops, icons and items that exist", () => {
    for (const cast of Object.values(CASTS)) for (const b of Object.values(cast.backdrops)) expect(BACKDROPS[b]).toBeDefined();
    for (const item of Object.values(ITEM_OF)) expect(ITEMS[item]).toBeDefined();
    for (const icon of ["phone", "baby", "house", "heart", "help"] as const) expect(ICONS[icon].length).toBeGreaterThan(0);
    for (const frame of Object.values(ICONS)) expect(new Set(frame.map((r) => r.length)).size).toBe(1);
  });

  it("falls back to the book illustration for units and kinds without art, and keeps every unit's kinds drawable", () => {
    expect(claimArt("KB-TM-ELEMENT-001", 0)).toBe("element");
    expect(claimArt("KB-UNKNOWN", 0)).toBe("book");
    expect(claimArt("KB-TM-ELEMENT-001", 99)).toBe("book");
    for (const kind of Object.keys(LESSON_ART_2)) expect(ART[kind as keyof typeof ART].taps).toBeGreaterThan(0);
  });
});

describe("nursery house zones follow the registry", () => {
  const attempt = (over: Partial<Attempt> = {}): Attempt => ({
    room_id: "r", story_id: "thai-elements-family", title_th: "x", finished_at: "2026-10-01", safety_status: "SAFETY_MET",
    score_total: null, objective_ids: [], strong: false, ...over,
  });

  it("keeps stages 2-4 locked until their lesson and scenario are both registered", () => {
    render(<NurseryHouse attempts={null} />);
    expect(screen.getAllByText(t("pixelHouse.locked"))).toHaveLength(3);
    expect(document.querySelector("[data-zone='2']")!.getAttribute("data-open")).toBe("false");
  });

  it("opens a zone and fills its own slots from its own pair", async () => {
    vi.resetModules();
    vi.doMock("@/components/pixel/registry", () => ({
      isPixelStory: (id: string) => ["thai-elements-family", "thai-birth-conversation"].includes(id),
      isPixelLesson: (id: string) => ["KB-TM-ELEMENT-001", "KB-IP-HERITAGE-001"].includes(id),
    }));
    const { NurseryHouse: House, houseItems: items } = await import("@/components/pixel/house");
    const attempts = [attempt({ story_id: "thai-birth-conversation", strong: true })];
    const lessons = [{ unit_id: "KB-IP-HERITAGE-001", completed_at: "2026-10-02" }];
    expect(items(attempts, lessons, "2")).toEqual({ book: true, table: 2 });
    expect(items(attempts, lessons, "1")).toEqual({ book: false, table: 0 }); // stage 2 records do not fill stage 1
    render(<House attempts={attempts} lessons={lessons} />);
    expect(screen.getAllByText(t("pixelHouse.locked"))).toHaveLength(2);
    expect(document.querySelector("[data-zone='2']")!.getAttribute("data-open")).toBe("true");
    expect(screen.getByRole("link", { name: new RegExp(t("pixelHouse.zones.2")) }).getAttribute("href")).toBe("/learn/2");
  });

  it("still reads stage 1 through the default zone", () => {
    expect(houseItems([attempt()]).table).toBe(1);
  });
});
