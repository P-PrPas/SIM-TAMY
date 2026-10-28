import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { t } from "../lib/i18n";

const apiUrl = "http://127.0.0.1:8000";

function goldenQuestions(id: "T11" | "T13"): string[] {
  // The Content/Golden suite owns the learner utterances; browser tests reuse them.
  const file = readFileSync(resolve(__dirname, `../../../eval/golden/pp001/${id}.yaml`), "utf8");
  const questions = [...file.matchAll(/^\s*- \{say: "([^"]+)"/gm)].map((match) => match[1]!);
  expect(questions.length).toBe(id === "T11" ? 8 : 3);
  return questions;
}

async function assertSafeShell(page: Page, compact = false) {
  await expect(page.getByText(t(compact ? "status.draft" : "status.draftFull"), { exact: true })).toHaveCount(0);
  await expect(page.getByText(t("banner.educationOnly"))).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
}

async function sendQuestion(page: Page, text: string) {
  const input = page.getByRole("textbox", { name: t("chat.messageLabel") });
  await input.fill(text);
  const response = page.waitForResponse((item) =>
    item.request().method() === "POST" && item.status() === 200
      && /\/v1\/sessions\/[^/]+\/turns$/.test(item.url()));
  await page.getByRole("button", { name: t("chat.send") }).click();
  // TURN_IN_PROGRESS may briefly return 409; the client retries the same turn ID.
  const body = JSON.stringify(await (await response).json());
  expect(body).not.toMatch(/revealed_fact_ids|risk_state|"actions"|"score"|safety_status/);
  await expect(page.getByText(t("chat.typing"))).toHaveCount(0);
  await expect(page.getByText(t("chat.sendError"))).toHaveCount(0);
  await expect(page.getByText(text, { exact: true })).toBeVisible();
}

async function startChat(page: Page, variant: "A" | "C") {
  // Every test passes through here before a session exists. A reused local server on :8000
  // may not be the mock one, and a real provider must never be reached by accident.
  const health = await page.request.get(`${apiUrl}/health`);
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toMatchObject({ db: "ok", llm_provider: "mock" });

  await page.goto("/lab/solo");
  await expect(page.getByRole("heading", { name: t("join.title") })).toBeVisible();
  await page.locator("#case").selectOption("PP-001");
  await page.locator("#variant").selectOption(variant);
  await page.getByRole("textbox", { name: t("join.nickname") }).fill(`E2E-${variant}`);
  await assertSafeShell(page);
  await page.getByRole("button", { name: t("join.start") }).click();
  await expect(page).toHaveURL(/\/briefing$/);
  await assertSafeShell(page);
  await page.getByRole("link", { name: t("briefing.begin") }).click();
  await expect(page).toHaveURL(/\/chat$/);
  await assertSafeShell(page);
}

async function commitDecision(page: Page, decision: "refer" | "proceed_service") {
  await page.getByRole("button", { name: t("chat.decide") }).click();
  await expect(page).toHaveURL(/\/decision$/);
  await assertSafeShell(page);
  await page.locator(`input[name="decision"][value="${decision}"]`).check();
  await page.getByRole("button", { name: t("decision.review") }).click();
  await expect(page.getByText(t("decision.irreversible"))).toBeVisible();
  await page.getByRole("button", { name: t("decision.confirm") }).click();
}

for (const variant of ["A", "C"] as const) {
  test(`PP-001 Variant ${variant} reaches a safety-gated report through the real API`, async ({ page }) => {
    await startChat(page, variant);

    const questions = goldenQuestions(variant === "A" ? "T11" : "T13");
    const interviewQuestions = variant === "A" ? questions : questions.slice(0, -1);
    await sendQuestion(page, interviewQuestions[0]!);
    // Refresh/resume: the session id lives in sessionStorage, the transcript on the server.
    await page.reload();
    await expect(page).toHaveURL(/\/chat$/);
    await expect(page.getByText(interviewQuestions[0]!, { exact: true })).toBeVisible();
    for (const question of interviewQuestions.slice(1)) await sendQuestion(page, question);
    await commitDecision(page, "refer");

    if (variant === "C") {
      await expect(page).toHaveURL(/\/chat$/);
      await expect(page.getByText(t("chat.pressure"))).toBeVisible();
      await assertSafeShell(page);
      await sendQuestion(page, questions.at(-1)!);
      await page.getByRole("link", { name: t("chat.toClosing") }).click();
    }
    await expect(page).toHaveURL(/\/closing$/);
    await assertSafeShell(page);
    await page.getByRole("button", { name: t("closing.complete") }).click();
    await expect(page).toHaveURL(/\/report$/);
    await expect(page.getByRole("heading", { name: t("report.title") })).toBeVisible();
    await expect(page.getByText(t("report.safetyMet"))).toBeVisible();
    await assertSafeShell(page, true);
  });
}

test("PP-001 proceeding on a red-flag case ends on a not-met report with no pass wording", async ({ page }) => {
  await startChat(page, "A");
  const questions = goldenQuestions("T11");
  for (const question of questions.slice(4, 6)) await sendQuestion(page, question); // blood loss, dizziness
  await commitDecision(page, "proceed_service");
  await expect(page).toHaveURL(/\/closing$/);
  await page.getByRole("button", { name: t("closing.complete") }).click();
  await expect(page).toHaveURL(/\/report$/);
  await expect(page.getByText(t("report.safetyNotMet"))).toBeVisible();
  await expect(page.getByText(t("report.safetyMet"))).toHaveCount(0);
  const text = await page.locator("main").innerText();
  expect(text).not.toMatch(/สอบผ่าน|ผ่านเกณฑ์|ผ่านการประเมิน|\bpass(ed)?\b/i);
});
