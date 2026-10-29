import { demoStorage } from "./fixtures/account";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { t } from "../lib/i18n";

const apiUrl = "http://127.0.0.1:8000";
type View = components["schemas"]["FamilyView"];

async function enter(page: Page) {
  const gate = page.getByRole("button", { name: t("experience.enterChapter"), exact: true });
  await expect(gate.or(page.getByLabel(t("lab.chat.label"))).or(page.getByRole("radio").first()).first()).toBeVisible();
  if (await gate.isVisible()) await gate.click();
}

for (const [id, stage] of [["thai-elements-family", 1], ["thai-birth-conversation", 2], ["thai-milk-family", 4]] as const) {
  test(`${id}: lesson link, real typed reply, decisions and report at 360px`, async ({ page, browser }) => {
    expect(await (await page.request.get(`${apiUrl}/health`)).json()).toMatchObject({ db: "ok", llm_provider: "mock" });
    await page.goto(`/learn/${stage}`);
    await page.locator(`a[href="/simulate/${id}"]`).first().click();
    const created = page.waitForResponse((r) => r.request().method() === "POST" && /\/family\/rooms$/.test(r.url()));
    await page.getByRole("button", { name: t("family.create"), exact: true }).click();
    const saved = await (await created).json() as components["schemas"]["FamilyCreated"];
    const read = async () => (await (await page.request.get(`${apiUrl}/v1/family/rooms/${saved.room_id}`, {
      headers: { Authorization: `Bearer ${saved.token}` },
    })).json()) as View;
    const partnerContext = id === "thai-milk-family" ? await browser.newContext({ storageState: demoStorage(), viewport: { width: 360, height: 780 } }) : null;
    const partner = partnerContext ? await partnerContext.newPage() : null;
    try {
      if (partner) {
        await partner.goto(await page.locator("#family-share").inputValue());
        await partner.getByRole("button", { name: t("family.join"), exact: true }).click();
        await expect.poll(async () => (await read()).partner_joined).toBe(true);
      }
      let view = await read();
      const question = readFileSync(resolve(__dirname, `../../../content/family/${id}.yaml`), "utf8")
        .match(/examples_th:\s*\[([^,\]]+)/)?.[1]?.trim();
      if (view.scene?.kind === "discover") {
        expect(question).toBeTruthy();
        await enter(page);
        await page.getByLabel(t("lab.chat.label")).fill(question!);
        const response = page.waitForResponse((r) => r.request().method() === "POST" && /\/messages$/.test(r.url()));
        await page.getByRole("button", { name: t("lab.chat.send") }).click();
        const reply = await (await response).json() as components["schemas"]["FamilyMessageResult"];
        expect(reply.reply?.citations.length).toBeGreaterThan(0);
      }
      for (let step = 0; step < view.total_steps; step++) {
        view = await read();
        const scene = view.scene!;
        const actors = scene.joint ? [page, partner!] : [scene.role === "father" && partner ? partner : page];
        for (const actor of actors) {
          await enter(actor);
          if (scene.kind === "discover") {
            await actor.getByRole("button", { name: scene.choices[0]!.text_th, exact: true }).click();
          } else {
            await actor.getByRole("radio").first().check();
            await actor.getByRole("button", { name: t("experience.commit"), exact: true }).click();
          }
        }
        await expect.poll(async () => (await read()).completed_steps).toBe(step + 1);
      }
      await expect(page.getByRole("heading", { name: t("lab.report.dimensions") })).toBeVisible();
      await expect(page.getByRole("heading", { name: t("lab.debrief.title") })).toBeVisible();
      expect((await read()).report?.score_total).not.toBeNull();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    } finally {
      await partnerContext?.close();
    }
  });
}
