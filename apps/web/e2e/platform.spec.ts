import { expect, test, type Page } from "@playwright/test";

import { t } from "../lib/i18n";

// The 2.0 endpoints are not in docs/openapi.yaml yet, so Prism cannot serve them: mock every /v1 call here.
// Re-point these at the real API (or Prism) once streams A, B and C have merged and the contract is regenerated.
const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "GET, OPTIONS" };
const data: Record<string, unknown> = {
  "/v1/learning-paths": { release_id: "r1", stages: [1, 2, 3, 4].map((n) => ({ stage: n, title_th: `Stage ${n}`, summary_th: "Summary", objectives: [
    { id: `OBJ-${n}-01`, title_th: `Objective ${n}`, dimension: "discovery", unit_ids: ["KB-1"], story_ids: ["gs-a-postpartum-warning"] }] })) },
  "/v1/knowledge/units": { release_id: "r1", items: [{ id: "KB-1", version: "1", title_th: "Unit one", care_stage: "postpartum", domain: 3, has_lens: true }] },
  "/v1/knowledge/units/KB-1": {
    id: "KB-1", version: "1", title_th: "Unit one", care_stage: "postpartum", domain: 3, evidence_status: "synthesis", review_basis: "knowledge_base_2026",
    reviewed_on: null, claims: [{ id: "C1", type: "safety", text_th: "Claim", sources: [{ source_id: "S07", title: "Source", url: "https://example.org", locator: "4.2" }] }],
    lens: { wisdom_th: "W", safety_th: "S", rights_th: "R" }, contraindications_th: [], escalation_th: "Escalate",
  },
  "/v1/knowledge/sources": { items: [{ id: "S07", kind: "kb_source", title: "Source", publisher: null, year: null, url: "https://example.org", rights_status: "public_web" }] },
  "/v1/demo/accounts": { items: [{ id: "acc-l1", org_id: "o", display_name_th: "Learner One", role: "learner" }] },
  "/v1/passport/acc-l1": { account: { id: "acc-l1", display_name_th: "Learner One" }, attempts: [
    { room_id: "r1", story_id: "gs-a-postpartum-warning", title_th: "Finished run", finished_at: "2026-10-20T10:00:00Z", safety_status: "SAFETY_NOT_MET", score_total: 70, objective_ids: ["OBJ-1-01"] }] },
  "/v1/family/stories": ["first-night", "thai-milk-family", "gs-b-thai-recovery", "thai-birth-conversation", "gs-a-postpartum-warning", "thai-elements-family", "golden-first-night"]
    .map((id) => ({ id, title_th: id, description_th: "d", mode: "coop", chapters_th: [] })),
  "/v1/cases": { items: [] },
};

async function mock(page: Page, account?: string) {
  if (account) await page.addInitScript((id) => localStorage.setItem("sim-tamy-demo-account", id), account);
  await page.route("**/v1/**", (route) => {
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: cors });
    const body = data[new URL(route.request().url()).pathname];
    return body === undefined
      ? route.fulfill({ status: 404, headers: cors, json: { error: { code: "NOT_FOUND", message: "x", details: {} } } })
      : route.fulfill({ status: 200, headers: cors, json: body });
  });
}

async function expectNoSeriousViolations(page: Page) {
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(async () => {
    const axe = (globalThis as unknown as { axe: { run: () => Promise<{ violations: Array<{ id: string; impact: string | null; nodes: Array<{ target: unknown }> }> }> } }).axe;
    return (await axe.run()).violations.filter((v) => v.impact === "critical" || v.impact === "serious")
      .map((v) => ({ id: v.id, impact: v.impact, targets: v.nodes.map((n) => n.target) }));
  });
  expect(violations, JSON.stringify(violations)).toEqual([]);
}

const pages: Array<[string, string, string]> = [
  ["Home", "/", t("platform.home.stagesTitle")],
  ["Learn", "/learn", "Stage 1"],
  ["Learn stage", "/learn/1", t("platform.learn.units")],
  ["Lab", "/lab", t("platform.lab.featured")],
  ["Passport", "/passport", "Finished run"],
  ["Knowledge", "/knowledge", "Unit one"],
  ["Knowledge unit", "/knowledge/KB-1", t("platform.knowledge.lensTitle")],
];

for (const [name, path, ready] of pages) {
  test(`${name} fits 360px, has 44px controls and no serious axe violations`, async ({ page }) => {
    await mock(page, "acc-l1");
    await page.goto(path);
    await expect(page.getByRole("heading", { name: ready }).first()).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const small = await page.evaluate(() => [...document.querySelectorAll("main a, main button, main summary, header a, header button")]
      .map((el) => ({ el, r: el.getBoundingClientRect(), inline: getComputedStyle(el).display === "inline" }))
      .filter(({ r, inline }) => r.width > 0 && !inline && (r.height < 43.5 || r.width < 43.5))
      .map(({ el }) => `${el.tagName} ${el.textContent?.slice(0, 30)}`));
    expect(small).toEqual([]);
    await expectNoSeriousViolations(page);
  });
}

test("top navigation shows the five family destinations and the institution link, not legacy routes", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await page.getByRole("button", { name: t("platform.nav.openMenu") }).click();
  const nav = page.getByRole("navigation", { name: t("nav.label") });
  for (const key of ["home", "learn", "lab", "passport", "knowledge", "institution"]) {
    await expect(nav.getByRole("link", { name: t(`platform.nav.${key}`) })).toBeVisible();
  }
  await expect(nav.locator('a[href="/family"], a[href="/replay"], a[href="/instructor"]')).toHaveCount(0);
});

test("the Passport never shows pass wording for a SAFETY_NOT_MET attempt", async ({ page }) => {
  await mock(page, "acc-l1");
  await page.goto("/passport");
  await expect(page.getByText(t("report.safetyNotMet"))).toBeVisible();
  await expect(page.getByText(t("report.safetyMet"), { exact: true })).toHaveCount(0);
});

test("disclosures open by keyboard and preserve archived routes and objective progress", async ({ page }) => {
  await mock(page, "acc-l1");
  await page.goto("/learn/1");
  const progress = page.locator("summary", { hasText: t("platform.learn.objectives") });
  await expect(page.getByRole("heading", { name: "Objective 1" })).not.toBeVisible();
  await progress.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Objective 1" })).toBeVisible();
  await expect(page.getByText(`${t("platform.learn.progressDone")} 1`, { exact: false })).toBeVisible();
  await page.goto("/lab");
  const core = page.getByRole("region", { name: t("platform.lab.featured") });
  await expect(core.getByRole("heading", { level: 3 })).toHaveText([
    "thai-elements-family", "thai-birth-conversation", "gs-a-postpartum-warning", "thai-milk-family"]);
  await expect(page.getByRole("heading", { name: "first-night", exact: true })).not.toBeVisible();
  await page.locator("summary", { hasText: t("platform.lab.otherStories") }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator('main a[href="/family"]')).toBeVisible();
  const tools = page.locator("summary", { hasText: t("platform.lab.moreModules") });
  await expect(page.locator('main a[href="/lab/solo"]')).not.toBeVisible();
  await tools.focus();
  await page.keyboard.press("Space");
  await expect(page.locator('main a[href="/lab/solo"]')).toBeVisible();
  await expectNoSeriousViolations(page);
  await page.goto("/knowledge");
  const source = page.getByRole("link", { name: new RegExp(t("platform.knowledge.sourceLink")) });
  await expect(source).not.toBeVisible();
  await page.locator("summary", { hasText: t("platform.knowledge.registry") }).focus();
  await page.keyboard.press("Enter");
  await expect(source).toBeVisible();
});

for (const width of [360, 844, 1440]) {
  test(`four-stage entry and navigation at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await mock(page);
    await page.goto("/");
    const stages = page.getByRole("region", { name: t("platform.home.stagesTitle") });
    await expect(stages.getByRole("heading", { level: 3 })).toHaveText(["Stage 1", "Stage 2", "Stage 3", "Stage 4"]);
    await page.getByRole("link", { name: t("platform.home.ctaStart"), exact: true }).click();
    await expect(page).toHaveURL(/#stages$/);
    await expect(stages.getByRole("heading", { level: 2 })).toBeInViewport();
    if (width < 1200) {
      const toggle = page.getByRole("button", { name: t("platform.nav.openMenu") });
      const menu = page.getByRole("navigation", { name: t("nav.label") });
      await expect(menu).toBeHidden();
      await toggle.focus();
      await page.keyboard.press("Enter");
      await expect(toggle).toHaveAttribute("aria-expanded", "true");
      await menu.getByRole("link", { name: t("platform.nav.learn"), exact: true }).focus();
      await page.keyboard.press("Escape");
      await expect(toggle).toBeFocused();
      await expect(menu).toBeHidden();
      await toggle.click();
      await menu.getByRole("link", { name: t("platform.nav.learn"), exact: true }).click();
      await expect(page).toHaveURL(/\/learn$/);
      await expect(menu).toBeHidden();
      await page.goto("/");
    }
    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expectNoSeriousViolations(page);
    await page.screenshot({ path: testInfo.outputPath("four-stages.png"), fullPage: true });
    await page.evaluate(() => { document.documentElement.style.fontSize = "32px"; });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
