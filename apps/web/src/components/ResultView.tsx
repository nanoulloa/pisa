"use client";

import type { AnalysisResult, Measurement, Plan, TestResult } from "@pisa/contracts";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { explanationKey, measuredValue, measurement } from "@/lib/result";

import { EvidenceVideo } from "./EvidenceVideo";
import { ShareButtons } from "./ShareButtons";
import { TrajectoryChart } from "./TrajectoryChart";
import { VerdictIcon } from "./VerdictIcon";

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
const EARTH_G = 9.81;

type Card = { key: string; title: string; value: string; detail: string };

export function ResultView({ result }: { result: AnalysisResult }) {
  const t = useTranslations("Result");
  const verdictLabels = useTranslations("Verdict");
  const format = useFormatter();
  const locale = useLocale();
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

  // Gravity in m/s² says the most in one number, then the laws a clip was checked against,
  // then the fall itself, then the context.
  const cards: Card[] = [];
  const impliedG = measuredValue(result.tests, "implied_g", "implied_g");
  if (impliedG !== undefined) {
    cards.push({
      key: "implied-g",
      title: t("cards.impliedGTitle"),
      value: t("cards.impliedGValue", { value: format.number(impliedG, { maximumFractionDigits: 1 }) }),
      detail: t("cards.impliedGDetail", { earth: format.number(EARTH_G) }),
    });
  }
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
        <p>
          {result.explanation?.locale === locale
            ? result.explanation.text
            : t(`explanations.${explanationKey(verdict, result.tests)}`)}
        </p>
      </div>
      {result.evidence?.video && result.evidence.series[0] && (
        <EvidenceVideo
          id={result.job.id}
          video={result.evidence.video}
          model={result.evidence.series[0].model}
        />
      )}
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
        {result.evidence?.series[0] && <TrajectoryChart series={result.evidence.series[0]} />}
        {result.plan && <PlanDetails plan={result.plan} />}
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
        {result.explanation?.locale === locale && <p className="hint">{t("modelExplanation")}</p>}
        <p className="hint">{t("policy", { version: verdict.policy_version })}</p>
      </details>

      <p className="hint">
        {t("limits")}{" "}
        <Link className="text-link" href="/how-we-know">
          {t("howWeKnow")}
        </Link>
      </p>
      <ShareButtons id={result.job.id} verdict={verdictLabels(verdict.label)} />
      <Link className="button-primary" href="/check">
        {t("checkAnother")}
      </Link>
    </article>
  );
}

/** What the planner saw: the windows that were measured, the camera, the size reference. */
function PlanDetails({ plan }: { plan: Plan }) {
  const t = useTranslations("Result.plan");
  const format = useFormatter();
  const seconds = (value: number) => format.number(value, { maximumFractionDigits: 2 });
  if (!plan.measurable) return null;
  return (
    <section className="technical-test">
      <h2>{t("title")}</h2>
      <ul className="plan-list">
        {plan.events.map((event, index) => (
          <li key={index}>
            {t("event", {
              type: t(`eventTypes.${event.type}`),
              start: seconds(event.start_s),
              end: seconds(event.end_s),
              objects: event.object_phrases.join(", "),
            })}
          </li>
        ))}
        <li>{t("camera", { motion: t(`cameraMotion.${plan.camera.motion}`) })}</li>
        {plan.camera.slow_motion_suspected && <li>{t("slowMotion")}</li>}
        {plan.references.map((reference, index) => (
          <li key={`ref-${index}`}>
            {t("reference", {
              phrase: reference.phrase,
              min: format.number(reference.size_min_m, { maximumFractionDigits: 3 }),
              max: format.number(reference.size_max_m, { maximumFractionDigits: 3 }),
            })}
          </li>
        ))}
      </ul>
    </section>
  );
}

function accelerationState(test: TestResult | undefined): "steady" | "changing" | "unmeasured" {
  if (test === undefined || test.outcome === "insufficient_data") return "unmeasured";
  return test.outcome === "pass" ? "steady" : "changing";
}

function measurementName(
  m: Measurement,
  translate: (key: (typeof MEASUREMENT_NAMES)[number]) => string,
): string {
  const known = (MEASUREMENT_NAMES as readonly string[]).includes(m.name);
  return known ? translate(m.name as (typeof MEASUREMENT_NAMES)[number]) : m.name;
}
