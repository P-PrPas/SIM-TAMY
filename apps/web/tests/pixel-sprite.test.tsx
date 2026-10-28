// @vitest-environment jsdom
import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { PALETTE, runs, Sprite } from "@/components/pixel/sprite";

afterEach(cleanup);

it("merges same-colour runs and skips transparent pixels", () => {
  expect(runs(["kk.y", "...."])).toEqual([
    { x: 0, y: 0, w: 2, fill: PALETTE.k },
    { x: 3, y: 0, w: 1, fill: PALETTE.y },
  ]);
});

it("lays frames side by side and only animates multi-frame sprites", () => {
  const { container, rerender } = render(<Sprite frames={[["ky"], ["yk"]]} scale={3} />);
  const svg = container.querySelector("svg")!;
  expect(svg.getAttribute("viewBox")).toBe("0 0 4 1");
  expect(svg.getAttribute("width")).toBe("12");
  expect(svg.classList.contains("is-animated")).toBe(true);
  expect(container.querySelector(".pixel-sprite")!.getAttribute("aria-hidden")).toBe("true");
  rerender(<Sprite frames={[["ky"]]} />);
  expect(container.querySelector("svg")!.classList.contains("is-animated")).toBe(false);
});
