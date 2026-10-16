import { expect, test, type Page } from "@playwright/test";

import { t } from "../lib/i18n";

const brief = {
  case_id: "PP-001", version: "0.1", title_th: "Synthetic case", status: "Draft",
  status_label_th: "Draft case", variants_available: ["A", "C"],
  patient_display_th: "Synthetic patient", learning_objectives: [], disclaimer_th: "Education only",
  decision_options: [{ id: "refer", label_th: "Refer" }, { id: "proceed_service", label_th: "Proceed" }],
};

async function setup(page: Page, variant: "A" | "C") {
  await page.addInitScript((value) => sessionStorage.setItem("sim-tamy-session", JSON.stringify(value)), {
    id: "session-1", token: "synthetic-token", caseId: "PP-001", brief,
  });
  let phase: "INTERVIEW" | "PRESSURE" | "CLOSING" = "INTERVIEW";
  const submitted: Array<{ url: string; body: Record<string, unknown> }> = [];
  await page.route("**/v1/sessions/session-1**", async (route) => {
    const request = route.request();
    const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Authorization, Content-Type", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" };
    if (request.method() === "OPTIONS") return route.fulfill({ status: 204, headers });
    if (request.method() === "GET") return route.fulfill({ status: 200, headers, contentType: "application/json", json: {
      session_id: "session-1", case: { case_id: "PP-001", version: "0.1", status: "Draft", status_label_th: "Draft case" },
      variant, status: "active", phase, turn_idx: 1, turns_remaining: 2,
      decision: { committed: phase !== "INTERVIEW", option_id: "refer" },
      history: phase === "PRESSURE" ? [{ idx: 1, speaker: "relative", text: "Synthetic pressure", created_at: "2026-10-12T00:00:00Z" }] : [],
      limits: { max_turns: 40, max_text_chars: 500, max_rationale_chars: 300, max_note_chars: 500 },
      created_at: "2026-10-12T00:00:00Z", last_activity_at: "2026-10-12T00:00:00Z",
    } });
    const body = request.postDataJSON() as Record<string, unknown>;
    submitted.push({ url: request.url(), body });
    if (request.url().endsWith("/decision")) {
      phase = variant === "C" ? "PRESSURE" : "CLOSING";
      return route.fulfill({ status: 200, headers, contentType: "application/json", json: {
        phase, decision: { option_id: body.option_id, committed_at_idx: 1 },
        replies: phase === "PRESSURE" ? [{ speaker: "relative", text: "Synthetic pressure" }] : [],
        pressure_turns_allowed: phase === "PRESSURE" ? 2 : null,
      } });
    }
    if (request.url().endsWith("/turns")) {
      phase = "CLOSING";
      return route.fulfill({ status: 200, headers, contentType: "application/json", json: {
        turn_idx: 2, replies: [{ speaker: "relative", text: "Synthetic reply" }],
        phase, clarification: false, turns_remaining: 0, degraded: false,
      } });
    }
    return route.fulfill({ status: 200, headers, contentType: "application/json", json: {
      status: "completed", report_ready: true, report_url: "javascript:alert(1)",
    } });
  });
  return submitted;
}

async function noHorizontalOverflow(page: Page) {
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(360);
}

test("Decision A confirms twice, then Closing completes at 360px", async ({ page }) => {
  const submitted = await setup(page, "A");
  await page.goto("/decision");
  await expect(page.getByText(t("status.draftFull"))).toBeVisible();
  await expect(page.getByText(t("banner.educationOnly"))).toBeVisible();
  await page.getByRole("radio", { name: "Refer" }).check();
  await page.getByRole("button", { name: t("decision.review") }).click();
  expect(submitted).toHaveLength(0);
  await expect(page.getByText(t("decision.irreversible"))).toBeVisible();
  await page.getByRole("button", { name: t("decision.confirm") }).click();
  await expect(page).toHaveURL(/\/closing$/);
  await expect(page.getByText(t("status.draftFull"))).toBeVisible();
  await noHorizontalOverflow(page);
  await page.getByRole("button", { name: t("closing.complete") }).click();
  await expect(page).toHaveURL(/\/report$/);
  expect(submitted.map((item) => item.url.split("/").at(-1))).toEqual(["decision", "complete"]);
  expect(submitted[0]?.body.option_id).toBe("refer");
});

test("Variant C enters pressure chat before Closing", async ({ page }) => {
  const submitted = await setup(page, "C");
  await page.goto("/decision");
  await page.getByRole("radio", { name: "Refer" }).check();
  await page.getByRole("button", { name: t("decision.review") }).click();
  await page.getByRole("button", { name: t("decision.confirm") }).click();
  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.getByText(t("chat.pressure"))).toBeVisible();
  await page.getByRole("textbox", { name: t("chat.messageLabel") }).fill("Response");
  await page.getByRole("button", { name: t("chat.send") }).click();
  await expect(page.getByRole("link", { name: t("chat.toClosing") })).toBeVisible();
  await page.getByRole("link", { name: t("chat.toClosing") }).click();
  await expect(page).toHaveURL(/\/closing$/);
  await noHorizontalOverflow(page);
  expect(submitted.map((item) => item.url.split("/").at(-1))).toEqual(["decision", "turns"]);
});
