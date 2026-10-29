// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AnalyticsPage from "../app/institution/analytics/page";
import CohortDetailPage from "../app/institution/cohorts/[id]/page";
import CohortsPage from "../app/institution/cohorts/page";
import LibraryPage from "../app/institution/library/page";
import OverviewPage from "../app/institution/page";
import StaffPage from "../app/institution/staff/page";
import JoinCodePage from "../app/join/[code]/page";
import { InstitutionShell } from "../components/institution-shell";
import { ApiError } from "../lib/api/client";
import { getDemoAccount } from "../lib/demo-account";
import { setLogin } from "../lib/demo-login";
import type { DemoAccount } from "../lib/v2-api";
import { t } from "../lib/i18n";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  remove: vi.fn(),
  push: vi.fn(),
  params: {} as Record<string, string>,
  search: new URLSearchParams(),
}));
vi.mock("@/lib/api/runtime", () => ({ api: () => ({ GET: mocks.get, POST: mocks.post, DELETE: mocks.remove }) }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/institution",
  useParams: () => mocks.params,
  useRouter: () => ({ push: mocks.push }),
  useSearchParams: () => mocks.search,
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

const accounts: DemoAccount[] = [
  { id: "staff-h-edu-1", org_id: "org-h", display_name_th: "Educator H", role: "educator" },
  { id: "staff-h-rev", org_id: "org-h", display_name_th: "Reviewer H", role: "reviewer" },
  { id: "parent-1", org_id: "org-h", display_name_th: "Parent 1", role: "learner" },
  { id: "staff-c-admin", org_id: "org-c", display_name_th: "Admin C", role: "org_admin" },
];
const cohort = { id: "c-1", code: "ABC234", name: "Cohort one", created_at: "2026-10-28T00:00:00Z", assignment_count: 1 };
const assignment = { id: "a-1", story_id: "first-night", story_version: "1.2", title_th: "First night", join_url_path: "/join/ABC234" };
const ratio = (numerator: number, n: number) =>
  t("institution.analytics.ratio").replace("{numerator}", String(numerator)).replace("{n}", String(n));
const analytics = {
  cohort_id: "c-1", demo: true, n_started: 5, n_finished: 4,
  safety_not_met: { numerator: 1, n: 4 },
  objectives: [
    { objective_id: "OBJ-3-01", numerator: null, n: 2, suppressed: true },
    { objective_id: "OBJ-3-02", numerator: 3, n: 4, suppressed: false },
  ],
  by_story: [{ story_id: "first-night", story_version: "1.2", n_finished: 4 }],
};

function routes(extra: Record<string, unknown> = {}) {
  const table: Record<string, unknown> = {
    "/v1/demo/accounts": { items: accounts },
    "/v1/orgs/{org_id}/overview": { org: { id: "org-h", name_th: "Org H" }, demo: true, cohort_count: 2, assignment_count: 3, finished_attempts: 4 },
    "/v1/orgs/{org_id}/cohorts": { items: [cohort] },
    "/v1/cohorts/{cohort_id}/assignments": { items: [assignment] },
    "/v1/cohorts/{cohort_id}/analytics": analytics,
    "/v1/family/stories": [{ id: "first-night", title_th: "First night", description_th: "Desc", mode: "coop", chapters_th: [] }],
    "/v1/join/{code}": { cohort: { id: "c-1", name: "Cohort one" }, assignments: [{ id: "a-1", story_id: "first-night", title_th: "First night" }] },
    ...extra,
  };
  mocks.get.mockImplementation(async (path: string) => {
    const value = table[path];
    if (value instanceof Error) throw value;
    if (value === undefined) throw new Error(`unexpected ${path}`);
    return { data: value };
  });
}

function staffPage(page: React.ReactNode) {
  return render(<InstitutionShell>{page}</InstitutionShell>);
}
async function pick(id: string) {
  const account = accounts.find((a) => a.id === id);
  if (!account) throw new Error("missing test account");
  act(() => setLogin(account));
  await screen.findByRole("navigation", { name: t("institution.nav.label") });
}

beforeEach(() => {
  mocks.get.mockReset(); mocks.post.mockReset(); mocks.push.mockReset(); mocks.remove.mockReset();
  mocks.params = {}; mocks.search = new URLSearchParams(); localStorage.clear();
  routes();
});
afterEach(() => { cleanup(); vi.unstubAllEnvs(); });

describe("S2 institution shell", () => {
  it("requires staff login and no longer offers a profile picker", async () => {
    staffPage(<OverviewPage />);
    expect(await screen.findByText(t("platform.login.staffRequired"))).toBeTruthy();
    expect(screen.getAllByText(t("institution.demoLabel")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.queryByText(/Reviewer H/)).toBeNull();
    expect(screen.queryByText(/Parent 1/)).toBeNull();
    await pick("staff-h-edu-1");
    expect(getDemoAccount()).toBe("staff-h-edu-1");
    expect(await screen.findByText("Org H")).toBeTruthy();
    expect(mocks.get).toHaveBeenCalledWith("/v1/orgs/{org_id}/overview", { params: { path: { org_id: "org-h" } } });
    expect(screen.getByText(t("institution.overview.finishedHint"))).toBeTruthy();
    expect(screen.getByRole("navigation", { name: t("institution.nav.label") })).toBeTruthy();
  });

  it("ignores an obsolete picker ID and restores the logged-in institution account", async () => {
    localStorage.setItem("sim-tamy-demo-account", "parent-1");
    const first = staffPage(<OverviewPage />);
    expect(await screen.findByText(t("platform.login.staffRequired"))).toBeTruthy();
    first.unmount();
    setLogin(accounts[3]!);
    staffPage(<OverviewPage />);
    await waitFor(() => expect(mocks.get).toHaveBeenCalledWith("/v1/orgs/{org_id}/overview", { params: { path: { org_id: "org-c" } } }));
  });

  it("explains a 403 from the API", async () => {
    routes({ "/v1/orgs/{org_id}/overview": new ApiError("FORBIDDEN", 403) });
    staffPage(<OverviewPage />);
    await pick("staff-h-edu-1");
    expect(await screen.findByText(t("institution.forbidden"))).toBeTruthy();
  });
});

describe("S2 cohorts and assignments", () => {
  it("requires confirmation before removing a cohort and keeps the list after a failed request", async () => {
    mocks.remove.mockRejectedValueOnce(new ApiError("FORBIDDEN", 403)).mockResolvedValue({});
    staffPage(<CohortsPage />);
    await pick("staff-h-edu-1");
    fireEvent.click(await screen.findByRole("button", { name: `${t("institution.manage.remove")} Cohort one` }));
    fireEvent.click(screen.getByRole("button", { name: t("institution.manage.cancel") }));
    expect(mocks.remove).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: `${t("institution.manage.remove")} Cohort one` }));
    fireEvent.click(screen.getByRole("button", { name: t("institution.manage.confirmButton") }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByRole("link", { name: t("institution.cohorts.open") })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: t("institution.manage.confirmButton") }));
    await waitFor(() => expect(mocks.remove).toHaveBeenLastCalledWith("/v1/cohorts/{cohort_id}", { params: { path: { cohort_id: "c-1" } } }));
    expect(await screen.findByText(t("institution.manage.removed"))).toBeTruthy();
  });

  it("removes an assignment from its own cohort after confirmation", async () => {
    mocks.params = { id: "c-1" }; mocks.remove.mockResolvedValue({});
    staffPage(<CohortDetailPage />); await pick("staff-h-edu-1");
    fireEvent.click(await screen.findByRole("button", { name: `${t("institution.manage.remove")} First night` }));
    fireEvent.click(screen.getByRole("button", { name: t("institution.manage.confirmButton") }));
    await waitFor(() => expect(mocks.remove).toHaveBeenCalledWith("/v1/cohorts/{cohort_id}/assignments/{assignment_id}", { params: { path: { cohort_id: "c-1", assignment_id: "a-1" } } }));
  });
  it("creates a cohort and reloads the list", async () => {
    mocks.post.mockResolvedValue({ data: cohort });
    staffPage(<CohortsPage />);
    await pick("staff-h-edu-1");
    expect(await screen.findByText("Cohort one")).toBeTruthy();
    expect(screen.getByText("ABC234")).toBeTruthy();
    fireEvent.change(screen.getByLabelText(t("institution.cohorts.name")), { target: { value: " New term " } });
    fireEvent.click(screen.getByRole("button", { name: t("institution.cohorts.create") }));
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith("/v1/orgs/{org_id}/cohorts", {
      params: { path: { org_id: "org-h" } }, body: { name: "New term" },
    }));
    expect(await screen.findByText(t("institution.cohorts.created"))).toBeTruthy();
  });

  it("shows the join code and link large, assigns a story and clones the cohort", async () => {
    mocks.params = { id: "c-1" };
    mocks.post.mockImplementation(async (path: string) => ({ data: path.endsWith("/clone") ? { ...cohort, id: "c-2" } : assignment }));
    staffPage(<CohortDetailPage />);
    await pick("staff-h-edu-1");
    expect(await screen.findByLabelText(t("institution.cohorts.code"))).toHaveProperty("textContent", "ABC234");
    expect(screen.getByText(/\/join\/ABC234$/)).toBeTruthy();
    expect(await screen.findByText(/1\.2/)).toBeTruthy(); // assignment shows its story version
    await waitFor(() => expect((screen.getByLabelText(t("institution.cohort.storyLabel")) as HTMLSelectElement).options.length).toBe(2));
    fireEvent.change(screen.getByLabelText(t("institution.cohort.storyLabel")), { target: { value: "first-night" } });
    fireEvent.click(screen.getByRole("button", { name: t("institution.cohort.assign") }));
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith("/v1/cohorts/{cohort_id}/assignments", {
      params: { path: { cohort_id: "c-1" } }, body: { story_id: "first-night" },
    }));
    fireEvent.change(screen.getByLabelText(t("institution.cohort.cloneName")), { target: { value: "Next term" } });
    fireEvent.click(screen.getByRole("button", { name: t("institution.cohort.clone") }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/institution/cohorts/c-2"));
  });

  it("shows an error when assigning fails", async () => {
    mocks.params = { id: "c-1" };
    mocks.post.mockRejectedValue(new ApiError("VALIDATION_ERROR", 422));
    staffPage(<CohortDetailPage />);
    await pick("staff-h-edu-1");
    await waitFor(() => expect((screen.getByLabelText(t("institution.cohort.storyLabel")) as HTMLSelectElement).options.length).toBe(2));
    fireEvent.change(screen.getByLabelText(t("institution.cohort.storyLabel")), { target: { value: "first-night" } });
    fireEvent.click(screen.getByRole("button", { name: t("institution.cohort.assign") }));
    expect(await screen.findByText(t("institution.actionError"))).toBeTruthy();
  });
});

describe("S2 analytics, library and staff", () => {
  it("shows numerator/n and version, hides suppressed objective numbers, labels demo data", async () => {
    mocks.search = new URLSearchParams("cohort=c-1");
    staffPage(<AnalyticsPage />);
    await pick("staff-h-edu-1");
    const objectives = await screen.findByLabelText(t("institution.analytics.objectivesTitle"));
    expect(objectives.textContent).toContain(t("institution.analytics.suppressed"));
    expect(objectives.textContent).toContain(ratio(3, 4));
    const small = screen.getByText("OBJ-3-01").closest("li");
    expect(small?.textContent).not.toContain("2"); // the n=2 count and no numerator leak
    expect(screen.getByText(ratio(1, 4))).toBeTruthy(); // safety gate numerator/n
    expect(screen.getAllByText(t("institution.demoLabel")).length).toBeGreaterThan(1);
    expect(screen.getByText(new RegExp(`${t("institution.analytics.storyVersion")} 1\\.2`))).toBeTruthy();
  });

  it("lists assignable stories in the library and the org's staff read-only", async () => {
    const library = staffPage(<LibraryPage />);
    await pick("staff-h-edu-1");
    expect(await screen.findByText("Desc")).toBeTruthy();
    library.unmount();
    staffPage(<StaffPage />);
    await pick("staff-h-edu-1");
    expect(await screen.findByText("Reviewer H")).toBeTruthy();
    expect(screen.queryByText("Parent 1")).toBeNull();
    expect(screen.queryByText("Admin C")).toBeNull(); // other org
    expect(screen.queryByRole("button", { name: /./ })).toBeNull(); // read-only
  });
});

describe("S2 join landing", () => {
  it("links each assignment to the simulation room with the assignment id", async () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_ALL_CONTENT", "true");
    mocks.params = { code: "ABC234" };
    render(<JoinCodePage />);
    const link = await screen.findByRole("link", { name: t("institution.join.start") });
    expect(link.getAttribute("href")).toBe("/simulate/first-night?assignment=a-1");
    expect(screen.getByText(t("institution.join.noIntake"))).toBeTruthy();
  });

  it("shows a not-ready label instead of a link for an assignment whose story is not ready", async () => {
    mocks.params = { code: "ABC234" };
    render(<JoinCodePage />);
    expect(await screen.findByText(t("platform.notReady"))).toBeTruthy();
    expect(screen.queryByRole("link", { name: t("institution.join.start") })).toBeNull();
  });

  it.each([
    ["CLASS_NOT_FOUND", 404, "institution.join.notFound"],
    ["SESSION_EXPIRED", 410, "institution.join.expired"],
  ] as const)("shows a helpful message for %s", async (code, status, key) => {
    mocks.params = { code: "ZZZZZZ" };
    routes({ "/v1/join/{code}": new ApiError(code, status) });
    render(<JoinCodePage />);
    expect(await screen.findByText(t(key))).toBeTruthy();
    expect(screen.queryByRole("link", { name: t("institution.join.start") })).toBeNull();
  });
});
