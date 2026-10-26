import type { EvidenceSeries, TestResult, Verdict } from "@pisa/contracts";
import { describe, expect, it } from "vitest";

import { chartPoints, explanationKey, headline } from "./result";

const test = (
  id: TestResult["test"],
  outcome: TestResult["outcome"],
  measurements: Record<string, number>,
  reason: string | null = null,
  confidence = 1,
): TestResult => ({
  test: id,
  outcome,
  confidence,
  reason_code: reason,
  measurements: Object.entries(measurements).map(([name, value]) => ({
    name,
    value,
    unit: "1",
    ci_low: null,
    ci_high: null,
  })),
});

const verdict = (
  label: Verdict["label"],
  decisive: Verdict["decisive_tests"],
  reason: string | null = null,
): Verdict => ({
  label,
  policy_version: "0.1.0",
  decisive_tests: decisive,
  reason_code: reason,
});

describe("explanationKey", () => {
  it("explains the strongest decisive violation", () => {
    const tests = [
      test("free_fall_shape", "violation", {}, "acceleration_grows", 0.7),
      test("galileo_pair", "violation", {}, "pair_falls_apart", 1),
    ];
    expect(explanationKey(verdict("physically_impossible", ["galileo_pair"]), tests)).toBe(
      "pair_falls_apart",
    );
  });

  it("says that wrong gravity can be slow motion", () => {
    const tests = [
      test("free_fall_shape", "pass", {}),
      test("implied_g", "violation", {}, "gravity_too_weak"),
    ];
    expect(explanationKey(verdict("inconclusive", [], "weak_violation"), tests)).toBe("gravity_too_weak");
  });

  it("uses the planner's reason when nothing was measurable", () => {
    expect(explanationKey(verdict("inconclusive", [], "too_unclear"), [])).toBe("too_unclear");
  });
});

describe("headline", () => {
  it("prefers gravity in m/s², then the laws", () => {
    const tests = [
      test("galileo_pair", "pass", { acceleration_ratio: 0.61 }),
      test("implied_g", "violation", { implied_g: 1.62 }),
    ];
    expect(headline(tests)).toEqual({ kind: "impliedG", value: 1.62 });
    expect(headline(tests.slice(0, 1))?.value).toBeCloseTo(1 / 0.61);
    expect(headline([test("free_fall_shape", "pass", {})])).toBeNull();
  });
});

describe("chartPoints", () => {
  it("puts time to the right and height up, on one scale for both series", () => {
    const series: EvidenceSeries = {
      phrase: "ball",
      object_id: 0,
      model: "earth_gravity",
      t_s: [0, 0.5, 1],
      y_px: [100, 150, 200],
      ghost_y_px: [100, 200, 300],
      px_per_m: 400,
    };
    const { measured, ghost } = chartPoints(series, 220, 120, 10);
    expect(measured[0]).toEqual([10, 10]); // Start: left, at the top (highest point).
    expect(ghost[2]).toEqual([210, 110]); // The ghost ends lowest: bottom right.
    expect(measured[2]?.[1]).toBe(60); // Halfway down the shared scale.
  });
});
