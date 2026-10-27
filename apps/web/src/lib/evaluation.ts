import type { EvalReport, TestId } from "@pisa/contracts";

import published from "../../../../eval/reports/published.json";

/** The eval shown on the "How we know" page. Which report it is, is a deliberate choice:
 * `uv run python -m pisa_engine.evaluation publish --name <run>` writes this file. */
export const publishedReport = published as EvalReport;

/** The five laws in the order the page explains them; T4 is the one that needs a scale. */
export const LAWS = [
  "free_fall_shape",
  "galileo_pair",
  "bounce_energy",
  "implied_g",
  "time_base_consistency",
] as const satisfies readonly TestId[];

export const NEEDS_SCALE: ReadonlySet<TestId> = new Set(["implied_g"]);

export function lawNumber(test: TestId): number {
  return LAWS.indexOf(test) + 1;
}
