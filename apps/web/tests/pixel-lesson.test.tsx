// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PixelLesson } from "@/components/pixel/lesson-cards";
import { KnowledgeUnit } from "@/components/platform/knowledge";
import { setDemoAccount } from "@/lib/demo-account";
import { buildSortItems, isSortable, LessonSort, seededOrder } from "@/components/pixel/lesson-sort";
import { t } from "@/lib/i18n";
import type { UnitDetail } from "@/lib/v2-api";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });

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

it("shows the short text in the info window beside the picture and marks the spot explored", () => {
  render(<PixelLesson unit={spotUnit} />);
  expect(screen.getByText(t("pixelLesson.infoEmpty"))).toBeTruthy();
  const spot = screen.getByRole("button", { name: "spot-one" });
  fireEvent.click(spot);
  expect(screen.queryByRole("dialog")).toBeNull(); // nothing covers the picture
  const info = screen.getByRole("complementary", { name: t("pixelLesson.infoTitle") });
  expect(info.textContent).toContain("short one");
  expect(spot.getAttribute("aria-pressed")).toBe("true");
  expect(spot.textContent).toContain(t("pixelLesson.explored"));
  expect(screen.getByRole("button", { name: t("pixelLesson.next") }).hasAttribute("disabled")).toBe(false);
});

it("swaps the info window from one spot to the next without closing anything", () => {
  render(<PixelLesson unit={spotUnit} />);
  fireEvent.click(screen.getByRole("button", { name: /spot-one/ }));
  fireEvent.click(screen.getByRole("button", { name: /spot-two/ }));
  const info = screen.getByRole("complementary", { name: t("pixelLesson.infoTitle") });
  expect(info.textContent).toContain("short two");
  expect(info.textContent).not.toContain("short one");
  expect(screen.getByRole("button", { name: /spot-one/ }).getAttribute("aria-pressed")).toBe("false");
});

it("keeps the full claim behind read more and the sources behind the info button", () => {
  render(<PixelLesson unit={spotUnit} />);
  expect(screen.queryByText("tradition claim one")).toBeNull();
  expect(screen.queryByText(/S41/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: t("pixelLesson.readMore") }));
  expect(screen.getByText("tradition claim one")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: new RegExp(t("pixelLesson.sourcesBtn")) }));
  expect(screen.getByRole("complementary", { name: t("pixelLesson.infoTitle") }).textContent).toContain("S41 · T · page 1");
});

it("falls back to the plain card when a claim has no hotspots", () => {
  render(<PixelLesson unit={unit} />);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByText("tradition claim one")).toBeTruthy();
});

describe("lesson completion is recorded server-side", () => {
  const plain = { ...unit, claims: [unit.claims[0]!], lens: null };
  function mockApi(complete: () => Response) {
    const calls: Request[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: string | Request, init?: RequestInit) => {
      const req = new Request(input, init);
      calls.push(req);
      const { pathname } = new URL(req.url);
      return pathname.endsWith("/lessons/KB-TM-ELEMENT-001") ? complete() : Response.json(plain);
    }));
    return calls;
  }
  const posts = (calls: Request[]) => calls.filter((c) => c.method === "POST");
  async function finishLesson() {
    render(<KnowledgeUnit id="KB-TM-ELEMENT-001" />);
    fireEvent.click(await screen.findByRole("button", { name: t("pixelLesson.finish") }));
  }

  it("posts once for the picked account when the lesson finishes", async () => {
    setDemoAccount("acc-l1");
    const calls = mockApi(() => Response.json({ unit_id: "KB-TM-ELEMENT-001", completed_at: "2026-10-01T00:00:00Z" }));
    await finishLesson();
    await waitFor(() => expect(posts(calls)).toHaveLength(1));
    expect(new URL(posts(calls)[0]!.url).pathname).toBe("/v1/passport/acc-l1/lessons/KB-TM-ELEMENT-001");
    expect(posts(calls)[0]!.headers.get("X-Demo-Account")).toBe("acc-l1");
    expect(screen.getByText(t("pixelLesson.lessonDone"))).toBeTruthy();
    expect(localStorage.length).toBe(1); // only the picked mock profile, no completion flag
  });

  it("still shows the lesson as done when the server call fails, and stores nothing locally", async () => {
    setDemoAccount("acc-l1");
    const calls = mockApi(() => Response.json({ error: { code: "INTERNAL_ERROR" } }, { status: 500 }));
    await finishLesson();
    await waitFor(() => expect(posts(calls)).toHaveLength(1));
    expect(screen.getByText(t("pixelLesson.lessonDone"))).toBeTruthy();
    expect(localStorage.length).toBe(1);
  });

  it("makes no completion call without a picked profile", async () => {
    const calls = mockApi(() => Response.json({}));
    await finishLesson();
    expect(screen.getByText(t("pixelLesson.lessonDone"))).toBeTruthy();
    expect(posts(calls)).toHaveLength(0);
  });
});
