// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { PixelLesson } from "@/components/pixel/lesson-cards";
import { buildSortItems, isSortable, LessonSort, seededOrder } from "@/components/pixel/lesson-sort";
import { t } from "@/lib/i18n";
import type { UnitDetail } from "@/lib/v2-api";

afterEach(cleanup);

const src = [{ source_id: "S41", title: "T", url: null, locator: "page 1" }];
const unit: UnitDetail = {
  id: "KB-TM-ELEMENT-001", version: "1", title_th: "Unit", care_stage: "preconception", domain: 10,
  evidence_status: "synthesis", review_basis: "knowledge_base_2026", reviewed_on: null,
  claims: [
    { id: "c1", type: "tradition", text_th: "tradition claim one", sources: src },
    { id: "c2", type: "scope", text_th: "scope claim two", sources: src },
    { id: "c3", type: "other", text_th: "other claim three", sources: [] },
  ],
  lens: { wisdom_th: "wisdom body", safety_th: "safety body", rights_th: "rights body" },
  contraindications_th: [], escalation_th: null,
};

it("assigns bins from claim type, puts lens safety/rights in scope and skips other types", () => {
  const items = buildSortItems(unit);
  expect(items.map((i) => [i.id, i.bin])).toEqual([["c1", "tradition"], ["c2", "scope"], ["lens-safety", "scope"], ["lens-rights", "scope"]]);
});

it("shuffles deterministically per seed", () => {
  const list = Array.from({ length: 12 }, (_, i) => i);
  expect(seededOrder(list, "a:0")).toEqual(seededOrder(list, "a:0"));
  expect(seededOrder(list, "a:0")).not.toEqual(seededOrder(list, "a:1"));
  expect([...seededOrder(list, "a:0")].sort((a, b) => a - b)).toEqual(list);
});

it("renders every claim verbatim with its source, and walks through the cards", () => {
  render(<PixelLesson unit={unit} />);
  for (const c of unit.claims) {
    expect(screen.getByText(c.text_th)).toBeTruthy();
    if (c.id === "c3") break;
    fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.next") }));
  }
});

it("shows the source code and locator on a card", () => {
  render(<PixelLesson unit={unit} />);
  expect(screen.getByText("S41 · page 1")).toBeTruthy();
});

it("runs the tap-tap flow with feedback, a miss reveal and the finish screen", () => {
  const onDone = vi.fn();
  const items = buildSortItems(unit);
  render(<LessonSort unit={unit} items={items} onDone={onDone} />);
  const bin = (b: string) => screen.getByRole("button", { name: t(`pixelLesson.${b}`) });
  expect((bin("binScope") as HTMLButtonElement).disabled).toBe(true);
  // first item: choose the wrong bin on purpose
  const first = screen.getAllByRole("button", { pressed: false }).find((b) => b.classList.contains("pl-item"))!;
  const firstItem = items.find((i) => i.text === first.textContent)!;
  fireEvent.click(first);
  expect(first.getAttribute("aria-pressed")).toBe("true");
  fireEvent.click(bin(firstItem.bin === "scope" ? "binTradition" : "binScope"));
  expect(screen.getByRole("status").textContent).toContain(t("pixelLesson.miss"));
  // place the rest correctly
  for (;;) {
    const next = screen.queryAllByRole("button").find((b) => b.classList.contains("pl-item"));
    if (!next) break;
    const item = items.find((i) => i.text === next.textContent)!;
    fireEvent.click(next);
    fireEvent.click(bin(item.bin === "scope" ? "binScope" : "binTradition"));
  }
  expect(onDone).toHaveBeenCalledWith(3, 4);
  expect(screen.getByText(t("pixelLesson.doneTitle"))).toBeTruthy();
});

it("skips the game and fires onComplete once when a unit has no scope items", () => {
  const plain = { ...unit, id: "KB-OTHER", claims: [unit.claims[0]!], lens: null };
  expect(isSortable(buildSortItems(plain))).toBe(false);
  const onComplete = vi.fn();
  render(<PixelLesson unit={plain} onComplete={onComplete} />);
  fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.finish") }));
  expect(onComplete).toHaveBeenCalledTimes(1);
  expect(screen.queryByText(t("pixelLesson.sortTitle"))).toBeNull();
});

it("goes from the last card into the game and calls onComplete only after it", () => {
  const onComplete = vi.fn();
  render(<PixelLesson unit={unit} onComplete={onComplete} />);
  for (let i = 0; i < 5; i++) fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.next") }));
  fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.toGame") }));
  expect(screen.getByText(t("pixelLesson.sortTitle"))).toBeTruthy();
  expect(onComplete).not.toHaveBeenCalled();
});

it("keeps the result, final feedback and replay available when the lesson game ends", () => {
  const onComplete = vi.fn();
  render(<PixelLesson unit={unit} onComplete={onComplete} />);
  for (let i = 0; i < 5; i++) fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.next") }));
  fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.toGame") }));
  const items = buildSortItems(unit);
  for (let round = 0; round < 2; round++) {
    for (const [i, item] of items.entries()) {
      fireEvent.click(screen.getByRole("button", { name: item.text }));
      const bin = i === items.length - 1 ? (item.bin === "scope" ? "tradition" : "scope") : item.bin;
      fireEvent.click(screen.getByRole("button", { name: t(bin === "scope" ? "pixelLesson.binScope" : "pixelLesson.binTradition") }));
    }
    expect(screen.getByText(t("pixelLesson.doneTitle"))).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain(t("pixelLesson.miss"));
    expect(onComplete).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.again") }));
    expect(screen.queryByText(t("pixelLesson.doneTitle"))).toBeNull();
  }
});

const spotUnit: UnitDetail = {
  ...unit,
  claims: [{ ...unit.claims[0]!, hotspots: [{ id: "h1", label_th: "spot-one", text_th: "short one" }, { id: "h2", label_th: "spot-two", text_th: "short two" }] }, ...unit.claims.slice(1)],
};

it("opens a sheet with the short text, marks the spot explored and returns focus on Esc", () => {
  render(<PixelLesson unit={spotUnit} />);
  const spot = screen.getByRole("button", { name: "spot-one" });
  spot.focus();
  fireEvent.click(spot);
  const dlg = screen.getByRole("dialog");
  expect(dlg.textContent).toContain("short one");
  expect(document.activeElement).toBe(screen.getByRole("button", { name: t("pixelLesson.close") }));
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(spot);
  expect(spot.textContent).toContain(t("pixelLesson.explored"));
  expect(screen.getByRole("button", { name: t("pixelLesson.next") }).hasAttribute("disabled")).toBe(false);
});

it("closes the sheet from the close button and the backdrop", () => {
  render(<PixelLesson unit={spotUnit} />);
  fireEvent.click(screen.getByRole("button", { name: /spot-two/ }));
  fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.close") }));
  expect(screen.queryByRole("dialog")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /spot-two/ }));
  fireEvent.click(screen.getByRole("dialog").parentElement!);
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("keeps the full claim behind read more and the sources behind the info button", () => {
  render(<PixelLesson unit={spotUnit} />);
  expect(screen.queryByText("tradition claim one")).toBeNull();
  expect(screen.queryByText(/S41/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.readMore") }));
  expect(screen.getByText("tradition claim one")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: new RegExp(t("pixelLesson.sourcesBtn")) }));
  expect(screen.getByRole("dialog").textContent).toContain("S41 · T · page 1");
});

it("falls back to the plain card when a claim has no hotspots", () => {
  render(<PixelLesson unit={unit} />);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByText("tradition claim one")).toBeTruthy();
});
