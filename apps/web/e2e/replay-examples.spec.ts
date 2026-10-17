import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { t } from "../lib/i18n";

test("the learner gallery plays a shipped course example without review notices", async ({ page }) => {
  const cases = ["dad-001", "dad-002", "mom-001", "mom-002", "pp-001", "stf-002"];
  const recordings = cases.map((id) => JSON.parse(readFileSync(resolve(__dirname, `../../../recordings/${id}-example.json`), "utf8")));
  await page.route("**/v1/replay/recordings**", (route) => {
    const id = route.request().url().split("/").pop();
    const selected = recordings.find((item) => item.recording_id === id);
    return route.fulfill({
      status: 200, contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": "*" },
      json: selected ?? { items: recordings.map((item) => ({ ...item, status: item.case.status })) },
    });
  });
  await page.goto("/replay");
  await expect(page.getByRole("button", { name: t("replay.open") })).toHaveCount(6);
  await expect(page.getByText(t("replay.unavailable"))).toHaveCount(0);
  await expect(page.getByText(t("status.draftFull"))).toHaveCount(0);
  await expect(page.getByText(t("banner.educationOnly"))).toHaveCount(0);
  await page.getByRole("button", { name: t("replay.open") }).first().click();
  const reply = recordings[0].steps.find((step: { type: string }) => step.type === "reply");
  await expect(page.getByText(reply.text, { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: t("replay.pause") }).click();
  await expect(page.getByRole("button", { name: t("replay.resume") })).toBeVisible();
});
