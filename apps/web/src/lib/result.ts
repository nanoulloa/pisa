import type { EvidenceSeries, TestId, TestResult, Verdict } from "@pisa/contracts";

/** Keys under `Result.explanations`: the sentence under the verdict when no model wrote one. */
export const EXPLANATIONS = [
  "slows_down_while_falling",
  "acceleration_grows",
  "accelerates_upward",
  "pair_falls_apart",
  "bounce_gains_energy",
  "gravity_changes",
  "gravity_too_weak",
  "gravity_too_strong",
  "impossible",
  "consistent",
  "weak_violation",
  "no_measurable_acceleration",
  "depth_change",
  "camera_motion",
  "too_few_samples",
  "no_free_flight",
  "too_unclear",
  "no_measurable_events",
] as const;

export type ExplanationKey = (typeof EXPLANATIONS)[number];

export function explanationKey(verdict: Verdict, tests: TestResult[]): ExplanationKey {
  if (verdict.label === "consistent_with_real_physics") return "consistent";
  // The tests' own reasons are more specific than the verdict's, so they come first.
  const reasons = [...tests.map((test) => test.reason_code), verdict.reason_code];
  if (verdict.label === "physically_impossible") {
    // Explain the strongest violation among the tests that decided the verdict.
    const decisive: readonly TestId[] = verdict.decisive_tests;
    const violation = tests
      .filter((test) => test.outcome === "violation" && decisive.includes(test.test))
      .sort((a, b) => b.confidence - a.confidence)[0]?.reason_code;
    return isExplanation(violation) ? violation : "impossible";
  }
  if (verdict.reason_code === "weak_violation") {
    // Gravity of the wrong strength is also what slow or fast playback looks like: say so.
    const gravity = tests.find((test) => test.test === "implied_g" && test.outcome === "violation");
    return isExplanation(gravity?.reason_code) ? gravity.reason_code : "weak_violation";
  }
  return reasons.find(isExplanation) ?? "no_measurable_events";
}

function isExplanation(code: string | null | undefined): code is ExplanationKey {
  return code !== null && code !== undefined && (EXPLANATIONS as readonly string[]).includes(code);
}

/** A measurement from the given test, preferring a violation over a pass. */
export function measuredValue(tests: TestResult[], id: TestId, name: string): number | undefined {
  const measured = tests.filter(
    (test) => test.test === id && (test.outcome === "pass" || test.outcome === "violation"),
  );
  const shown = measured.find((test) => test.outcome === "violation") ?? measured[0];
  return shown ? measurement(shown, name) : undefined;
}

export function measurement(test: TestResult, name: string): number | undefined {
  return test.measurements.find((m) => m.name === name)?.value;
}

/** The one number that says the most, in the order the result cards use. */
export type Headline =
  | { kind: "impliedG"; value: number }
  | { kind: "bounce"; value: number }
  | { kind: "pair"; value: number }
  | { kind: "gravity"; value: number };

export function headline(tests: TestResult[]): Headline | null {
  const impliedG = measuredValue(tests, "implied_g", "implied_g");
  if (impliedG !== undefined) return { kind: "impliedG", value: impliedG };
  const restitution = measuredValue(tests, "bounce_energy", "restitution");
  if (restitution !== undefined) return { kind: "bounce", value: restitution };
  const pair = measuredValue(tests, "galileo_pair", "acceleration_ratio");
  if (pair !== undefined) return { kind: "pair", value: Math.max(pair, 1 / pair) };
  const gravity = measuredValue(tests, "time_base_consistency", "acceleration_ratio");
  if (gravity !== undefined) return { kind: "gravity", value: gravity };
  return null;
}

export type Point = readonly [number, number];

/**
 * A measured flight and its ghost as chart coordinates: time to the right, height up,
 * both series on one scale inside a `width` x `height` box with `pad` around.
 */
export function chartPoints(
  series: EvidenceSeries,
  width: number,
  height: number,
  pad: number,
): { measured: Point[]; ghost: Point[] } {
  const times = series.t_s;
  const t0 = times[0] ?? 0;
  const span = (times.at(-1) ?? t0) - t0 || 1;
  // Image y points down; height is its negative.
  const heights = [...series.y_px, ...series.ghost_y_px].map((y) => -y);
  const top = Math.max(...heights);
  const range = top - Math.min(...heights) || 1;
  const point = (t: number, y: number): Point => [
    pad + ((t - t0) / span) * (width - 2 * pad),
    pad + ((top + y) / range) * (height - 2 * pad),
  ];
  return {
    measured: times.map((t, i) => point(t, series.y_px[i] ?? 0)),
    ghost: times.map((t, i) => point(t, series.ghost_y_px[i] ?? 0)),
  };
}
