// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { FamilySimulator } from "@/components/family-simulator";
import { t } from "@/lib/i18n";

const base = {
  room_id: "22222222-2222-2222-2222-222222222222", story_id: "golden-first-night", title_th: "Golden",
  role: "mother", private_brief_th: "Mother brief", partner_joined: true, partner_online: true,
  state_version: 2, completed_steps: 2, total_steps: 6, transcript: [], report: null,
  my_facts: [{ id: "m-feed", role: "mother", text_th: "Fed less", shared: false }, { id: "m-sleepy", role: "mother", text_th: "Sleepy", shared: true }],
  shared_facts: [{ id: "m-sleepy", role: "mother", text_th: "Sleepy", shared: true }],
  scene: { id: "joint", chapter_th: "Joint", role: "mother", speaker_th: "Elder", prompt_th: "Decide together", joint: true,
    vote: { my_choice_id: null, waiting_for_partner: false, disagreement: null },
    card: { tradition_th: "Tradition X", learning_point_th: "Point", evidence_status: "traditional_practice", precautions_th: ["Careful"], when_to_consult_th: "Consult", sources: [{ id: "S", title_th: "Source title", url: "https://example.org" }] },
    choices: [{ id: "a", text_th: "Option A" }, { id: "b", text_th: "Option B" }] },
};

beforeEach(() => sessionStorage.setItem("sim-tamy-family:golden-first-night", JSON.stringify({ room_id: base.room_id, token: "tok" })));
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear(); });

function serve(handler: (request: Request) => Response | Promise<Response>) {
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/stories") ? Response.json([{ id: "golden-first-night", title_th: "t", description_th: "d", mode: "coop", chapters_th: [] }]) : handler(request)));
}

it("shows own facts with a share action, the shared timeline, presence, card and progress by completed steps", async () => {
  const sent: Record<string, unknown>[] = [];
  serve(async (request) => {
    if (request.url.endsWith("/shares")) { sent.push(await request.json()); return Response.json({ ...base, my_facts: base.my_facts.map((f) => ({ ...f, shared: true })) }); }
    return Response.json(base);
  });
  render(<FamilySimulator storyId="golden-first-night" />);
  expect(await screen.findByText("Fed less")).not.toBeNull();
  expect(screen.getByText(t("family.cosim.presence.online"))).not.toBeNull();
  expect(screen.getByText(`2 / 6 ${t("family.decisions")}`)).not.toBeNull();
  expect(screen.getByText("Tradition X")).not.toBeNull();
  expect(screen.getByText(t("family.cosim.card.status.traditional_practice"))).not.toBeNull();
  expect(screen.getByRole("link", { name: "Source title" }).getAttribute("href")).toBe("https://example.org");
  expect(screen.getAllByRole("button", { name: t("family.cosim.facts.share") })).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: t("family.cosim.facts.share") }));
  await waitFor(() => expect(sent).toHaveLength(1));
  expect(sent[0]).toMatchObject({ fact_id: "m-feed" });
  expect(typeof sent[0]?.client_turn_id).toBe("string");
});

it("hides choices and the partner's vote after voting, then reveals both choices on disagreement", async () => {
  let phase = 0;
  serve(async (request) => {
    if (request.url.endsWith("/decisions")) { phase = 1; }
    if (phase === 0) return Response.json(base);
    if (phase === 1) return Response.json({ ...base, scene: { ...base.scene, choices: [], vote: { my_choice_id: "a", waiting_for_partner: true, disagreement: null } } });
    return Response.json(base);
  });
  render(<FamilySimulator storyId="golden-first-night" />);
  fireEvent.click(await screen.findByRole("radio", { name: "Option A" }));
  fireEvent.click(screen.getByRole("button", { name: t("experience.commit") }));
  expect(await screen.findByText(t("family.cosim.joint.waiting"), { selector: ".family-vote-waiting" })).not.toBeNull();
  expect(screen.queryByRole("radio", { name: "Option A" })).toBeNull();
  expect(screen.queryByText("Option B")).toBeNull();
});

it("renders both choices with an alert when the pair disagrees and allows a new vote", async () => {
  serve(async () => Response.json({ ...base, scene: { ...base.scene, vote: { my_choice_id: null, waiting_for_partner: false,
    disagreement: [{ role: "mother", choice_id: "a", text_th: "Mother picked A" }, { role: "father", choice_id: "b", text_th: "Father picked B" }] } } }));
  render(<FamilySimulator storyId="golden-first-night" />);
  const alert = await screen.findByRole("alert");
  expect(alert.textContent).toContain(t("family.cosim.joint.needAgree"));
  expect(alert.textContent).toContain("Mother picked A");
  expect(alert.textContent).toContain("Father picked B");
  expect(screen.getByRole("radio", { name: "Option B" })).not.toBeNull();
});

it("shows the partner as offline when presence is false", async () => {
  serve(async () => Response.json({ ...base, partner_online: false }));
  render(<FamilySimulator storyId="golden-first-night" />);
  expect(await screen.findByText(t("family.cosim.presence.offline"))).not.toBeNull();
});

it("tells the learner when the story is not offered by the API", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json([])));
  render(<FamilySimulator storyId="golden-first-night" />);
  expect(await screen.findByText(t("family.cosim.unavailable"))).toBeTruthy();
});
