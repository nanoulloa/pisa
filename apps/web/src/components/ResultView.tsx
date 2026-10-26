"use client";

import type { AnalysisResult, Measurement, TestResult, Verdict } from "@pisa/contracts";
import { useFormatter, useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

import { VerdictIcon } from "./VerdictIcon";

const EXPLANATIONS = [
  "slows_down_while_falling",
  "acceleration_grows",
  "accelerates_upward",
  "impossible",
  "consistent",
  "weak_violation",
  "no_measurable_acceleration",
  "depth_change",
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
] as const;

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
        <li className="card">
          <span className="card-title">{t("cards.framesTitle")}</span>
          <span className="card-value">{format.number(frames)}</span>
          <span className="card-detail">
            {t("cards.framesDetail", { fps: format.number(fps, { maximumFractionDigits: 2 }) })}
          </span>
        </li>
        <li className="card">
          <span className="card-title">{t("cards.accelerationTitle")}</span>
          <span className="card-value">{t(`cards.acceleration.${accelerationState(firstMeasured)}`)}</span>
          <span className="card-detail">{t("cards.accelerationDetail")}</span>
        </li>
        {residual !== undefined && (
          <li className="card">
            <span className="card-title">{t("cards.fitTitle")}</span>
            <span className="card-value">
              {t("cards.fitValue", { value: format.number(residual, { maximumFractionDigits: 2 }) })}
            </span>
            <span className="card-detail">{t("cards.fitDetail")}</span>
          </li>
        )}
        <li className="card">
          <span className="card-title">{t("cards.phasesTitle")}</span>
          <span className="card-value">{format.number(shape.length)}</span>
          <span className="card-detail">{t("cards.phasesDetail")}</span>
        </li>
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
    const violation = tests.find((test) => test.outcome === "violation")?.reason_code;
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
