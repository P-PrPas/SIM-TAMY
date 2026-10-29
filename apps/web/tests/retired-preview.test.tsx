// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import JoinPage from "../app/lab/solo/page";
import RetiredReplayPage from "../app/replay/page";

const mocks = vi.hoisted(() => ({ redirect: vi.fn(), get: vi.fn().mockResolvedValue({ data: { items: [] } }) }));
vi.mock("next/navigation", () => ({ permanentRedirect: mocks.redirect, useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api/runtime", () => ({ api: () => ({ GET: mocks.get }) }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("redirects retired example bookmarks to the simulation lab", () => {
  RetiredReplayPage();
  expect(mocks.redirect).toHaveBeenCalledWith("/lab");
  expect(mocks.get).not.toHaveBeenCalled();
});

it("offers no recorded-example entry point from solo practice", () => {
  render(<JoinPage />);
  expect(screen.queryAllByRole("link").map((link) => link.getAttribute("href"))).not.toContain("/replay");
});
