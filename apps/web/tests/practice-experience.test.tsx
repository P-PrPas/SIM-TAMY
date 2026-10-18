// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PracticeChoice } from "@/components/practice-choice";
import { PracticeStage } from "@/components/practice-stage";
import { t } from "@/lib/i18n";

afterEach(cleanup);

it("keeps selection editable and commits only after explicit confirmation", () => {
  const commit = vi.fn();
  render(<PracticeChoice choices={[{ id: "a", text_th: "First response" }, { id: "b", text_th: "Second response" }]} disabled={false} onCommit={commit} />);
  expect(screen.getByRole("button").hasAttribute("disabled")).toBe(true);
  fireEvent.click(screen.getByRole("radio", { name: "First response" }));
  fireEvent.click(screen.getByRole("radio", { name: "Second response" }));
  expect(commit).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: t("experience.commit") }));
  expect(commit).toHaveBeenCalledExactlyOnceWith("b");
});

it("prevents selection and duplicate submission while a decision is pending", () => {
  const commit = vi.fn();
  render(<PracticeChoice choices={[{ id: "a", text_th: "First response" }]} disabled onCommit={commit} />);
  fireEvent.submit(screen.getByRole("button").closest("form")!);
  expect(commit).not.toHaveBeenCalled();
  expect(screen.getByRole("radio").closest("fieldset")?.disabled).toBe(true);
});

it("lets a learner collapse the decorative scene while retaining context", () => {
  render(<PracticeStage chapter="A public chapter" speaker="A public speaker" family />);
  expect(screen.getByText("A public chapter")).not.toBeNull();
  const summary = screen.getByText(t("experience.scene")).closest("summary")!;
  const details = summary.parentElement as HTMLDetailsElement;
  expect(details.open).toBe(true);
  fireEvent.click(summary);
  expect(details.open).toBe(false);
});
