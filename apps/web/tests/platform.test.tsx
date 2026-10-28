// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "../app/page";
import { SiteHeader } from "../components/site-shell";
import { KnowledgeIndex, KnowledgeUnit } from "../components/platform/knowledge";
import { Lab } from "../components/platform/lab";
import { StageCards, StageDetail } from "../components/platform/learn";
import { Passport } from "../components/platform/passport";
import { StoryGate } from "../components/platform/not-ready";
import { setDemoAccount } from "../lib/demo-account";
import { t } from "../lib/i18n";
import { CORE_PATH, storyReady, unitReady } from "../lib/learning-path";
import { storyHref, v2Get } from "../lib/v2-api";

vi.mock("next/navigation", () => ({ usePathname: () => "/learn", useRouter: () => ({ push: vi.fn() }) }));
vi.mock("next/image", () => ({ default: () => null }));

const paths = {
  release_id: "r1",
  stages: [
    { stage: 1, title_th: "Stage one", summary_th: "Stage one summary", objectives: [
      { id: "OBJ-1-01", title_th: "Objective one", dimension: "discovery", unit_ids: ["KB-TM-ELEMENT-001", "KB-1", "KB-HIDDEN"], story_ids: ["gs-a-postpartum-warning", "gs-b-thai-recovery", "PP-001", "missing-story"] },
      { id: "OBJ-1-02", title_th: "Objective two", dimension: "decision", unit_ids: ["KB-1"], story_ids: [] },
    ] },
    { stage: 2, title_th: "Stage two", summary_th: "Two", objectives: [] },
  ],
};
const units = { release_id: "r1", items: [
  { id: "KB-TM-ELEMENT-001", version: "1", title_th: "Core unit", care_stage: "preconception", domain: 1, has_lens: true },
  { id: "KB-1", version: "1", title_th: "Unit one", care_stage: "postpartum", domain: 3, has_lens: true },
  { id: "KB-2", version: "1", title_th: "Unit two", care_stage: "antenatal", domain: 1, has_lens: false },
] };
const unitDetail = {
  id: "KB-1", version: "1", title_th: "Unit one", care_stage: "postpartum", domain: 3,
  evidence_status: "synthesis", review_basis: "knowledge_base_2026", reviewed_on: null,
  claims: [{ id: "C1", type: "safety", text_th: "Claim text", sources: [{ source_id: "S07", title: "Source seven", url: "https://example.org/s7", locator: "section 4.2" }] }],
  lens: { wisdom_th: "Wisdom body", safety_th: "Safety body", rights_th: "Rights body" },
  contraindications_th: ["Avoid X"], escalation_th: "Escalate now",
};
const stories = [
  ...["thai-milk-family", "thai-birth-conversation", "thai-elements-family", "golden-first-night"].map((id) =>
    ({ id, title_th: id, description_th: "d", mode: "solo", chapters_th: [] })),
  { id: "first-night", title_th: "Legacy story", description_th: "d", mode: "coop", chapters_th: ["a", "b"] },
  { id: "gs-b-thai-recovery", title_th: "GS-B title", description_th: "d", mode: "coop", chapters_th: [] },
  { id: "gs-a-postpartum-warning", title_th: "GS-A title", description_th: "d", mode: "coop", chapters_th: [] },
];
const cases = { items: [{ case_id: "PP-001", title_th: "Solo case" }, { case_id: "DEV-001", title_th: "Fixture" }] };
const accounts = { items: [
  { id: "acc-l1", org_id: "o", display_name_th: "Learner One", role: "learner" },
  { id: "acc-e1", org_id: "o", display_name_th: "Educator One", role: "educator" },
] };
const sources = { items: [{ id: "S01", kind: "kb_source", title: "KB source", publisher: "Pub", year: 2024, url: "https://example.org/s1", rights_status: "public_web" },
  { id: "M01", kind: "catalog", title: "Catalog book", publisher: null, year: null, url: null, rights_status: "metadata_only" }] };
const attempt = (o: Partial<Record<string, unknown>> = {}) => ({
  room_id: "r", story_id: "gs-a-postpartum-warning", title_th: "Attempt title", finished_at: "2026-10-20T10:00:00Z",
  safety_status: "SAFETY_MET", score_total: 80, objective_ids: ["OBJ-1-01"], strong: false, ...o,
});

type Routes = Record<string, unknown | ((req: Request) => Response)>;
let calls: Request[] = [];
function mockApi(routes: Routes) {
  calls = [];
  vi.stubGlobal("fetch", vi.fn(async (input: string | Request, init?: RequestInit) => {
    const req = input instanceof Request ? input : new Request(input, init);
    calls.push(req);
    const path = new URL(req.url).pathname.replace(/^\/v1/, "");
    if (!(path in routes)) return Response.json({ error: { code: "NOT_FOUND", message: "x", details: {} } }, { status: 404 });
    const r = routes[path];
    return typeof r === "function" ? (r as (q: Request) => Response)(req) : Response.json(r);
  }));
}
const base: Routes = {
  "/learning-paths": paths, "/knowledge/units": units, "/family/stories": stories, "/cases": cases,
  "/demo/accounts": accounts, "/knowledge/sources": sources,
};

beforeEach(() => { localStorage.clear(); });
afterEach(() => vi.unstubAllEnvs());
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });

describe("v2 api module", () => {
  it("sends X-Demo-Account only when a profile is picked and maps the error envelope", async () => {
    mockApi({ "/ping": { ok: true }, "/boom": () => Response.json({ error: { code: "ORG_FORBIDDEN" } }, { status: 403 }) });
    await v2Get("/ping");
    expect(calls[0]?.headers.get("X-Demo-Account")).toBeNull();
    setDemoAccount("acc-l1");
    await v2Get("/ping");
    expect(calls[1]?.headers.get("X-Demo-Account")).toBe("acc-l1");
    await expect(v2Get("/boom")).rejects.toMatchObject({ code: "ORG_FORBIDDEN", status: 403 });
  });

  it("routes legacy stories to their old pages and everything else to the room page", () => {
    expect(storyHref("golden-first-night")).toBe("/golden");
    expect(storyHref("gs-a-postpartum-warning")).toBe("/simulate/gs-a-postpartum-warning");
  });
});

describe("navigation", () => {
  it("offers the five family destinations plus a discreet institution link, and no legacy items", () => {
    render(<SiteHeader />);
    const nav = screen.getByRole("navigation", { name: t("nav.label") });
    const hrefs = within(nav).getAllByRole("link").map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual(["/", "/learn", "/lab", "/passport", "/knowledge", "/institution"]);
    expect(within(nav).getByRole("link", { name: t("platform.nav.learn") }).getAttribute("aria-current")).toBe("page");
    for (const legacy of ["/family", "/golden", "/replay", "/instructor", "/bridge"]) expect(hrefs).not.toContain(legacy);
  });
});

describe("Home", () => {
  it("shows the four pillars, featured golden scenarios in order, and the labeled learner-only profile picker", async () => {
    mockApi(base);
    render(<HomePage />);
    for (let n = 1; n <= 4; n++) expect(screen.getByRole("heading", { name: t(`platform.home.pillar${n}Title`) })).toBeTruthy();
    const featured = await screen.findByRole("heading", { name: t("platform.home.goldenTitle") });
    const section = featured.closest("section") as HTMLElement;
    expect(within(section).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["GS-A title"]); // GS-B is not in the ready set
    expect(within(section).getAllByRole("link").map((a) => a.getAttribute("href"))).toEqual(["/simulate/gs-a-postpartum-warning"]);
    expect(await screen.findByRole("button", { name: /Learner One/ })).toBeTruthy();
    expect(screen.queryByText("Educator One")).toBeNull();
    expect(screen.getAllByText(t("platform.common.demoBadge")).length).toBeGreaterThan(0);
    expect(screen.getByText(t("platform.home.continuePick"))).toBeTruthy();
  });

  it("hides the golden section when the API does not list them and survives a failing accounts call", async () => {
    mockApi({ ...base, "/family/stories": [stories.find((s) => s.id === "first-night")], "/demo/accounts": () => Response.json({ error: { code: "X" } }, { status: 500 }) });
    render(<HomePage />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: t("platform.home.goldenTitle") })).toBeNull();
    expect(screen.getByRole("link", { name: new RegExp(t("platform.home.ctaStart")) })).toBeTruthy();
  });

  it("picks an account, persists it, and shows the latest finished attempt", async () => {
    mockApi({ ...base, "/passport/acc-l1": { account: { id: "acc-l1", display_name_th: "Learner One" }, attempts: [
      attempt({ title_th: "Older", finished_at: "2026-10-01T00:00:00Z" }), attempt({ title_th: "Newest" }), attempt({ title_th: "Unfinished", finished_at: null })] } });
    render(<HomePage />);
    fireEvent.click(await screen.findByRole("button", { name: /Learner One/ }));
    expect(localStorage.getItem("sim-tamy-demo-account")).toBe("acc-l1");
    expect(await screen.findByText("Newest")).toBeTruthy();
    expect(screen.queryByText("Unfinished")).toBeNull();
    expect(calls.some((c) => new URL(c.url).pathname === "/v1/passport/acc-l1" && c.headers.get("X-Demo-Account") === "acc-l1")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: t("platform.profile.clear") }));
    expect(localStorage.getItem("sim-tamy-demo-account")).toBeNull();
    expect(await screen.findByText(t("platform.home.continuePick"))).toBeTruthy();
  });

  it("points to the Lab when the picked account has no finished attempt", async () => {
    setDemoAccount("acc-l1");
    mockApi({ ...base, "/passport/acc-l1": { account: { id: "acc-l1", display_name_th: "L" }, attempts: [] } });
    render(<HomePage />);
    expect(await screen.findByText(t("platform.home.continueNone"))).toBeTruthy();
  });
});

describe("Learning Journey", () => {
  it("lists the stage cards with links", async () => {
    mockApi(base);
    render(<StageCards />);
    expect(await screen.findByRole("heading", { name: "Stage one" })).toBeTruthy();
    const links = screen.getAllByRole("link", { name: new RegExp(t("platform.learn.openStage")) });
    expect(links.map((a) => a.getAttribute("href"))).toEqual(["/learn/1", "/learn/2"]);
  });

  it("fills the house palm-leaf book from the passport's completed lessons", async () => {
    setDemoAccount("acc-l1");
    mockApi({ ...base, "/passport/acc-l1": { account: { id: "acc-l1", display_name_th: "L" }, attempts: [],
      lessons: [{ unit_id: "KB-TM-ELEMENT-001", completed_at: "2026-10-01T00:00:00Z" }] } });
    render(<StageCards />);
    const book = (await screen.findAllByText(t("pixelHouse.items.book"), { exact: false }))[0]!.closest("li") as HTMLElement;
    expect(book.textContent).toContain(t("pixelHouse.itemState.have"));
  });

  it("shows retry on failure", async () => {
    mockApi({});
    render(<StageCards />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByRole("button", { name: t("platform.common.retry") })).toBeTruthy();
  });

  it("deduplicates supplementary reading, prioritizes the stage core and hides unavailable API items", async () => {
    mockApi(base);
    render(<StageDetail stage="1" />);
    expect(await screen.findByRole("link", { name: "Core unit" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "thai-elements-family" }).getAttribute("href")).toBe("/simulate/thai-elements-family");
    // not-ready items stay visible but greyed out and cannot be opened
    expect(screen.queryByRole("link", { name: "Unit one" })).toBeNull();
    expect(screen.getAllByText("Unit one")).toHaveLength(1);
    expect(screen.getByText("Unit one").closest("[aria-disabled='true']")).not.toBeNull();
    expect(screen.getByRole("link", { name: "GS-A title" }).getAttribute("href")).toBe("/simulate/gs-a-postpartum-warning"); // ready
    expect(screen.queryByRole("link", { name: "GS-B title" })).toBeNull();
    expect(screen.getByText("GS-B title").closest("[aria-disabled='true']")).not.toBeNull();
    expect(screen.queryByText("KB-HIDDEN")).toBeNull();
    expect(screen.queryByText(/missing-story/)).toBeNull();
    fireEvent.click(screen.getByText(t("platform.learn.objectives")));
    expect(screen.getAllByText(t("platform.learn.progressPick"))).toHaveLength(2);
    expect(document.body.textContent).not.toMatch(/นาที|ชั่วโมง/);
  });

  it("does not link a curated unit or story that the API omits", async () => {
    mockApi({ ...base, "/knowledge/units": { items: [] }, "/family/stories": [] });
    render(<StageDetail stage="1" />);
    expect(await screen.findByText(t("platform.learn.noUnits"))).toBeTruthy();
    expect(await screen.findByText(t("platform.learn.noScenarios"))).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Core unit" })).toBeNull();
    expect(screen.queryByRole("link", { name: "thai-elements-family" })).toBeNull();
  });

  it("counts an objective as done only from finished attempts", async () => {
    setDemoAccount("acc-l1");
    mockApi({ ...base, "/passport/acc-l1": { account: { id: "acc-l1", display_name_th: "L" }, attempts: [
      attempt(), attempt({ room_id: "r2", finished_at: null }), attempt({ room_id: "r3", objective_ids: ["OBJ-1-02"], finished_at: null })] } });
    render(<StageDetail stage="1" />);
    await screen.findByRole("heading", { name: "Stage one" });
    fireEvent.click(screen.getByText(t("platform.learn.objectives")));
    const one = (await screen.findByRole("heading", { name: "Objective one" })).closest("li") as HTMLElement;
    const two = screen.getByRole("heading", { name: "Objective two" }).closest("li") as HTMLElement;
    await waitFor(() => expect(within(one).getByText(new RegExp(`${t("platform.learn.progressDone")} 1`))).toBeTruthy());
    expect(within(two).getByText(t("platform.learn.progressNone"))).toBeTruthy();
  });

  it("says so for an unknown stage", async () => {
    mockApi(base);
    render(<StageDetail stage="9" />);
    expect(await screen.findByText(t("platform.learn.notFound"))).toBeTruthy();
  });
});

describe("Simulation Lab", () => {
  it("shows the four ready stories in stage order and greys out the rest inside a collapsed section", async () => {
    mockApi(base);
    render(<Lab />);
    const featured = (await screen.findByRole("heading", { name: t("platform.lab.featured") })).closest("section") as HTMLElement;
    expect(within(featured).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "thai-elements-family", "thai-birth-conversation", "GS-A title", "thai-milk-family"]);
    for (const title of ["Legacy story", "golden-first-night", "GS-B title", t("platform.lab.soloTitle")]) {
      expect(screen.getByRole("heading", { name: title }).closest("details")?.open).toBe(false);
    }
    fireEvent.click(screen.getByText(t("platform.lab.otherStories")));
    for (const title of ["Legacy story", "golden-first-night", "GS-B title"]) {
      const card = screen.getByRole("heading", { name: title }).closest("li") as HTMLElement;
      expect(within(card).queryByRole("link")).toBeNull();
      expect(within(card).getByText(t("platform.notReady"))).toBeTruthy();
    }
    fireEvent.click(screen.getByText(t("platform.lab.moreModules")));
    expect(screen.queryByText("Fixture")).toBeNull();
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href"));
    for (const h of ["/lab/solo", "/replay", "/instructor", "/validation"]) expect(hrefs).toContain(h);
    for (const h of ["/family", "/golden", "/simulate/gs-b-thai-recovery"]) expect(hrefs).not.toContain(h);
  });

  it("hides unavailable core stories without promoting archived stories", async () => {
    mockApi({ ...base, "/family/stories": [stories.find((s) => s.id === "first-night")] });
    render(<Lab />);
    await screen.findByText(t("platform.lab.otherStories"));
    expect(screen.queryByRole("heading", { name: t("platform.lab.featured") })).toBeNull();
    expect(screen.getByRole("heading", { name: "Legacy story" }).closest("details")?.open).toBe(false);
  });
});

describe("Learning Passport", () => {
  it("asks for a profile first and labels the page as demo", async () => {
    mockApi(base);
    render(<Passport />);
    expect(screen.getByText(t("platform.passport.pickFirst"))).toBeTruthy();
    expect(screen.getAllByText(t("platform.common.demoBadge")).length).toBeGreaterThan(0);
    expect(screen.getByText(t("platform.common.demoNote"))).toBeTruthy();
    expect(await screen.findByRole("button", { name: /Learner One/ })).toBeTruthy();
  });

  it("shows an empty state linking to the Lab", async () => {
    setDemoAccount("acc-l1");
    mockApi({ ...base, "/passport/acc-l1": { account: { id: "acc-l1", display_name_th: "L" }, attempts: [] } });
    render(<Passport />);
    expect(await screen.findByText(t("platform.passport.empty"))).toBeTruthy();
    expect(screen.getByRole("link", { name: new RegExp(t("platform.passport.emptyCta")) }).getAttribute("href")).toBe("/lab");
  });

  it("shows safety per attempt, never pass wording when SAFETY_NOT_MET, scores only when present, and badges as topics", async () => {
    setDemoAccount("acc-l1");
    mockApi({ ...base, "/passport/acc-l1": { account: { id: "acc-l1", display_name_th: "L" }, attempts: [
      attempt({ room_id: "a", title_th: "Unsafe run", safety_status: "SAFETY_NOT_MET", score_total: 95 }),
      attempt({ room_id: "b", title_th: "Safe run", score_total: null, finished_at: "2026-10-19T10:00:00Z" }),
      attempt({ room_id: "c", title_th: "Open run", finished_at: null }),
    ] } });
    render(<Passport />);
    const unsafe = (await screen.findByRole("heading", { name: "Unsafe run" })).closest("li") as HTMLElement;
    const safe = screen.getByRole("heading", { name: "Safe run" }).closest("li") as HTMLElement;
    expect(screen.queryByRole("heading", { name: "Open run" })).toBeNull();
    expect(within(unsafe).getByRole("alert").textContent).toContain(t("report.safetyNotMet"));
    expect(unsafe.textContent).not.toContain(t("report.safetyMet"));
    expect(unsafe.textContent).not.toMatch(/ผ่าน(?!การ)/);
    expect(unsafe.textContent).not.toContain("pass");
    expect(within(unsafe).getByText(/95/)).toBeTruthy();
    expect(within(safe).getByRole("status").textContent).toContain(t("report.safetyMet"));
    expect(within(safe).queryByText(new RegExp(t("platform.passport.score")))).toBeNull();
    expect(screen.queryByText(/เฉลี่ย\s*\d|average/i)).toBeNull();
    const badges = screen.getByRole("heading", { name: t("platform.passport.badges") }).closest("section") as HTMLElement;
    expect(within(badges).getByText(/Objective one/)).toBeTruthy();
    expect(within(badges).getByText(t("platform.passport.badgeTimes").replace("{n}", "2"))).toBeTruthy();
    expect(badges.textContent).not.toMatch(/ใบรับรอง(?!หรือ)/);
  });
});

describe("Knowledge & Sources", () => {
  it("groups units by care stage in order and lists the source registry with rights status", async () => {
    mockApi(base);
    render(<KnowledgeIndex />);
    await screen.findByRole("link", { name: "Core unit" });
    const headings = screen.getAllByRole("heading", { level: 2 });
    const texts = headings.map((h) => h.textContent);
    expect(texts.indexOf(t("platform.knowledge.stage_pregnancy"))).toBeLessThan(texts.indexOf(t("platform.knowledge.stage_postpartum")));
    expect(screen.getByRole("link", { name: "Core unit" }).getAttribute("href")).toBe("/knowledge/KB-TM-ELEMENT-001");
    expect(screen.queryByRole("link", { name: "Unit one" })).toBeNull(); // listed but not ready
    expect(screen.getByText("Unit one").closest("[aria-disabled='true']")).not.toBeNull();
    expect(screen.getAllByText(t("platform.knowledge.hasLens"), { exact: false })).toHaveLength(2);
    expect(screen.getByText(t("platform.knowledge.registry")).closest("details")?.open).toBe(false);
    fireEvent.click(screen.getByText(t("platform.knowledge.registry")));
    expect(await screen.findByText("KB source", { exact: false })).toBeTruthy();
    expect(screen.getByText(new RegExp(t("platform.knowledge.rights_metadata_only")))).toBeTruthy();
    const ext = screen.getByRole("link", { name: new RegExp(t("platform.knowledge.sourceLink")) });
    expect(ext.getAttribute("rel")).toContain("noopener");
  });

  it("renders claims with sources, the three-part Thai Wisdom Lens, and provenance that never claims expert review", async () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_ALL_CONTENT", "true");
    mockApi({ ...base, "/knowledge/units/KB-1": unitDetail });
    render(<KnowledgeUnit id="KB-1" />);
    expect(await screen.findByText("Claim text")).toBeTruthy();
    expect(screen.getByText(/S07/)).toBeTruthy();
    expect(screen.getByText(/section 4\.2/)).toBeTruthy();
    expect(screen.getByRole("link", { name: new RegExp(t("platform.knowledge.sourceLink")) }).getAttribute("href")).toBe("https://example.org/s7");
    for (const key of ["lensWisdom", "lensSafety", "lensRights"]) expect(screen.getByRole("heading", { name: t(`platform.knowledge.${key}`) })).toBeTruthy();
    for (const body of ["Wisdom body", "Safety body", "Rights body", "Avoid X", "Escalate now"]) expect(screen.getByText(body)).toBeTruthy();
    expect(screen.getByText(t("platform.knowledge.provenance_knowledge_base_2026"), { exact: false })).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/ผ่านการตรวจโดยผู้เชี่ยวชาญ/);
  });

  it("omits the lens, contraindications and escalation when absent, and handles 404", async () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_ALL_CONTENT", "true");
    mockApi({ ...base, "/knowledge/units/KB-1": { ...unitDetail, lens: null, contraindications_th: [], escalation_th: null } });
    const { unmount } = render(<KnowledgeUnit id="KB-1" />);
    await screen.findByText("Claim text");
    expect(screen.queryByText(t("platform.knowledge.lensTitle"))).toBeNull();
    expect(screen.queryByText(t("platform.knowledge.contraindications"))).toBeNull();
    expect(screen.queryByText(t("platform.knowledge.escalation"))).toBeNull();
    unmount();
    render(<KnowledgeUnit id="nope" />);
    expect(await screen.findByText(t("platform.knowledge.notFound"))).toBeTruthy();
  });
});

it("shows loading and lets a learner retry failed house progress without losing attempts", async () => {
  setDemoAccount("acc-l1");
  let resolvePassport!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(async (input: string | Request) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/passport/acc-l1")) return new Promise<Response>((resolve) => { resolvePassport = resolve; });
    return Response.json(paths);
  }));
  render(<StageCards />);
  await screen.findByText("Stage one");
  expect(screen.queryByText(t("pixelHouse.itemState.table"), { exact: false })).toBeNull();
  expect(screen.getByRole("status").textContent).toBe(t("platform.common.loading"));
  resolvePassport(Response.json({ error: { code: "X" } }, { status: 500 }));
  const alert = await screen.findByRole("alert");
  expect(within(alert).getByText(t("platform.common.loadError"))).toBeTruthy();
  expect(screen.queryByText(t("pixelHouse.itemState.table"), { exact: false })).toBeNull();
  mockApi({ ...base, "/passport/acc-l1": { account: { id: "acc-l1", display_name_th: "Learner One" },
    attempts: [attempt({ story_id: "thai-elements-family" })] } });
  fireEvent.click(within(alert).getByRole("button", { name: t("platform.common.retry") }));
  expect(await screen.findByText(t("pixelHouse.itemState.have"), { exact: false })).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
});

describe("ready gating", () => {
  it("opens only the curated unit and scenario per stage unless SHOW_ALL is set", () => {
    expect(CORE_PATH.map((s) => [s.units.length, s.stories.length])).toEqual([[1, 1], [1, 1], [1, 1], [1, 1]]);
    expect(unitReady("KB-TM-ELEMENT-001")).toBe(true);
    expect(unitReady("KB-ANC-PLAN-001")).toBe(false);
    expect(storyReady("gs-a-postpartum-warning")).toBe(true);
    expect(storyReady("gs-b-thai-recovery")).toBe(false);
    vi.stubEnv("NEXT_PUBLIC_SHOW_ALL_CONTENT", "true");
    expect(unitReady("KB-ANC-PLAN-001")).toBe(true);
    expect(storyReady("gs-b-thai-recovery")).toBe(true);
  });

  it("shows a notice instead of a unit that is not ready and does not fetch it", () => {
    mockApi(base);
    render(<KnowledgeUnit id="KB-1" />);
    expect(screen.getByRole("heading", { name: t("platform.notReadyTitle") })).toBeTruthy();
    expect(calls.map((c) => c.url).join()).not.toContain("KB-1");
  });

  it("shows a notice instead of a story page that is not ready", () => {
    render(<StoryGate id="gs-b-thai-recovery"><p>room</p></StoryGate>);
    expect(screen.getByRole("heading", { name: t("platform.notReadyTitle") })).toBeTruthy();
    expect(screen.queryByText("room")).toBeNull();
  });

  it("renders a ready story page", () => {
    render(<StoryGate id="thai-elements-family"><p>room</p></StoryGate>);
    expect(screen.getByText("room")).toBeTruthy();
  });
});
