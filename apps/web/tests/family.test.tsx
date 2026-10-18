// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { FamilySimulator } from "@/components/family-simulator";
import { t } from "@/lib/i18n";

const room = {
  room_id: "11111111-1111-1111-1111-111111111111", story_id: "first-night", title_th: "Family story",
  role: "mother", private_brief_th: "Only mother's context", partner_joined: true,
  state_version: 0, total_steps: 2, transcript: [], report: null,
  scene: { id: "first", chapter_th: "First night", role: "mother", speaker_th: "Partner",
    prompt_th: "What help do you need?", choices: [{ id: "share", text_th: "Ask for rest" }] },
};
beforeEach(() => sessionStorage.clear());
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("creates a room, shows only its role brief, and preserves the decision ID on retry", async () => {
  let fail = true;
  const sent: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (path.endsWith("/stories")) return Response.json([{ id: "first-night", title_th: "Family story", description_th: "Practice together", mode: "coop", chapters_th: ["First night"] }]);
    if (path.endsWith("/decisions")) {
      sent.push(await request.text());
      if (fail) { fail = false; return Response.json({ error: { code: "VALIDATION_ERROR" } }, { status: 500 }); }
      return Response.json({ ...room, state_version: 1, scene: { ...room.scene, role: "father", choices: [] } });
    }
    if (request.method === "POST") return Response.json({ room_id: room.room_id, token: "host-token", invite: "invite-token" });
    return Response.json(room);
  }));
  render(<FamilySimulator storyId="first-night" />);
  const create = await screen.findByRole("button", { name: t("family.create") });
  await waitFor(() => expect((create as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(create);
  expect(await screen.findByText(room.private_brief_th)).not.toBeNull();
  fireEvent.click(await screen.findByRole("button", { name: "Ask for rest" }));
  fireEvent.click(await screen.findByRole("button", { name: t("family.retry") }));
  await screen.findByText(t("family.partnerTurn"));
  expect(sent).toHaveLength(2);
  expect(sent[0]).toBe(sent[1]);
});

it("restores a session and keeps the partner's choices out of the screen", async () => {
  sessionStorage.setItem("sim-tamy-family:first-night", JSON.stringify({ room_id: room.room_id, token: "partner-token" }));
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => Response.json(
    request.url.endsWith("/stories") ? [] : { ...room, role: "father", private_brief_th: "Only father's context", scene: { ...room.scene, choices: [] } },
  )));
  render(<FamilySimulator storyId="first-night" />);
  expect(await screen.findByText("Only father's context")).not.toBeNull();
  expect(screen.queryByText(room.private_brief_th)).toBeNull();
  expect(screen.queryByRole("button", { name: "Ask for rest" })).toBeNull();
});
