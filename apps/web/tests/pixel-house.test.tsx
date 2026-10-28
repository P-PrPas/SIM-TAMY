// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NurseryHouse, houseItems } from "@/components/pixel/house";
import { HouseReveal, metersFor } from "@/components/pixel/reveal";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";
import type { Attempt } from "@/lib/v2-api";

type Ev = components["schemas"]["FamilyEvidence"];
const ev = (idx: number, over: Partial<Ev> = {}): Ev => ({
  idx, text_th: `choice-${idx}`, feedback_th: "f", source_ids: ["S1"], safe: true, skills: [], dimension: null, critical: false, kind: "choice", ...over,
});
const attempt = (over: Partial<Attempt> = {}): Attempt => ({
  room_id: "r", story_id: "thai-elements-family", title_th: "x", finished_at: "2026-10-01", safety_status: "SAFETY_MET", score_total: 50, objective_ids: [], ...over,
});

afterEach(() => { cleanup(); vi.useRealTimers(); });

describe("NurseryHouse", () => {
  it("locks stages 2-4 and leaves slots empty without finished attempts", () => {
    render(<NurseryHouse attempts={[attempt({ finished_at: null }), attempt({ story_id: "other" })]} />);
    expect(screen.getAllByText(t("pixelHouse.locked"))).toHaveLength(3);
    expect(screen.getByText(t("pixelHouse.itemState.table"), { exact: false })).toBeTruthy();
    expect(houseItems(null).table).toBe(0);
  });
  it("fills the table from a finished attempt and upgrades it on replay, never adds a score", () => {
    expect(houseItems([attempt()]).table).toBe(1);
    expect(houseItems([attempt(), attempt({ safety_status: "SAFETY_NOT_MET" })]).table).toBe(2);
    render(<NurseryHouse attempts={[attempt()]} />);
    expect(screen.getByText(t("pixelHouse.itemState.have"), { exact: false })).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/XP|\d+\s*%/);
  });
});

describe("HouseReveal", () => {
  it("derives meters from skills and dimension", () => {
    expect(metersFor(ev(1, { skills: ["support"] }))).toEqual(["heart"]);
    expect(metersFor(ev(1, { skills: ["responsibility", "safety"] }))).toEqual(["clear", "safe"]);
    expect(metersFor(ev(1, { dimension: "evidence_scope" }))).toEqual(["clear"]);
    expect(metersFor(ev(1))).toEqual([]);
  });
  it("hides the safety meter without a critical step and shows it with one", () => {
    const { rerender } = render(<HouseReveal evidence={[ev(1)]} safetyStatus="SAFETY_MET" />);
    expect(document.querySelector('[data-meter="safe"]')).toBeNull();
    rerender(<HouseReveal evidence={[ev(1, { critical: true })]} safetyStatus="SAFETY_MET" />);
    expect(document.querySelector('[data-meter="safe"]')).not.toBeNull();
  });
  it("plays step by step, shows an open beat for a no-skill choice, and skip jumps to the end", () => {
    vi.useFakeTimers();
    render(<HouseReveal evidence={[ev(1, { skills: ["support"] }), ev(2), ev(3, { skills: ["communication"] })]} safetyStatus="SAFETY_MET" />);
    expect(document.querySelector("[data-final]")).toBeNull();
    act(() => { vi.advanceTimersByTime(1200); });
    act(() => { vi.advanceTimersByTime(1200); });
    expect(screen.getByText(t("pixelHouse.reveal.open"))).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: t("pixelHouse.reveal.skip") }));
    expect(document.querySelector("[data-final]")?.textContent).toBe(t("pixelHouse.reveal.finalMet"));
    expect(document.querySelectorAll('[data-meter="heart"] [data-on="true"]')).toHaveLength(2);
    expect(screen.queryByRole("button", { name: t("pixelHouse.reveal.skip") })).toBeNull();
  });
  it("never celebrates when safety is not met", () => {
    render(<HouseReveal evidence={[ev(1, { skills: ["safety"], critical: true, safe: false })]} safetyStatus="SAFETY_NOT_MET" />);
    fireEvent.click(screen.getByRole("button", { name: t("pixelHouse.reveal.skip") }));
    expect(document.querySelector("[data-final]")?.textContent).toBe(t("pixelHouse.reveal.finalReview"));
    expect(document.body.textContent).not.toContain(t("pixelHouse.reveal.finalMet"));
  });
  it("shows the final state at once under reduced motion", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    render(<HouseReveal evidence={[ev(1, { skills: ["support"] })]} safetyStatus="SAFETY_MET" />);
    expect(document.querySelector("[data-final]")).not.toBeNull();
    vi.unstubAllGlobals();
  });
});
