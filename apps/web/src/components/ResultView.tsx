"use client";

import type { AnalysisResult, Measurement, TestId, TestResult, Verdict } from "@pisa/contracts";
import { useFormatter, useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

import { VerdictIcon } from "./VerdictIcon";

const EXPLANATIONS = [
  "slows_down_while_falling",
  "acceleration_grows",
  "accelerates_upward",
  "pair_falls_apart",
  "bounce_gains_energy",
  "gravity_changes",
  "impossible",
  "consistent",
  "weak_violation",
  "no_measurable_acceleration",
  "depth_change",
  "camera_motion",
  "too_few_samples",
  "no_measurable_events",
] as const;

type Explanation = (typeof EXPLANATIONS)[number];

const MEASUREMENT_NAMES = [
  "acceleration_px_s2",
  "acceleration_start_px_s2",
  "acceleration_end_px_s2",
  "bic_gain_constant_acceleration",
  "bic_gain_changing_acceleration",
  "residual_rms_px",
  "area_ratio",
  "samples",
  "duration_s",
  "acceleration_ratio",
  "acceleration_first_px_s2",
  "acceleration_second_px_s2",
  "release_gap_s",
  "z_score",
  "restitution",
  "restitution_se",
  "speed_in_px_s",
  "speed_out_px_s",
  "acceleration_max_px_s2",
  "acceleration_min_px_s2",
  "flights",
  "implied_g",
  "earth_g_ratio",
  "unreliable_share",
] as const;

const MAX_CARDS = 4;

type Card = { key: string; title: string; value: string; detail: string };

export function ResultView({ result }: { result: AnalysisResult }) {
  const t = useTranslations("Result");
  const verdictLabels = useTranslations("Verdict");
  const format = useFormatter();
  const verdict = result.verdict;
  if (verdict === null) return null;

  const shape = result.tests.filter((test) => test.test === "free_fall_shape");
  const firstMeasured = shape.find((test) => test.outcome !== "insufficient_data") ?? shape[0];
  const frames = result.tracks?.objects[0]?.samples.length ?? 0;
  const timebase = result.ingest?.timebase;
  const fps = timebase ? timebase.fps_num / timebase.fps_den : 0;
  const residual = firstMeasured ? measurement(firstMeasured, "residual_rms_px") : undefined;
  const ratio = (value: number) =>
    t("cards.ratioValue", { value: format.number(value, { maximumFractionDigits: 2 }) });

  // The laws a clip was checked against come first, then the fall itself, then the context.
  const cards: Card[] = [];
  const restitution = measuredValue(result.tests, "bounce_energy", "restitution");
  if (restitution !== undefined) {
    cards.push({
      key: "bounce",
      title: t("cards.bounceTitle"),
      value: format.number(restitution, { style: "percent", maximumFractionDigits: 0 }),
      detail: t("cards.bounceDetail"),
    });
  }
  const pair = measuredValue(result.tests, "galileo_pair", "acceleration_ratio");
  if (pair !== undefined) {
    cards.push({
      key: "pair",
      title: t("cards.pairTitle"),
      value: ratio(Math.max(pair, 1 / pair)),
      detail: t("cards.pairDetail"),
    });
  }
  const gravity = measuredValue(result.tests, "time_base_consistency", "acceleration_ratio");
  if (gravity !== undefined) {
    cards.push({
      key: "gravity",
      title: t("cards.gravityTitle"),
      value: ratio(gravity),
      detail: t("cards.gravityDetail"),
    });
  }
  cards.push({
    key: "acceleration",
    title: t("cards.accelerationTitle"),
    value: t(`cards.acceleration.${accelerationState(firstMeasured)}`),
    detail: t("cards.accelerationDetail"),
  });
  const stabilization = result.stabilization;
  if (stabilization?.applied) {
    cards.push({
      key: "camera",
      title: t("cards.cameraTitle"),
      value: t("cards.cameraValue"),
      detail: t("cards.cameraDetail", {
        value: format.number(stabilization.max_motion_px, { maximumFractionDigits: 0 }),
      }),
    });
  }
  if (residual !== undefined) {
    cards.push({
      key: "fit",
      title: t("cards.fitTitle"),
      value: t("cards.fitValue", { value: format.number(residual, { maximumFractionDigits: 2 }) }),
      detail: t("cards.fitDetail"),
    });
  }
  cards.push(
    {
      key: "phases",
      title: t("cards.phasesTitle"),
      value: format.number(shape.length),
      detail: t("cards.phasesDetail"),
    },
    {
      key: "frames",
      title: t("cards.framesTitle"),
      value: format.number(frames),
      detail: t("cards.framesDetail", { fps: format.number(fps, { maximumFractionDigits: 2 }) }),
    },
  );

  return (
    <article className="page result" aria-labelledby="verdict-title">
      <span className="eyebrow">{t("eyebrow")}</span>
      <div className={`verdict verdict-${verdict.label}`}>
        <VerdictIcon label={verdict.label} />
        <h1 id="verdict-title">{verdictLabels(verdict.label)}</h1>
        <p>{t(`explanations.${explanation(verdict, result.tests)}`)}</p>
      </div>
      {verdict.label === "consistent_with_real_physics" && (
        <p className="note">{t("consistentNote")}</p>
      )}

      <ul className="cards">
        {cards.slice(0, MAX_CARDS).map((card) => (
          <li key={card.key} className="card">
            <span className="card-title">{card.title}</span>
            <span className="card-value">{card.value}</span>
            <span className="card-detail">{card.detail}</span>
          </li>
        ))}
      </ul>

      <details className="technical">
        <summary>{t("detailsSummary")}</summary>
        {result.tests.map((test, index) => (
          <section key={index} className="technical-test">
            <h2>
              {t(`tests.${test.test}`)} · {t(`outcomes.${test.outcome}`)} ·{" "}
              {t("confidence", { value: format.number(test.confidence, { style: "percent" }) })}
            </h2>
            <div className="table-wrap">
              <table>
                <tbody>
                  {test.measurements.map((m) => (
                    <tr key={m.name}>
                      <th scope="row">{measurementName(m, (key) => t(`measurements.${key}`))}</th>
                      <td className="num">
                        {format.number(m.value, { maximumFractionDigits: 3 })} {m.unit === "1" ? "" : m.unit}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ))}
        {stabilization && (
          <p className="hint">
            {t("stabilization", {
              max: format.number(stabilization.max_motion_px, { maximumFractionDigits: 1 }),
              unreliable: format.number(stabilization.unreliable_frames),
              frames: format.number(stabilization.frames),
            })}
          </p>
        )}
        <p className="hint">{t("policy", { version: verdict.policy_version })}</p>
      </details>

      <p className="hint">{t("limits")}</p>
      <Link className="button-primary" href="/check">
        {t("checkAnother")}
      </Link>
    </article>
  );
}

function explanation(verdict: Verdict, tests: TestResult[]): Explanation {
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
  if (verdict.reason_code === "weak_violation") return "weak_violation";
  return reasons.find(isExplanation) ?? "no_measurable_events";
}

function isExplanation(code: string | null | undefined): code is Explanation {
  return code !== null && code !== undefined && (EXPLANATIONS as readonly string[]).includes(code);
}

function accelerationState(test: TestResult | undefined): "steady" | "changing" | "unmeasured" {
  if (test === undefined || test.outcome === "insufficient_data") return "unmeasured";
  return test.outcome === "pass" ? "steady" : "changing";
}

/** A measurement from the given test, preferring a violation over a pass. */
function measuredValue(tests: TestResult[], id: TestId, name: string): number | undefined {
  const measured = tests.filter(
    (test) => test.test === id && (test.outcome === "pass" || test.outcome === "violation"),
  );
  const shown = measured.find((test) => test.outcome === "violation") ?? measured[0];
  return shown ? measurement(shown, name) : undefined;
}

function measurement(test: TestResult, name: string): number | undefined {
  return test.measurements.find((m) => m.name === name)?.value;
}

function measurementName(
  m: Measurement,
  translate: (key: (typeof MEASUREMENT_NAMES)[number]) => string,
): string {
  const known = (MEASUREMENT_NAMES as readonly string[]).includes(m.name);
  return known ? translate(m.name as (typeof MEASUREMENT_NAMES)[number]) : m.name;
}
