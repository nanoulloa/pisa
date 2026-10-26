"use client";

import type { AnalysisResult, Job, Stage } from "@pisa/contracts";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Link } from "@/i18n/navigation";
import { EngineError, getJob, getResult } from "@/lib/engine";

import { ErrorMessage } from "./ErrorMessage";
import { ResultView } from "./ResultView";

const POLL_MS = 700;

/** The four steps people see, each covering the engine stages that run under it. */
const STEPS = [
  { key: "watching", stages: ["ingest", "plan"] },
  { key: "tracking", stages: ["track"] },
  { key: "measuring", stages: ["stabilize", "measure", "test", "verdict"] },
  { key: "explaining", stages: ["explain", "render"] },
] as const satisfies readonly { key: string; stages: readonly Stage[] }[];

type StepState = "done" | "current" | "pending";

export function JobView({ id }: { id: string }) {
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const current = await getJob(id);
        if (cancelled) return;
        setJob(current);
        if (current.status === "done") {
          const analysis = await getResult(id);
          if (!cancelled) setResult(analysis);
        } else if (current.status === "failed") {
          setError(current.error?.code ?? "internal_error");
        } else {
          timer = setTimeout(poll, POLL_MS);
        }
      } catch (caught) {
        if (!cancelled) setError(caught instanceof EngineError ? caught.code : "internal_error");
      }
    }

    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  if (result !== null) return <ResultView result={result} />;
  return <Progress stage={job?.stage ?? null} error={error} />;
}

function Progress({ stage, error }: { stage: Stage | null; error: string | null }) {
  const t = useTranslations("Progress");
  const active = activeStep(stage);
  const current = STEPS[active];

  return (
    <section className="page" aria-labelledby="progress-title">
      <h1 id="progress-title">{t("title")}</h1>
      <ol className="steps">
        {STEPS.map((step, index) => {
          const state: StepState = index < active ? "done" : index === active ? "current" : "pending";
          return (
            <li
              key={step.key}
              className={`step step-${state}`}
              aria-current={state === "current" ? "step" : undefined}
            >
              <span className="step-marker" aria-hidden="true" />
              <span>{t(`steps.${step.key}`)}</span>
              <span className="visually-hidden">{t("state", { state })}</span>
            </li>
          );
        })}
      </ol>
      <p className="visually-hidden" aria-live="polite">
        {error === null && current !== undefined ? t(`steps.${current.key}`) : ""}
      </p>
      {error !== null && (
        <div className="stack">
          <ErrorMessage code={error} />
          <Link className="button-secondary" href="/check">
            {t("tryAgain")}
          </Link>
        </div>
      )}
    </section>
  );
}

function activeStep(stage: Stage | null): number {
  if (stage === null) return 0;
  const index = STEPS.findIndex((step) => (step.stages as readonly Stage[]).includes(stage));
  return index === -1 ? 0 : index;
}
