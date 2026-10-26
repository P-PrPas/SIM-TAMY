import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { t } from "../lib/i18n";

type View = components["schemas"]["FamilyView"];
const API = "http://127.0.0.1:8000/v1/family/rooms";

async function view(request: APIRequestContext, saved: { room_id: string; token: string }) {
  const response = await request.get(`${API}/${saved.room_id}`, { headers: { Authorization: `Bearer ${saved.token}` } });
  return await response.json() as View;
}

async function choose(page: Page, request: APIRequestContext, saved: { room_id: string; token: string }, choiceId: string) {
  const text = (await view(request, saved)).scene!.choices.find((choice) => choice.id === choiceId)!.text_th;
  const enter = page.getByRole("button", { name: t("experience.enterChapter"), exact: true });
  const radio = page.getByRole("radio", { name: text, exact: true });
  await expect(enter.or(radio)).toBeVisible();
  if (await enter.isVisible()) await enter.click();
  await radio.check();
  await page.getByRole("button", { name: t("experience.commit"), exact: true }).click();
}

test("two devices share private facts, disagree, re-vote and lock a joint decision", async ({ page, browser, request }) => {
  await page.goto("/golden");
  await page.getByRole("button", { name: t("family.create"), exact: true }).click();
  const link = await page.locator("#family-share").inputValue();
  const partnerContext = await browser.newContext({ viewport: { width: 360, height: 780 } });
  try {
    const partner = await partnerContext.newPage();
    await partner.goto(link);
    await partner.getByRole("button", { name: t("family.join"), exact: true }).click();
    await expect(partner.getByText(t("family.private"), { exact: true })).toBeVisible();
    await expect(page.getByText(t("family.cosim.presence.online"))).toBeVisible({ timeout: 15_000 });
    const [mother, father] = await Promise.all([page, partner].map((tab) => tab.evaluate(() =>
      JSON.parse(sessionStorage.getItem("sim-tamy-family:golden-first-night")!) as { room_id: string; token: string })));
    const first = await view(request, mother!);
    const motherFact = first.my_facts!.find((fact) => fact.id === "m-feed")!.text_th;
    const fatherFact = (await view(request, father!)).my_facts!.find((fact) => fact.id === "f-nappy")!.text_th;

    // Asymmetry: the partner never sees an unshared fact, in the page or in the API.
    await expect(partner.getByText(motherFact)).toHaveCount(0);
    expect(JSON.stringify(await view(request, father!))).not.toContain(motherFact);
    await page.getByText(motherFact).locator("xpath=..").getByRole("button", { name: t("family.cosim.facts.share") }).click();
    await expect(partner.locator(".family-timeline").getByText(motherFact)).toBeVisible({ timeout: 15_000 });
    await partner.getByText(fatherFact).locator("xpath=..").getByRole("button", { name: t("family.cosim.facts.share") }).click();
    await expect(page.locator(".family-timeline").getByText(fatherFact)).toBeVisible({ timeout: 15_000 });

    await choose(page, request, mother!, "say-what-you-see");
    await expect.poll(async () => (await view(request, mother!)).completed_steps).toBe(1);
    await choose(partner, request, father!, "share-and-listen");
    await expect.poll(async () => (await view(request, mother!)).completed_steps).toBe(2);
    await choose(page, request, mother!, "listen-then-ask");
    await expect.poll(async () => (await view(request, mother!)).scene?.joint).toBe(true);

    // Mismatch: the partner's vote stays hidden until both have voted.
    await choose(page, request, mother!, "contact-health-service");
    await expect(page.locator(".family-vote-waiting")).toBeVisible();
    expect(JSON.stringify((await view(request, father!)).scene!.vote)).not.toContain("contact-health-service");
    await choose(partner, request, father!, "wait-until-morning");
    for (const tab of [page, partner]) {
      await expect(tab.getByRole("alert").filter({ hasText: t("family.cosim.joint.needAgree") })).toBeVisible({ timeout: 15_000 });
    }
    // Agree: both re-vote the same option and the decision locks.
    await choose(page, request, mother!, "contact-health-service");
    await choose(partner, request, father!, "contact-health-service");
    await expect.poll(async () => (await view(request, mother!)).scene?.id).toBe("consequence");
    await choose(partner, request, father!, "report-observations");
    await expect.poll(async () => (await view(request, mother!)).completed_steps).toBe(5);
    await choose(page, request, mother!, "agree-share-and-ask");
    await expect(page.getByRole("heading", { name: t("family.report") })).toBeVisible();
    expect((await view(request, father!)).report!.safety_status).toBe("SAFETY_MET");
  } finally { await partnerContext.close(); }
});
