import { expect, test, type Page } from "@playwright/test";
import { t } from "../lib/i18n";
import { DEMO_PASSWORD } from "../lib/demo-login";

test.use({ storageState: { cookies: [], origins: [] } });
const api = "http://127.0.0.1:8000";

async function login(page: Page, id: string, next = "") {
  await page.goto(`/login${next ? `?next=${encodeURIComponent(next)}` : ""}`);
  await page.getByText(t("platform.login.choose"), { exact: true }).click();
  await page.getByLabel(t("platform.login.account"), { exact: true }).selectOption(id);
  await expect(page.getByLabel(t("platform.login.username"))).toHaveValue(id);
  await expect(page.getByLabel(t("platform.login.password"), { exact: true })).toHaveValue(DEMO_PASSWORD);
  await page.getByRole("button", { name: t("platform.login.submit"), exact: true }).click();
}

async function logout(page: Page) {
  await page.locator(".account-menu > summary").click();
  await page.getByRole("button", { name: t("platform.login.logout"), exact: true }).click();
  await expect(page).toHaveURL(/\/login(?:\?|$)/);
}

async function accessible(page: Page) {
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const serious = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run(): Promise<{ violations: Array<{ id: string; impact: string; nodes: Array<{ target: string[] }> }> }> } }).axe;
    return (await axe.run()).violations.filter((v) => ["critical", "serious"].includes(v.impact)).map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) }));
  });
  expect(serious).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

for (const width of [360, 844, 1440]) {
  test(`login and personal dashboard at ${width}px`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/profile");
    await expect(page).toHaveURL(/\/login\?next=/);
    await expect(page.getByRole("heading", { name: t("platform.login.title") })).toBeVisible();
    await accessible(page);
    await page.screenshot({ path: info.outputPath("login.png"), fullPage: true });
    const completed = await page.request.post(`${api}/v1/passport/parent-h-mom-1/lessons/KB-TM-ELEMENT-001`);
    expect(completed.ok()).toBe(true);
    await login(page, "parent-h-mom-1", "/profile");
    await expect(page).toHaveURL(/\/profile$/);
    await expect(page.getByRole("progressbar")).toHaveCount(4);
    await expect.poll(async () => Number(await page.getByRole("progressbar").first().getAttribute("value"))).toBeGreaterThanOrEqual(1);
    await expect(page.getByRole("heading", { name: t("platform.dashboard.lessonHistory") })).toBeVisible();
    await accessible(page);
    await page.screenshot({ path: info.outputPath("profile.png"), fullPage: true });
    await page.locator(".account-menu > summary").focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("link", { name: t("platform.login.viewProfile"), exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.locator(".account-menu")).not.toHaveAttribute("open", "");
    await page.goto("/institution");
    await expect(page).toHaveURL(/\/profile$/);
    await logout(page);
    await login(page, "parent-free-dad-1", "/profile");
    await expect(page.getByRole("progressbar").first()).toHaveAttribute("value", "0");
    await expect(page.getByText(t("platform.dashboard.noLessons"))).toBeVisible();
  });
}

test("institution login has only workspace features and manages cohorts and assignments", async ({ page }, info) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, "staff-h-edu-1");
  await expect(page).toHaveURL(/\/institution$/);
  await expect(page.getByRole("heading", { name: t("institution.overview.title"), exact: true })).toBeVisible();
  await expect(page.locator(".site-nav nav a")).toHaveCount(1);
  await expect(page.locator('a[href="/learn"], a[href="/lab"], a[href="/profile"]')).toHaveCount(0);
  await accessible(page);
  await page.screenshot({ path: info.outputPath("institution.png"), fullPage: true });
  await page.goto("/learn");
  await expect(page).toHaveURL(/\/institution$/);
  await page.getByRole("link", { name: t("institution.overview.manage"), exact: true }).click();
  const name = `Dashboard test ${Date.now()}`;
  await page.getByLabel(t("institution.cohorts.name")).fill(name);
  await page.getByRole("button", { name: t("institution.cohorts.create"), exact: true }).click();
  const row = page.locator("li").filter({ has: page.getByText(name, { exact: true }) });
  await row.getByRole("link", { name: t("institution.cohorts.open") }).click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  await page.getByLabel(t("institution.cohort.storyLabel")).selectOption("thai-elements-family");
  await page.getByRole("button", { name: t("institution.cohort.assign"), exact: true }).click();
  const removeAssignment = page.getByRole("button", { name: new RegExp(`^${t("institution.manage.remove")}`) });
  await expect(removeAssignment).toHaveCount(1);
  await removeAssignment.click();
  await page.getByRole("button", { name: t("institution.manage.confirmButton"), exact: true }).click();
  await expect(removeAssignment).toHaveCount(0);
  await page.getByRole("link", { name: t("institution.cohort.back"), exact: true }).click();
  const removeCohort = page.getByRole("button", { name: `${t("institution.manage.remove")} ${name}`, exact: true });
  await removeCohort.click();
  await page.getByRole("button", { name: t("institution.manage.cancel"), exact: true }).click();
  await expect(removeCohort).toBeVisible();
  await removeCohort.click();
  await page.getByRole("button", { name: t("institution.manage.confirmButton"), exact: true }).click();
  await expect(removeCohort).toHaveCount(0);
  await accessible(page);
  await logout(page);
});
