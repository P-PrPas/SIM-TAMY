// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "../app/login/page";
import { DEMO_PASSWORD, LOGIN_KEY, loginDestination, readLogin, setLogin } from "../lib/demo-login";
import { t } from "../lib/i18n";
import type { DemoAccount } from "../lib/v2-api";

const mock = vi.hoisted(() => ({ path: "/login", replace: vi.fn() }));
vi.mock("next/navigation", () => ({ usePathname: () => mock.path, useRouter: () => ({ replace: mock.replace }) }));
vi.mock("next/image", () => ({ default: () => null }));
const learner: DemoAccount = { id: "parent-1", role: "learner", org_id: "org-1", display_name_th: "Learner one" };
const staff: DemoAccount = { id: "staff-1", role: "educator", org_id: "org-1", display_name_th: "Educator one" };
beforeEach(() => {
  localStorage.clear(); sessionStorage.clear(); mock.replace.mockReset(); mock.path = "/login";
  history.replaceState({}, "", "/");
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ items: [learner, staff] })));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("demo login", () => {
  it("autofills only, rejects a wrong password, then signs in and restores a learner destination", async () => {
    history.replaceState({}, "", "/login?next=/profile");
    render(<LoginPage />);
    fireEvent.click(screen.getByText(t("platform.login.choose")));
    const picker = await screen.findByLabelText(t("platform.login.account"));
    fireEvent.change(picker, { target: { value: learner.id } });
    expect(screen.getByLabelText(t("platform.login.username"))).toHaveProperty("value", learner.id);
    expect(screen.getByLabelText(t("platform.login.password"))).toHaveProperty("value", DEMO_PASSWORD);
    expect(localStorage.getItem(LOGIN_KEY)).toBeNull();
    fireEvent.change(screen.getByLabelText(t("platform.login.password")), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: t("platform.login.submit") }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", t("platform.login.invalid"));
    expect(mock.replace).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText(t("platform.login.password")), { target: { value: DEMO_PASSWORD } });
    fireEvent.click(screen.getByRole("button", { name: t("platform.login.submit") }));
    expect(mock.replace).toHaveBeenCalledWith("/profile");
    expect(readLogin(localStorage.getItem(LOGIN_KEY))).toEqual(learner);
    expect(localStorage.getItem(LOGIN_KEY)).not.toContain(DEMO_PASSWORD);
  });

  it("redirects institution accounts to their workspace and rejects external return paths", () => {
    expect(loginDestination(staff, "/learn/1")).toBe("/institution");
    for (const path of ["//example.org", "https://example.org", "/institution", "/login"]) expect(loginDestination(learner, path)).toBe("/");
    expect(readLogin("bad JSON")).toBeNull();
    expect(readLogin(JSON.stringify({ id: "staff", role: "educator", org_id: null }))).toBeNull();
  });

  it("keeps room credentials for the same account, clears them when switching or logging out", () => {
    setLogin(learner);
    sessionStorage.setItem("sim-tamy-session", "private");
    sessionStorage.setItem("sim-tamy-family:story", "private");
    sessionStorage.setItem("other-app", "keep");
    setLogin(learner);
    expect(sessionStorage.getItem("sim-tamy-session")).toBe("private");
    setLogin(staff);
    expect(sessionStorage.getItem("sim-tamy-session")).toBeNull();
    expect(sessionStorage.getItem("sim-tamy-family:story")).toBeNull();
    setLogin(null);
    expect(readLogin(localStorage.getItem(LOGIN_KEY))).toBeNull();
    expect(localStorage.getItem("sim-tamy-demo-account")).toBeNull();
    expect(sessionStorage.getItem("other-app")).toBe("keep");
  });
});

