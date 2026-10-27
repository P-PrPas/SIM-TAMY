import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { t } from "../lib/i18n";

// C02: the stage golden path against the local API + PostgreSQL with the mock LLM.
// Run with `make test-e2e-demo`. Every wait is a web-first assertion or a response/poll, never a sleep.
const apiUrl = "http://127.0.0.1:8000";

function goldenQuestions(): string[] {
  // The Content/Golden suite owns the learner utterances; the browser reuses them.
  const file = readFileSync(resolve(__dirname, "../../../eval/golden/pp001/T11.yaml"), "utf8");
  return [...file.matchAll(/^\s*- \{say: "([^"]+)"/gm)].map((match) => match[1]!);
}

async function requireMockApi(page: Page) {
  // A reused server on :8000 must be the mock one; a real provider is never reached by accident.
  const health = await page.request.get(`${apiUrl}/health`);
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toMatchObject({ db: "ok", llm_provider: "mock" });
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

// C03: no serious/critical axe violation, no horizontal scroll and no visible control under 44x44 CSS px
// (touch-target guidance; WCAG 2.2 AA minimum is 24) on the page as it currently renders.
async function audit(page: Page) {
  await noOverflow(page);
  // Buttons fade colors; axe must see the settled state the user ends up with, not a mid-fade blend.
  await page.evaluate(() => Promise.all(document.getAnimations()
    .filter((animation) => animation instanceof CSSTransition).map((animation) => animation.finished.catch(() => undefined))));
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const found = await page.evaluate(async () => {
    const axe = (globalThis as unknown as { axe: { run: () => Promise<{ violations: Array<{ id: string; impact: string | null; nodes: Array<{ target: unknown }> }> }> } }).axe;
    const serious = (await axe.run()).violations.filter((v) => v.impact === "serious" || v.impact === "critical")
      .map((v) => `${v.id}: ${JSON.stringify(v.nodes.map((n) => n.target))}`);
    const small = [...document.querySelectorAll<HTMLElement>("button, a[href]:not(.sr-only), summary, input, select, textarea, [role=tab], [role=radio]")]
      .filter((el) => {
        const box = el.getBoundingClientRect();
        // radios/checkboxes are often visually hidden behind a larger label
        const target = el.closest("label")?.getBoundingClientRect() ?? box;
        return box.width > 0 && getComputedStyle(el).visibility !== "hidden" && (target.width < 44 || target.height < 44);
      }).map((el) => el.outerHTML.slice(0, 80));
    return { serious, small };
  });
  expect(found, JSON.stringify(found)).toEqual({ serious: [], small: [] });
}

async function ask(page: Page, text: string) {
  await page.getByRole("textbox", { name: t("chat.messageLabel") }).fill(text);
  const turn = page.waitForResponse((item) =>
    item.request().method() === "POST" && item.status() === 200 && /\/v1\/sessions\/[^/]+\/turns$/.test(item.url()));
  await page.getByRole("button", { name: t("chat.send") }).click();
  const body = JSON.stringify(await (await turn).json());
  expect(body).not.toMatch(/revealed_fact_ids|risk_state|"actions"|"score"|safety_status/);
  await expect(page.getByText(t("chat.typing"))).toHaveCount(0);
  await expect(page.getByText(text, { exact: true })).toBeVisible();
}

test("solo: ask, decide, safety-gated report with evidence, then branch and example replay", async ({ page }) => {
  await requireMockApi(page);
  await page.goto("/");
  await page.locator("#case").selectOption("PP-001");
  await page.locator("#variant").selectOption("A");
  await page.getByRole("textbox", { name: t("join.nickname") }).fill("DEMO-solo");
  await page.getByRole("button", { name: t("join.start") }).click();
  await expect(page).toHaveURL(/\/briefing$/);
  await expect(page.getByRole("link", { name: t("briefing.begin") })).toBeVisible();
  await audit(page);
  await page.getByRole("link", { name: t("briefing.begin") }).click();
  await expect(page).toHaveURL(/\/chat$/);

  // Two questions that reveal facts (blood loss, dizziness), then the Decision Panel.
  for (const question of goldenQuestions().slice(4, 6)) await ask(page, question);
  await audit(page);
  await page.getByRole("button", { name: t("chat.decide") }).click();
  await expect(page).toHaveURL(/\/decision$/);
  await expect(page.locator('input[name="decision"]').first()).toBeVisible();
  await audit(page);
  // A dev build can hydrate after the first check and reset the form; retry the pair until it holds.
  await expect(async () => {
    await page.locator('input[name="decision"][value="refer"]').check();
    await page.getByRole("button", { name: t("decision.review") }).click();
    await expect(page.getByText(t("decision.irreversible"))).toBeVisible({ timeout: 2_000 });
  }).toPass();
  await page.getByRole("button", { name: t("decision.confirm") }).click();
  await expect(page).toHaveURL(/\/closing$/);
  await expect(page.getByRole("button", { name: t("closing.complete") })).toBeVisible();
  await audit(page);
  await page.getByRole("button", { name: t("closing.complete") }).click();

  await expect(page).toHaveURL(/\/report$/);
  await expect(page.getByRole("heading", { name: t("report.title") })).toBeVisible();
  // Critical Safety is a gate: the gate is always shown and never carries pass wording.
  const gate = page.getByText(t("report.safetyMet")).or(page.getByText(t("report.safetyNotMet")));
  await expect(gate).toBeVisible();
  await expect(page.getByText(t("report.score"), { exact: true })).toBeVisible();
  await audit(page);
  expect(await page.locator("main").innerText()).not.toMatch(/สอบผ่าน|ผ่านเกณฑ์|ผ่านการประเมิน|\bpass(ed)?\b/i);

  // Evidence: the glass-box tab lists the case facts and the learner's actions after the fact.
  await page.getByRole("tab", { name: t("report.glassBox") }).click();
  await expect(page.getByRole("heading", { name: t("report.learnerActions") })).toBeVisible();
  await expect(page.getByRole("heading", { name: t("report.facts") })).toBeVisible();

  // Branch replay: step through the scripted consequence scenes.
  await page.getByRole("tab", { name: t("report.consequenceReplay") }).click();
  await expect(page.getByRole("heading", { name: t("branchReplay.title") })).toBeVisible();
  await audit(page);
  const next = page.getByRole("button", { name: t("branchReplay.next") });
  if (await next.isEnabled()) {
    await next.click();
    await expect(page.locator("[aria-current=step]").first()).toBeVisible();
  }
  await noOverflow(page);

  // Alternate path without a model: a shipped example plays from static recordings.
  // A cold `next dev` can drop the first load of a freshly compiled route; reload until the list renders.
  await expect(async () => {
    await page.goto("/replay");
    await expect(page.getByRole("button", { name: t("replay.open") }).first()).toBeVisible({ timeout: 8_000 });
  }).toPass({ timeout: 45_000 });
  await page.getByRole("button", { name: t("replay.open") }).first().click();
  await expect(page.getByRole("button", { name: t("replay.pause") })).toBeVisible();
  await audit(page);
});

async function chooseReply(page: Page, text: string) {
  const enter = page.getByRole("button", { name: t("experience.enterChapter"), exact: true });
  const radio = page.getByRole("radio", { name: text, exact: true });
  await expect(enter.or(radio)).toBeVisible();
  if (await enter.isVisible()) await enter.click();
  await radio.check();
  await page.getByRole("button", { name: t("experience.commit"), exact: true }).click();
}

test("family co-op: desktop host and 360px mobile partner finish a shared story", async ({ browser }) => {
  const hostContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const partnerContext = await browser.newContext({ viewport: { width: 360, height: 780 } });
  try {
    const host = await hostContext.newPage();
    const partner = await partnerContext.newPage();
    await requireMockApi(host);

    await host.goto("/family");
    await host.getByRole("button", { name: t("family.create"), exact: true }).click();
    await expect(host.locator("#family-share")).toHaveValue(/#room=/);
    const invite = await host.locator("#family-share").inputValue();

    await partner.goto(invite);
    await expect(partner.getByRole("button", { name: t("family.join"), exact: true })).toBeVisible();
    await audit(partner);
    await partner.getByRole("button", { name: t("family.join"), exact: true }).click();
    await expect(partner.getByText(t("family.private"), { exact: true })).toBeVisible();

    const tabs = [host, partner];
    const saved = await Promise.all(tabs.map((tab) => tab.evaluate(() =>
      JSON.parse(sessionStorage.getItem("sim-tamy-family:first-night")!) as { room_id: string; token: string })));
    // Four decisions alternate between the two roles; the server view says what each may choose.
    for (let i = 0; i < 4; i++) {
      const who = i % 2;
      const url = `${apiUrl}/v1/family/rooms/${saved[who]!.room_id}`;
      const headers = { Authorization: `Bearer ${saved[who]!.token}` };
      const view = await (await tabs[who]!.request.get(url, { headers })).json() as components["schemas"]["FamilyView"];
      expect(view.report).toBeNull();
      await chooseReply(tabs[who]!, view.scene!.choices[0]!.text_th);
      await expect.poll(async () => (await (await tabs[who]!.request.get(url, { headers })).json()).state_version).toBe(i + 1);
    }

    for (const tab of tabs) await expect(tab.getByRole("heading", { name: t("family.report") })).toBeVisible();
    await audit(partner); // the 360px device
    await expect(host.getByText(t("profiles.team"), { exact: true })).toBeVisible();
    await expect(partner.getByRole("heading", { name: t("family.sources") })).toBeVisible();
  } finally {
    await hostContext.close();
    await partnerContext.close();
  }
});

type Saved = { room_id: string; token: string };

test("family co-op: golden-first-night private facts, disagreement and joint decision", async ({ browser }) => {
  const hostContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const partnerContext = await browser.newContext({ viewport: { width: 360, height: 780 } });
  try {
    const host = await hostContext.newPage();
    const partner = await partnerContext.newPage();
    await requireMockApi(host);

    await host.goto("/golden");
    await host.getByRole("button", { name: t("family.create"), exact: true }).click();
    await partner.goto(await host.locator("#family-share").inputValue());
    await partner.getByRole("button", { name: t("family.join"), exact: true }).click();
    await expect(partner.getByText(t("family.private"), { exact: true })).toBeVisible();
    await expect(host.getByText(t("family.cosim.presence.online"))).toBeVisible();
    await audit(partner);

    const [mother, father] = (await Promise.all([host, partner].map((tab) => tab.evaluate(() =>
      JSON.parse(sessionStorage.getItem("sim-tamy-family:golden-first-night")!) as Saved)))) as [Saved, Saved];
    const read = async (tab: Page, saved: Saved) => (await (await tab.request.get(`${apiUrl}/v1/family/rooms/${saved.room_id}`,
      { headers: { Authorization: `Bearer ${saved.token}` } })).json()) as components["schemas"]["FamilyView"];
    const choose = async (tab: Page, saved: Saved, id: string) =>
      chooseReply(tab, (await read(tab, saved)).scene!.choices.find((choice) => choice.id === id)!.text_th);
    const completed = async () => (await read(host, mother)).completed_steps;

    // Each parent holds a private fact; sharing one moves it into the other parent's view.
    const motherFact = (await read(host, mother)).my_facts!.find((fact) => fact.id === "m-feed")!.text_th;
    await expect(partner.getByText(motherFact)).toHaveCount(0);
    await host.getByText(motherFact).locator("xpath=..").getByRole("button", { name: t("family.cosim.facts.share") }).click();
    await expect(partner.locator(".family-timeline").getByText(motherFact)).toBeVisible();

    await choose(host, mother, "say-what-you-see");
    await expect.poll(completed).toBe(1);
    await choose(partner, father, "share-and-listen");
    await expect.poll(completed).toBe(2);
    await choose(host, mother, "listen-then-ask");
    await expect.poll(async () => (await read(host, mother)).scene?.joint).toBe(true);

    // The joint decision: different picks show a disagreement notice, the same pick locks it.
    await choose(host, mother, "contact-health-service");
    await choose(partner, father, "wait-until-morning");
    await expect(partner.getByRole("alert").filter({ hasText: t("family.cosim.joint.needAgree") })).toBeVisible();
    await audit(partner);
    await choose(host, mother, "contact-health-service");
    await choose(partner, father, "contact-health-service");
    await expect.poll(async () => (await read(host, mother)).scene?.id).toBe("consequence");
    await choose(partner, father, "report-observations");
    await expect.poll(completed).toBe(5);
    await choose(host, mother, "agree-share-and-ask");

    for (const tab of [host, partner]) await expect(tab.getByRole("heading", { name: t("family.report") })).toBeVisible();
    await audit(partner);
  } finally {
    await hostContext.close();
    await partnerContext.close();
  }
});
