import { expect, test, type Page } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { t } from "../lib/i18n";

async function chooseReply(page: Page, text: string) {
  const enter = page.getByRole("button", { name: t("experience.enterChapter"), exact: true });
  const radio = page.getByRole("radio", { name: text, exact: true });
  await expect(enter.or(radio)).toBeVisible();
  if (await enter.isVisible()) await enter.click();
  await radio.check();
  await page.getByRole("button", { name: t("experience.commit"), exact: true }).click();
}

test("two isolated devices complete a shared story and see the critical checkpoint", async ({ page, browser, request }) => {
  await page.goto("/family");
  await page.getByRole("button", { name: t("family.create"), exact: true }).click();
  await expect(page.locator("#family-share")).toHaveValue(/#room=/);
  const link = await page.locator("#family-share").inputValue();
  await page.getByRole("button", { name: t("family.design.copy"), exact: true }).click();
  await expect(page.getByRole("button", { name: t("family.design.copied"), exact: true })).toBeVisible();
  const partnerContext = await browser.newContext({ viewport: { width: 360, height: 780 } });
  try {
    const partner = await partnerContext.newPage();
    await partner.goto(link);
    await partner.getByRole("button", { name: t("family.join"), exact: true }).click();
    await expect(partner.getByText(t("family.private"), { exact: true })).toBeVisible();
    if (process.env.SIMTAMY_DESIGN_SHOTS) {
      await page.screenshot({ path: ".tmp/family-design/room-360.png", fullPage: true, animations: "disabled" });
    }
    const credentials = await Promise.all([page, partner].map((tab) => tab.evaluate(() =>
      JSON.parse(sessionStorage.getItem("sim-tamy-family:first-night")!) as { room_id: string; token: string },
    )));
    for (let i = 0; i < 4; i++) {
      const actor = i % 2 === 0 ? page : partner;
      const saved = credentials[i % 2]!;
      const url = `http://127.0.0.1:8000/v1/family/rooms/${saved.room_id}`;
      const options = { headers: { Authorization: `Bearer ${saved.token}` } };
      const response = await request.get(url, options);
      const view = await response.json() as components["schemas"]["FamilyView"];
      expect(view.report).toBeNull();
      const choices = view.scene!.choices;
      const choice = i === 3 ? choices[choices.length - 1]! : choices[0]!;
      await chooseReply(actor, choice.text_th);
      await expect.poll(async () => (await (await request.get(url, options)).json()).state_version).toBe(i + 1);
      if (i === 1) await page.reload();
    }
    await expect(page.getByRole("heading", { name: t("family.report") })).toBeVisible();
    await expect(partner.getByText(t("family.safetyReview"))).toBeVisible();
    for (const tab of [page, partner]) {
      expect(await tab.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    }
    if (process.env.SIMTAMY_DESIGN_SHOTS) {
      await page.screenshot({ path: ".tmp/family-design/report-360.png", fullPage: true, animations: "disabled" });
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.screenshot({ path: ".tmp/family-design/report-1280.png", fullPage: true, animations: "disabled" });
    }
  } finally { await partnerContext.close(); }
});

test("all family entrances remain readable and keyboard accessible on mobile and desktop", async ({ page }) => {
  for (const width of [360, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: width === 1280 ? "reduce" : "no-preference" });
    for (const [path, name] of [["/family", "coop"], ["/parenthood", "journey"], ["/bridge", "bridge"]]) {
      await page.goto(path!);
      const start = page.getByRole("button", { name: t(path === "/family" ? "family.create" : "family.startSolo"), exact: true });
      await expect(start).toBeEnabled();
      if (width === 1280) await expect(page.locator(".family-hero-art")).toHaveCSS("animation-name", "none");
      await page.getByRole("radio", { name: new RegExp(t("family.father")) }).focus();
      await page.keyboard.press("Space");
      await expect(page.getByRole("radio", { name: new RegExp(t("family.father")) })).toBeChecked();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      if (process.env.SIMTAMY_DESIGN_SHOTS) await page.screenshot({ path: `.tmp/family-design/${name}-${width}.png`, fullPage: true, style: "nextjs-portal { display: none; }" });
      await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
      const serious = await page.evaluate(async () => {
        const axe = (globalThis as unknown as { axe: { run: () => Promise<{ violations: Array<{ id: string; impact: string | null; nodes: Array<{ target: string[] }> }> }> } }).axe;
        return (await axe.run()).violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => ({ id: v.id, targets: v.nodes.map((node) => node.target) }));
      });
      expect(serious).toEqual([]);
    }
  }
  await page.setViewportSize({ width: 360, height: 900 });
  await page.goto("/family");
  await page.evaluate(() => { document.documentElement.style.fontSize = "32px"; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByRole("button", { name: t("family.create"), exact: true })).toBeEnabled();
});

test("a parent resumes a three-chapter story and reaches its evidence report", async ({ page, request }) => {
  await page.goto("/parenthood");
  await page.getByRole("button", { name: t("family.startSolo"), exact: true }).click();
  await expect(page.getByText(t("family.private"), { exact: true })).toBeVisible();
  const saved = await page.evaluate(() => JSON.parse(sessionStorage.getItem("sim-tamy-family:parenthood")!) as { room_id: string; token: string });
  const url = `http://127.0.0.1:8000/v1/family/rooms/${saved.room_id}`;
  const headers = { Authorization: `Bearer ${saved.token}` };
  const path = ["postpone-plan", "keep-private", "adjust-plan", "request-relief", "respectful-boundary", "verify-together"];
  const chapters = new Set<string>();
  for (let i = 0; i < path.length; i++) {
    const view = await (await request.get(url, { headers })).json() as components["schemas"]["FamilyView"];
    chapters.add(view.scene!.chapter_th);
    await chooseReply(page, view.scene!.choices.find((choice) => choice.id === path[i])!.text_th);
    await expect.poll(async () => (await (await request.get(url, { headers })).json()).state_version).toBe(i + 1);
    if (i === 1) await page.reload();
  }
  expect(chapters.size).toBe(3);
  await expect(page.getByRole("heading", { name: t("family.report") })).toBeVisible();
  await expect(page.getByRole("heading", { name: t("family.sources") })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("all four grandmother topics finish with cited evidence and bounded dialogue", async ({ page, request }) => {
  for (const topic of ["fire", "compress", "food", "herbs"]) {
    await page.goto(`/bridge?topic=${topic}`);
    await page.getByRole("button", { name: t("family.startSolo"), exact: true }).click();
    await expect(page.getByText(t("family.private"), { exact: true })).toBeVisible();
    const saved = await page.evaluate((id) => JSON.parse(sessionStorage.getItem(`sim-tamy-family:${id}`)!) as { room_id: string; token: string }, `bridge-${topic}`);
    const url = `http://127.0.0.1:8000/v1/family/rooms/${saved.room_id}`;
    const headers = { Authorization: `Bearer ${saved.token}` };
    for (let i = 0; i < 3; i++) {
      const view = await (await request.get(url, { headers })).json() as components["schemas"]["FamilyView"];
      expect(view.report).toBeNull();
      await chooseReply(page, view.scene!.choices[0]!.text_th);
      await expect.poll(async () => (await (await request.get(url, { headers })).json()).state_version).toBe(i + 1);
    }
    await expect(page.getByRole("heading", { name: t("family.sources") })).toBeVisible();
    await expect(page.locator('a[href^="https://"]')).not.toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(async () => {
    const axe = (globalThis as unknown as { axe: { run: () => Promise<{ violations: Array<{ id: string; impact: string | null }> }> } }).axe;
    return (await axe.run()).violations.filter((v) => v.impact === "critical" || v.impact === "serious").map((v) => v.id);
  });
  expect(violations).toEqual([]);
});
