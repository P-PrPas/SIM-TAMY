import { expect, test, type Page } from "@playwright/test";

import { t } from "../lib/i18n";
import { syntheticReport } from "./fixtures/report";

const brief = {
  case_id: "PP-001", version: "0.1", title_th: "Synthetic case", status: "Draft",
  status_label_th: "Draft case", variants_available: ["A"],
  patient_display_th: "Synthetic patient", learning_objectives: [{ id: "LO1", label_th: "Synthetic objective" }], disclaimer_th: "Education only",
  decision_options: [{ id: "refer", label_th: "Refer" }, { id: "proceed_service", label_th: "Proceed" }],
};
const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Authorization, Content-Type", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" };

async function seed(page: Page) {
  await page.addInitScript((value) => sessionStorage.setItem("sim-tamy-session", JSON.stringify(value)), {
    id: "session-1", token: "synthetic-token", caseId: "PP-001", brief,
  });
  await page.route("**/v1/sessions/session-1**", (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS") return route.fulfill({ status: 204, headers });
    if (request.url().endsWith("/report")) return route.fulfill({ status: 200, headers, contentType: "application/json", json: syntheticReport });
    return route.fulfill({ status: 200, headers, contentType: "application/json", json: {
      session_id: "session-1", case: { case_id: "PP-001", version: "0.1", status: "Draft", status_label_th: "Draft case" },
      variant: "A", status: "active", phase: "INTERVIEW", turn_idx: 1, turns_remaining: 39,
      decision: { committed: false, option_id: null },
      history: [{ idx: 1, speaker: "patient", text: "Synthetic reply", created_at: "2026-10-12T00:00:00Z" }],
      limits: { max_turns: 40, max_text_chars: 500, max_rationale_chars: 300, max_note_chars: 500 },
      created_at: "2026-10-12T00:00:00Z", last_activity_at: "2026-10-12T00:00:00Z",
    } });
  });
}

// ponytail: fails on critical and serious axe impacts only; moderate/minor are reported by axe but not gated.
async function expectNoSeriousViolations(page: Page) {
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(async () => {
    const axe = (globalThis as unknown as { axe: { run: () => Promise<{ violations: Array<{ id: string; impact: string | null; nodes: Array<{ target: unknown }> }> }> } }).axe;
    const result = await axe.run();
    return result.violations.filter((item) => item.impact === "critical" || item.impact === "serious")
      .map((item) => ({ id: item.id, impact: item.impact, targets: item.nodes.map((node) => node.target) }));
  });
  expect(violations, JSON.stringify(violations)).toEqual([]);
}

for (const [name, path] of [["S3 Chat", "/chat"], ["S4 Decision", "/decision"], ["S6 Closing", "/closing"], ["S7 Report", "/report"], ["S2 Briefing", "/briefing"]] as const) {
  test(`${name} has no critical or serious axe violations at 360px`, async ({ page }) => {
    await seed(page);
    await page.goto(path);
    await page.locator("main").first().waitFor();
    await expectNoSeriousViolations(page);
  });
}

test("S1 Join has no critical or serious axe violations at 360px", async ({ page }) => {
  await page.goto("/");
  await page.locator("main").first().waitFor();
  await expectNoSeriousViolations(page);
});

test("the skip link is the first focusable element and moves focus to the content", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: t("app.skipToContent") });
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});
