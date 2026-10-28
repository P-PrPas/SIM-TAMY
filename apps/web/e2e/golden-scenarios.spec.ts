import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Browser, type Page } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { t } from "../lib/i18n";

// 2.0 Golden Scenarios GS-A / GS-B: two browser contexts (desktop host + 360px partner) against the
// local API + PostgreSQL with the mock LLM. The mock script makes AI-01 fail, so typed text takes the
// deterministic lexical fallback: the typed phrases are the authored example questions. Every learner
// phrase and authored reply is read from content/family/*.yaml, never written in this spec.
// Run with `make test-e2e-demo`. Every wait is a web-first assertion or a response/poll, never a sleep.
const apiUrl = "http://127.0.0.1:8000";
type View = components["schemas"]["FamilyView"];
type Saved = { room_id: string; token: string };

const story = (id: string) => readFileSync(resolve(__dirname, `../../../content/family/${id}.yaml`), "utf8");
function field(file: string, id: string, name: string): string {
  const from = file.indexOf(`- id: ${id}\n`);
  const found = file.slice(from).match(new RegExp(`\\n\\s+${name}: (.*)`));
  if (from < 0 || !found) throw new Error(`${id}.${name} not found`);
  return found[1]!.trim();
}
const example = (file: string, intent: string) => field(file, intent, "examples_th").replace(/^\[|\]$/g, "").split(", ")[0]!;
const topLevel = (file: string, name: string) => file.match(new RegExp(`^${name}: (.*)$`, "m"))![1]!.trim();

async function requireMockApi(page: Page) {
  const health = await page.request.get(`${apiUrl}/health`);
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toMatchObject({ db: "ok", llm_provider: "mock" });
}

// Same checks as competition-demo.spec.ts: no serious/critical axe violation, no horizontal scroll,
// and no visible control under 44x44 CSS px.
async function audit(page: Page) {
  const layout = await page.evaluate(() => ({
    width: window.innerWidth, scrollWidth: document.documentElement.scrollWidth,
    overflow: [...document.querySelectorAll<HTMLElement>("main *")].filter((el) =>
      el.getBoundingClientRect().right > window.innerWidth).map((el) => el.className).slice(0, 12),
  }));
  expect(layout.scrollWidth, JSON.stringify(layout)).toBeLessThanOrEqual(layout.width);
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
        const target = el.closest("label")?.getBoundingClientRect() ?? box;
        return box.width > 0 && getComputedStyle(el).visibility !== "hidden" && (target.width < 44 || target.height < 44);
      }).map((el) => el.outerHTML.slice(0, 80));
    return { serious, small };
  });
  expect(found, JSON.stringify(found)).toEqual({ serious: [], small: [] });
}

async function enter(page: Page) {
  const gate = page.getByRole("button", { name: t("experience.enterChapter"), exact: true });
  const input = page.getByLabel(t("lab.chat.label"));
  const radio = page.getByRole("radio").first();
  await expect(gate.or(input).or(radio).first()).toBeVisible();
  if (await gate.isVisible()) await gate.click();
}

/** Type into the chat and wait for the validated reply; play-time bodies never carry hidden state. */
async function say(page: Page, text: string) {
  await enter(page);
  await page.getByLabel(t("lab.chat.label")).fill(text);
  const reply = page.waitForResponse((r) => r.request().method() === "POST" && r.status() === 200 && /\/messages$/.test(r.url()));
  await page.getByRole("button", { name: t("lab.chat.send") }).click();
  const raw = await (await reply).text();
  expect(raw).not.toMatch(/revealed_fact_ids|risk_state|"actions"|ASK_[A-Z_]+|"score"/);
  return JSON.parse(raw) as components["schemas"]["FamilyMessageResult"];
}

async function pick(page: Page, text: string) {
  await enter(page);
  await page.getByRole("radio", { name: text, exact: true }).check();
  await page.getByRole("button", { name: t("experience.commit"), exact: true }).click();
}

async function openKnowledge(page: Page) {
  const panel = page.locator("details.pixel-know");
  if (await panel.count() && await panel.getAttribute("open") === null) {
    await panel.locator("summary").click();
  }
}

async function setup(browser: Browser, id: string, assigned = false) {
  const hostContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const partnerContext = await browser.newContext({ viewport: { width: 360, height: 780 } });
  const host = await hostContext.newPage();
  const partner = await partnerContext.newPage();
  await requireMockApi(host);
  let cohortId: string | undefined;
  let assignmentId: string | undefined;
  if (assigned) {
    const headers = { "X-Demo-Account": "staff-h-edu-1" };
    const cohort = await host.request.post(`${apiUrl}/v1/orgs/org-demo-hospital/cohorts`, {
      headers, data: { name: "Golden integration" },
    });
    expect(cohort.status()).toBe(201);
    cohortId = (await cohort.json()).id;
    const assignment = await host.request.post(`${apiUrl}/v1/cohorts/${cohortId}/assignments`, {
      headers, data: { story_id: id },
    });
    expect(assignment.status()).toBe(201);
    assignmentId = (await assignment.json()).id;
    await host.addInitScript(() => localStorage.setItem("sim-tamy-demo-account", "parent-h-mom-1"));
    await partner.addInitScript(() => localStorage.setItem("sim-tamy-demo-account", "parent-h-dad-1"));
  }
  await host.goto(`/simulate/${id}${assignmentId ? `?assignment=${assignmentId}` : ""}`);
  await host.getByRole("button", { name: t("family.create"), exact: true }).click();
  await partner.goto(await host.locator("#family-share").inputValue());
  await partner.getByRole("button", { name: t("family.join"), exact: true }).click();
  await expect(partner.getByText(t("family.private"), { exact: true })).toBeAttached();
  await openKnowledge(partner);
  await expect(partner.getByText(t("family.private"), { exact: true })).toBeVisible();
  await openKnowledge(host);
  const [mother, father] = (await Promise.all([host, partner].map((tab) => tab.evaluate((key) =>
    JSON.parse(sessionStorage.getItem(key)!) as Saved, `sim-tamy-family:${id}`)))) as [Saved, Saved];
  const read = async (tab: Page, saved: Saved) => (await (await tab.request.get(`${apiUrl}/v1/family/rooms/${saved.room_id}`,
    { headers: { Authorization: `Bearer ${saved.token}` } })).json()) as View;
  const text = async (choice: string, tab: Page, saved: Saved) =>
    (await read(tab, saved)).scene!.choices.find((c) => c.id === choice)!.text_th;
  const choose = async (tab: Page, saved: Saved, id: string) => {
    const choice = (await read(tab, saved)).scene!.choices.find((c) => c.id === id)!;
    await pick(tab, choice.short_th || choice.text_th);
  };
  const cont = async (tab: Page, saved: Saved) =>
    tab.getByRole("button", { name: (await read(tab, saved)).scene!.choices[0]!.text_th }).click();
  const step = async () => (await read(host, mother)).scene?.id;
  return { hostContext, partnerContext, host, partner, mother, father, read, text, choose, cont, step, cohortId };
}

test("GS-A: typed discovery, role-private facts, share, joint vote mismatch then agreement, report and debrief", async ({ browser }) => {
  const s = await setup(browser, "gs-a-postpartum-warning", true);
  const { host, partner, mother, father, read, text, choose, cont, step } = s;
  try {
    const file = story("gs-a-postpartum-warning");

    // typed question -> validated reply -> the fact joins only the asker's private brief
    const first = await say(host, example(file, "ASK_BLEEDING"));
    expect(first.reply?.text_th).toBe(field(file, "ASK_BLEEDING", "reply_th")); // high-risk authored template
    const bleed = first.view.my_facts![0]!.text_th;
    await expect(host.getByText(bleed, { exact: false }).first()).toBeVisible();
    await expect(partner.getByText(bleed, { exact: false })).toHaveCount(0);
    // real-world health requests hit the content boundary and change nothing
    const boundary = await say(host, "diagnose me");
    expect(boundary.reply?.text_th).toBe(topLevel(file, "boundary_th"));
    await audit(host);
    await cont(host, mother);
    await expect.poll(step).toBe("discover-father");

    await say(partner, example(file, "ASK_BREATHING"));
    await cont(partner, father);
    await expect.poll(step).toBe("share-with-partner");

    // share the discovered fact, then the mother commits the next choice
    await host.getByText(bleed, { exact: false }).locator("xpath=..").getByRole("button", { name: t("family.cosim.facts.share") }).click();
    await expect(partner.locator(".family-timeline").getByText(bleed, { exact: false })).toBeVisible();
    await audit(partner);
    await choose(host, mother, "say-what-you-see");
    await expect.poll(step).toBe("ask-grandmother");

    // The integrated knowledge stream supplies released claims and matching source locators.
    const answer = await say(partner, example(file, "ASK_TRADITION"));
    expect(answer.reply?.citations.length).toBeGreaterThan(0);
    for (const cite of answer.reply!.citations) {
      const unit = await partner.request.get(`${apiUrl}/v1/knowledge/units/${cite.knowledge_id}`);
      expect(unit.ok()).toBeTruthy();
      const claims = (await unit.json()).claims as components["schemas"]["ClaimView"][];
      expect(claims.find((c) => c.id === cite.claim_id)?.sources).toContainEqual(
        expect.objectContaining({ source_id: cite.source_id, locator: cite.locator }),
      );
    }
    await cont(partner, father);
    await expect.poll(step).toBe("elder-suggestion");

    await enter(host);
    await expect(host.getByText(t("lab.lens.wisdom"), { exact: true })).toHaveCount(1); // Thai Wisdom Lens
    await choose(host, mother, "listen-then-ask");
    await expect.poll(step).toBe("joint-help-decision");

    // a critical joint step never commits from typed text: the chat only offers the buttons
    const typed = await say(host, await text("contact-health-service", host, mother));
    expect(typed.clarification?.options.length).toBeGreaterThan(1);
    expect((await read(host, mother)).scene?.id).toBe("joint-help-decision");
    await choose(host, mother, "contact-health-service");
    await choose(partner, father, "wait-until-morning");
    await expect(partner.getByRole("alert").filter({ hasText: t("family.cosim.joint.needAgree") })).toBeVisible();
    await choose(host, mother, "contact-health-service");
    await choose(partner, father, "contact-health-service");
    await expect.poll(step).toBe("consequence");
    await choose(partner, father, "report-observations");
    await choose(host, mother, "agree-check-first");

    for (const tab of [host, partner]) {
      await expect(tab.getByRole("heading", { name: t("family.report") })).toBeVisible();
      await expect(tab.getByRole("heading", { name: t("lab.report.dimensions") })).toBeVisible();
      await expect(tab.getByRole("heading", { name: t("lab.debrief.title") })).toBeVisible();
      await expect(tab.getByText(t("lab.debrief.strengths"))).toBeVisible();
    }
    await expect(host.getByText(t("family.safetyObserved"))).toBeVisible();
    await audit(partner);
    const analytics = await host.request.get(`${apiUrl}/v1/cohorts/${s.cohortId}/analytics`, {
      headers: { "X-Demo-Account": "staff-h-edu-1" },
    });
    expect(analytics.ok()).toBeTruthy();
    expect(await analytics.json()).toMatchObject({
      n_started: 1, n_finished: 1,
      objectives: [
        { objective_id: "OBJ-3-01", n: 1, numerator: null, suppressed: true },
        { objective_id: "OBJ-3-03", n: 1, numerator: null, suppressed: true },
      ],
    });
    await host.goto("/passport");
    const passport = await host.request.get(`${apiUrl}/v1/passport/parent-h-mom-1`);
    const attempt = (await passport.json()).attempts.find((a: { room_id: string }) => a.room_id === mother.room_id);
    expect(attempt).toMatchObject({ score_total: expect.any(Number), objective_ids: ["OBJ-3-01", "OBJ-3-03"] });
    await expect(host.getByRole("heading", { name: attempt.title_th }).first()).toBeVisible();
    await expect(host.getByText(t("platform.passport.score") + ":", { exact: false }).first()).toBeVisible();
  } finally {
    await s.hostContext.close();
    await s.partnerContext.close();
  }
});

test("GS-B: positive Thai-service route with typed discovery, a choice committed from text, and no emergency gate", async ({ browser }) => {
  const s = await setup(browser, "gs-b-thai-recovery");
  const { host, partner, mother, father, read, text, cont, step } = s;
  try {
    const file = story("gs-b-thai-recovery");
    const reply = await say(host, example(file, "ASK_TIMING_WOUND"));
    expect((reply.view.my_facts ?? []).map((f) => f.id)).toEqual(["m-timing"]);
    await cont(host, mother);
    await say(partner, example(file, "ASK_PROVIDER"));
    await cont(partner, father);
    await expect.poll(step).toBe("share-checklist");

    const fact = (await read(host, mother)).my_facts![0]!.text_th;
    await host.getByText(fact, { exact: false }).locator("xpath=..").getByRole("button", { name: t("family.cosim.facts.share") }).click();
    await expect(partner.locator(".family-timeline").getByText(fact, { exact: false })).toBeVisible();
    await pick(host, await text("share-what-we-learned", host, mother));
    await expect.poll(step).toBe("elder-offer");

    // non-critical, non-joint choice step: the typed choice text commits the decision
    const committed = await say(partner, await text("welcome-and-ask", partner, father));
    expect(committed.reply?.text_th).toBe(field(file, "welcome-and-ask", "reply_th"));
    await expect.poll(step).toBe("joint-booking");

    const booking = await text("book-with-checklist", host, mother);
    await pick(host, booking);
    await pick(partner, booking);
    await expect.poll(step).toBe("at-service");
    await pick(partner, await text("tell-and-agree-stop", partner, father));
    await pick(host, await text("agree-ask-and-record", host, mother));

    for (const tab of [host, partner]) {
      await expect(tab.getByRole("heading", { name: t("lab.report.dimensions") })).toBeVisible();
      await expect(tab.getByRole("heading", { name: t("lab.debrief.title") })).toBeVisible();
    }
    await expect(host.getByText(t("family.safetyObserved"))).toBeVisible();
    await audit(host);
  } finally {
    await s.hostContext.close();
    await s.partnerContext.close();
  }
});
