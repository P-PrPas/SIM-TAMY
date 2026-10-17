// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { BranchReplay } from "../components/branch-replay";
import { t } from "../lib/i18n";

afterEach(cleanup);

it.each([ ["Referral", "referral"], ["UnsafeProceed", "unsafe"] ])("shows the actual %s outcome and walks the supplied script", (terminal_state, key) => {
  const view = render(<BranchReplay replay={{ terminal_state, timeline_th: ["First supplied scene", "Second supplied scene"], missed_opportunities: [], disclaimer_th: "fixture" }} timeline={[{ event_id: 4, turn_idx: 2, type: "DECISION_COMMITTED", summary_th: "Committed choice" }]} />);
  expect(screen.getByText(t(`branchReplay.${key}`))).toBeTruthy();
  expect(screen.getByText("Committed choice")).toBeTruthy();
  expect(view.container.querySelector('[aria-current="step"]')?.textContent).toBe("First supplied scene");
  fireEvent.click(screen.getByRole("button", { name: t("branchReplay.next") }));
  expect(view.container.querySelector('[aria-current="step"]')?.textContent).toBe("Second supplied scene");
  expect(screen.getByRole("button", { name: t("branchReplay.next") }).hasAttribute("disabled")).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: t("branchReplay.previous") }));
  expect(view.container.querySelector('[aria-current="step"]')?.textContent).toBe("First supplied scene");
});
