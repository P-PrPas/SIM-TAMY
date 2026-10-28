// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { FamilySimulator } from "@/components/family-simulator";
import { PIXEL_STORIES, isPixelStory } from "@/components/pixel/registry";
import { t } from "@/lib/i18n";

// Pretend the co-op story is a pixel story, as a later stage PR would by adding its id to the set.
const COOP = "golden-first-night";
vi.mock("@/components/pixel/registry", async (original) => {
  const real = await original<typeof import("@/components/pixel/registry")>();
  return { ...real, isPixelStory: (id: string) => real.isPixelStory(id) || id === "golden-first-night" };
});

const ROOM = "55555555-5555-5555-5555-555555555555";
const mine = [{ id: "m-feed", role: "mother", text_th: "Fed less", shared: false }, { id: "m-sleepy", role: "mother", text_th: "Sleepy", shared: true }];
const scene = (extra = {}) => ({
  id: "joint", chapter_th: "Ch", role: "mother", speaker_th: "Elder", prompt_th: "Decide together", joint: true,
  vote: { my_choice_id: null, waiting_for_partner: false, disagreement: null }, card: null, kind: "choice", character_th: null,
  accepts_text: false, can_continue: false, examples_th: [], choices: [{ id: "a", text_th: "Option A" }, { id: "b", text_th: "Option B" }], ...extra,
});
const view = (extra = {}) => ({
  room_id: ROOM, story_id: COOP, title_th: "Golden", role: "mother", private_brief_th: "Mother brief", partner_joined: true, partner_online: true,
  state_version: 2, completed_steps: 1, total_steps: 4, transcript: [], report: null, my_facts: mine,
  shared_facts: [mine[1]], dialogue: [], scene: scene(), ...extra,
});
const speaker = { selector: ".pixel-line p" };

function serve(handler: (request: Request) => Response | Promise<Response> = () => Response.json(view()), story = COOP, mode = "coop") {
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => request.url.endsWith("/stories")
    ? Response.json([{ id: story, title_th: "t", description_th: "d", mode, chapters_th: [] }]) : handler(request)));
}
const open = (story = COOP) => sessionStorage.setItem(`sim-tamy-family:${story}`, JSON.stringify({ room_id: ROOM, token: "tok" }));

beforeEach(() => {
  open(); serve();
  vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener() {}, removeEventListener() {} }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear(); });

it("registers the chapter-1 story and answers by exact id", async () => {
  const real = await vi.importActual<typeof import("@/components/pixel/registry")>("@/components/pixel/registry");
  expect([...real.PIXEL_STORIES]).toContain("thai-elements-family"); // stage PRs only add ids, so do not pin the whole list
  expect(real.isPixelStory("thai-elements-family")).toBe(true);
  expect(real.isPixelStory("not-a-story")).toBe(false);
  expect(PIXEL_STORIES.has("thai-elements-family")).toBe(true);
  expect(isPixelStory(COOP)).toBe(true); // the mocked registry used by the rest of this file
});

it("puts brief and facts in an open details at the top of the panel, not a dialog", async () => {
  const { container } = render(<FamilySimulator storyId={COOP} />);
  const know = await waitFor(() => {
    const el = container.querySelector(".pixel-panel > details.pixel-know");
    expect(el).not.toBeNull();
    return el as HTMLDetailsElement;
  });
  expect(know.open).toBe(true); // an unshared fact exists
  expect(know.parentElement?.firstElementChild).toBe(know); // top of the panel
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(know.textContent).toContain(t("pixelSim.know.title"));
  expect(know.textContent).toContain("Mother brief");
  expect(know.textContent).toContain("Fed less");
  expect(know.textContent).toContain(t("family.cosim.timeline.title"));
  expect(container.querySelector(".family-room-sidebar")).toBeNull();
});

it("collapses the section once every fact is shared", async () => {
  serve(() => Response.json(view({ my_facts: mine.map((f) => ({ ...f, shared: true })) })));
  const { container } = render(<FamilySimulator storyId={COOP} />);
  await screen.findByText("Decide together", speaker);
  const know = container.querySelector("details.pixel-know") as HTMLDetailsElement;
  expect(know.open).toBe(false);
  expect(know.textContent).toContain("Mother brief"); // still readable on demand
});

it("shares a fact from the panel", async () => {
  const sent: Record<string, unknown>[] = [];
  serve(async (request) => {
    if (request.url.endsWith("/shares")) { sent.push(await request.json()); return Response.json(view({ my_facts: mine.map((f) => ({ ...f, shared: true })) })); }
    return Response.json(view());
  });
  const { container } = render(<FamilySimulator storyId={COOP} />);
  fireEvent.click(await screen.findByRole("button", { name: t("family.cosim.facts.share") }));
  await waitFor(() => expect(sent).toHaveLength(1));
  expect(sent[0]).toMatchObject({ fact_id: "m-feed" });
  await waitFor(() => expect((container.querySelector("details.pixel-know") as HTMLDetailsElement).open).toBe(false));
});

it("renders no section without a brief or facts", async () => {
  serve(() => Response.json(view({ private_brief_th: "", my_facts: [], shared_facts: [] })));
  const { container } = render(<FamilySimulator storyId={COOP} />);
  await screen.findByText("Decide together", speaker);
  expect(container.querySelector(".pixel-know")).toBeNull();
});

it("shows partner presence in the HUD with a text equivalent", async () => {
  serve(() => Response.json(view({ partner_online: false })));
  const { container } = render(<FamilySimulator storyId={COOP} />);
  await screen.findByText("Decide together", speaker);
  expect(container.querySelector(".pixel-hud .pixel-partner.is-offline")?.textContent).toBe(t("pixelSim.partner.offline"));
  cleanup();
  serve();
  const online = render(<FamilySimulator storyId={COOP} />);
  await waitFor(() => expect(online.container.querySelector(".pixel-partner.is-online")?.textContent).toBe(t("pixelSim.partner.online")));
});

it("omits presence for solo stories", async () => {
  const solo = "thai-elements-family";
  open(solo);
  serve(() => Response.json(view({ story_id: solo, partner_online: false })), solo, "solo");
  const { container } = render(<FamilySimulator storyId={solo} />);
  await screen.findByText("Decide together", speaker);
  expect(container.querySelector(".pixel-partner")).toBeNull();
});

it("says what is awaited when the partner has not joined and keeps the invite reachable", async () => {
  serve(() => Response.json(view({ partner_joined: false, partner_online: false })));
  const { container } = render(<FamilySimulator storyId={COOP} />);
  expect(await screen.findByText(t("family.waitPartner"), { selector: ".family-turn-status" })).not.toBeNull();
  expect(container.querySelector(".pixel-partner.is-waiting")?.textContent).toBe(t("pixelSim.partner.waiting"));
  expect(container.querySelector(".family-invite-panel")).not.toBeNull();
  expect(container.querySelectorAll("#family-facts-title")).toHaveLength(1); // facts only in the panel, never twice
  expect((screen.getByRole("radio", { name: "Option A" }).closest("fieldset") as HTMLFieldSetElement).disabled).toBe(true);
  expect((screen.getByRole("button", { name: t("family.cosim.facts.share") }) as HTMLButtonElement).disabled).toBe(true);
});

it("shows the partner's turn status instead of leaving the panel empty", async () => {
  serve(() => Response.json(view({ scene: scene({ role: "father", joint: false, vote: null, choices: [] }) })));
  const { container } = render(<FamilySimulator storyId={COOP} />);
  expect(await screen.findByText(t("family.partnerTurn"), { selector: ".family-turn-status" })).not.toBeNull();
  expect(container.querySelector(".pixel-line.is-speaker")?.textContent).toContain("Decide together");
  expect(container.querySelector(".pixel-cards")).toBeNull();
});

it("hides cards and the partner's vote after I vote on a joint step", async () => {
  let phase = 0;
  serve(async (request) => {
    if (request.url.endsWith("/decisions")) phase = 1;
    if (phase === 0) return Response.json(view());
    return Response.json(view({ state_version: 3, scene: scene({ choices: [], vote: { my_choice_id: "a", waiting_for_partner: true, disagreement: null } }) }));
  });
  const { container } = render(<FamilySimulator storyId={COOP} />);
  fireEvent.click(await screen.findByRole("radio", { name: "Option A" }));
  fireEvent.click(screen.getByRole("button", { name: t("experience.commit") }));
  expect(await screen.findByText(t("family.cosim.joint.waiting"), { selector: ".family-vote-waiting" })).not.toBeNull();
  expect(screen.getByText(t("family.cosim.joint.waiting"), { selector: ".family-turn-status" })).not.toBeNull();
  expect(container.querySelector(".pixel-panel .family-vote")).not.toBeNull();
  expect(screen.queryByRole("radio")).toBeNull();
  expect(screen.queryByText("Option B")).toBeNull();
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("shows both choices only when the pair disagrees", async () => {
  serve(() => Response.json(view({ scene: scene({ vote: { my_choice_id: null, waiting_for_partner: false,
    disagreement: [{ role: "mother", choice_id: "a", text_th: "Mother picked A" }, { role: "father", choice_id: "b", text_th: "Father picked B" }] } }) })));
  render(<FamilySimulator storyId={COOP} />);
  const alert = await screen.findByRole("alert");
  expect(alert.textContent).toContain("Mother picked A");
  expect(alert.textContent).toContain("Father picked B");
  expect(screen.getByRole("radio", { name: "Option B" })).not.toBeNull();
});

it("keeps the classic layout for non-pixel stories", async () => {
  const other = "gs-b-thai-recovery";
  open(other);
  serve(() => Response.json(view({ story_id: other })), other);
  const { container } = render(<FamilySimulator storyId={other} />);
  await screen.findByText("Decide together");
  expect(container.querySelector(".pixel-know")).toBeNull();
  expect(container.querySelector(".pixel-partner")).toBeNull();
  expect(container.querySelector(".family-room-sidebar .family-private")).not.toBeNull();
  expect(container.querySelector(".family-room-sidebar .family-facts")).not.toBeNull();
});
