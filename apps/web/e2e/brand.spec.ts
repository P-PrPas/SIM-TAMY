import { expect, test } from "@playwright/test";

import { t } from "../lib/i18n";

for (const viewport of [{ width: 360, height: 780 }, { width: 844, height: 390 }, { width: 1440, height: 1000 }]) {
  test(`branded learning entry works at ${viewport.width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/lab/solo");
    await expect(page.locator("#case:enabled")).toBeVisible();
    if (viewport.width < 1200) await page.getByRole("button", { name: t("platform.nav.openMenu") }).click();
    await expect(page.getByRole("navigation", { name: t("nav.label") })).toBeVisible();
    await expect(page.locator("a.brand")).toBeVisible();
    await expect(page.locator("a.brand")).toHaveAccessibleName(/SIM-TAMY/);
    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await page.locator(".hero-logo").evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
    await page.screenshot({ path: testInfo.outputPath("home.png"), fullPage: true });

    await page.getByRole("link", { name: t("join.heroCta") }).click();
    await expect(page).toHaveURL(/#practice$/);
    await expect(page.locator("#practice-title")).toBeInViewport();
    await page.getByRole("textbox", { name: t("join.nickname") }).fill("Learner");
    await page.getByRole("button", { name: t("join.start") }).click();
    await expect(page).toHaveURL(/\/briefing$/);
    await expect(page.getByRole("link", { name: t("briefing.begin") })).toBeVisible();
    await expect(page.locator('[aria-current="step"]')).toHaveText(new RegExp(t("steps.briefing")));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath("briefing.png"), fullPage: true });
  });
}

test("entry remains usable with enlarged text", async ({ page }) => {
  await page.goto("/lab/solo");
  await expect(page.locator("#case:enabled")).toBeVisible();
  await page.evaluate(() => { document.documentElement.style.fontSize = "32px"; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.getByRole("button", { name: t("join.start") })).toBeEnabled();
});

test("motion settles without shifting layout and responds to reduced motion changes", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/lab/solo");
  const hero = page.locator(".hero-art");
  await expect(hero).toHaveCSS("animation-name", "hero-art-arrive");
  await expect(hero).toHaveCSS("opacity", "1");
  await expect.poll(() => hero.evaluate((element) => {
    const transform = getComputedStyle(element).transform;
    return transform === "none" || new DOMMatrixReadOnly(transform).isIdentity;
  })).toBe(true);
  const button = page.getByRole("link", { name: t("join.heroCta") });
  await button.hover();
  await expect(button).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, -2)");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(hero).toHaveCSS("animation-name", "none");
  await expect(hero).toHaveCSS("opacity", "1");
  await expect(button).toHaveCSS("transition-duration", "0s");
  await expect(button).toHaveCSS("transform", "none");
  await expect(page.locator("html")).toHaveCSS("scroll-behavior", "auto");
  await button.click();
  await expect(page.locator("#practice-title")).toBeInViewport();
});
