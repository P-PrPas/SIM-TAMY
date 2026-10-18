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
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

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

it("lets a learner recover when a restored role token is no longer usable", async () => {
  sessionStorage.setItem("sim-tamy-family:first-night", JSON.stringify({ room_id: room.room_id, token: "invalid-token" }));
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/stories")
    ? Response.json([{ id: "first-night", title_th: "Family story", description_th: "Practice together", mode: "coop", chapters_th: [] }])
    : Response.json({ error: { code: "UNAUTHORIZED" } }, { status: 401 })));
  render(<FamilySimulator storyId="first-night" />);
  await screen.findByText(t("family.unauthorized"));
  fireEvent.click(screen.getByRole("button", { name: t("family.leave") }));
  expect(sessionStorage.getItem("sim-tamy-family:first-night")).toBeNull();
  expect(await screen.findByRole("button", { name: t("family.create") })).not.toBeNull();
});

it.each([false, true])("copies an invitation or explains manual copying when clipboard fails: %s", async (fails) => {
  const writeText = vi.fn<(text: string) => Promise<void>>().mockImplementation(() => fails ? Promise.reject(new Error("Clipboard unavailable")) : Promise.resolve());
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  sessionStorage.setItem("sim-tamy-family:first-night", JSON.stringify({ room_id: room.room_id, token: "host-token", invite: "test-invite" }));
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => Response.json(request.url.endsWith("/stories") ? [] : { ...room, partner_joined: false })));
  render(<FamilySimulator storyId="first-night" />);
  fireEvent.click(await screen.findByRole("button", { name: t("family.design.copy") }));
  await screen.findByText(t(fails ? "family.design.copyManual" : "family.design.copySuccess"));
  expect(writeText).toHaveBeenCalledOnce();
  expect(writeText.mock.calls[0]?.[0]).toContain(`#room=${room.room_id}&invite=test-invite`);
});

it("keeps the latest reply visible and earlier conversation available on demand", async () => {
  sessionStorage.setItem("sim-tamy-family:first-night", JSON.stringify({ room_id: room.room_id, token: "host-token" }));
  const turn = { idx: 1, role: "mother", speaker_th: "Partner", prompt_th: "First prompt", text_th: "Earlier choice", reply_th: "Earlier reply" };
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => Response.json(request.url.endsWith("/stories") ? [] : { ...room, transcript: [turn, { ...turn, idx: 2, text_th: "Latest choice", reply_th: "Latest reply" }] })));
  render(<FamilySimulator storyId="first-night" />);
  expect(await screen.findByText("Latest reply")).not.toBeNull();
  const earlier = screen.getByText("Earlier reply").closest("details");
  expect(earlier?.open).toBe(false);
  fireEvent.click(screen.getByText(t("family.design.history")));
  await waitFor(() => expect(earlier?.open).toBe(true));
});

it("stops polling after a decision completes the report", async () => {
  const startTimer = vi.spyOn(window, "setInterval");
  const clearTimer = vi.spyOn(window, "clearInterval");
  sessionStorage.setItem("sim-tamy-family:first-night", JSON.stringify({ room_id: room.room_id, token: "host-token" }));
  const fetch = vi.fn(async (request: Request) => Response.json(request.url.endsWith("/stories") ? []
    : request.url.endsWith("/decisions") ? { ...room, scene: null, report: { safety_status: "SAFETY_MET", competencies: [], evidence: [], sources: [] } } : room));
  vi.stubGlobal("fetch", fetch);
  render(<FamilySimulator storyId="first-night" />);
  const choice = await screen.findByRole("button", { name: "Ask for rest" });
  const timer = startTimer.mock.results[startTimer.mock.calls.findIndex(([, delay]) => delay === 3000)]?.value;
  expect(timer).toBeDefined();
  fireEvent.click(choice);
  await screen.findByRole("heading", { name: t("family.report") });
  expect(clearTimer).toHaveBeenCalledWith(timer);
  expect(startTimer.mock.calls.filter(([, delay]) => delay === 3000)).toHaveLength(1);
});

it("joins and decides without randomUUID on an HTTP LAN browser", async () => {
  vi.stubGlobal("crypto", { getRandomValues: crypto.getRandomValues.bind(crypto) });
  const sent: Record<string, unknown>[] = [];
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => {
    if (request.url.endsWith("/stories")) return Response.json([]);
    if (request.method === "POST") sent.push(await request.json());
    return Response.json(room);
  }));
  render(<FamilySimulator storyId="first-night" />);
  fireEvent.change(await screen.findByLabelText(t("family.invitation")), { target: { value: `http://192.168.1.2/family#room=${room.room_id}&invite=secret` } });
  fireEvent.click(screen.getByRole("button", { name: t("family.join") }));
  fireEvent.click(await screen.findByRole("button", { name: "Ask for rest" }));
  await waitFor(() => expect(sent).toHaveLength(2));
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  expect(sent[0]?.participant_token).toMatch(uuid);
  expect(sent[1]?.client_turn_id).toMatch(uuid);
});
