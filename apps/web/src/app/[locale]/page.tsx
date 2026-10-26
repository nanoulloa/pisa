import type { VerdictLabel } from "@pisa/contracts";
import { getTranslations } from "next-intl/server";

import { GhostDemo } from "@/components/GhostDemo";
import { VerdictIcon } from "@/components/VerdictIcon";
import { Link } from "@/i18n/navigation";
import { resolveLocale } from "@/i18n/locale";

const VERDICTS: readonly VerdictLabel[] = [
  "physically_impossible",
  "consistent_with_real_physics",
  "inconclusive",
];

const STEPS = ["watching", "tracking", "measuring", "explaining"] as const;

const SOURCES = {
  gravity: "https://arxiv.org/abs/2512.02016",
  morpheus: "https://arxiv.org/abs/2504.02918",
  code: "https://github.com/nanoulloa/pisa",
};

export default async function HomePage({ params }: PageProps<"/[locale]">) {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "Home" });
  const verdict = await getTranslations({ locale, namespace: "Verdict" });
  const steps = await getTranslations({ locale, namespace: "Progress.steps" });
  const brand = await getTranslations({ locale, namespace: "Metadata" });

  return (
    <main className="home">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy">
          <p className="eyebrow">{t("eyebrow")}</p>
          <h1 id="hero-title" className="hero-title">
            <span>{t("taglineLead")}</span> <span className="hero-turn">{t("taglineTurn")}</span>
          </h1>
          <p className="lede">{t("lede")}</p>
          <div className="hero-actions">
            <Link className="button-primary" href="/check">
              {t("cta")}
            </Link>
            <a className="text-link" href="#how">
              {t("howLink")}
            </a>
          </div>
        </div>
        <GhostDemo
          filmed={{
            label: t("demo.filmed"),
            verdictLabel: verdict("consistent_with_real_physics"),
            note: t("demo.filmedNote"),
          }}
          generated={{
            label: t("demo.generated"),
            verdictLabel: verdict("physically_impossible"),
            note: t("demo.generatedNote"),
          }}
          legend={t("demo.legend")}
          caption={t("demo.caption")}
        />
      </section>

      <section id="how" className="band" aria-labelledby="how-title">
        <h2 id="how-title">{t("steps.title")}</h2>
        <ol className="steps-row">
          {STEPS.map((step, index) => (
            <li key={step}>
              <span className="step-number">{String(index + 1).padStart(2, "0")}</span>
              <h3>{steps(step)}</h3>
              <p>{t(`steps.${step}`)}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="band" aria-labelledby="answers-title">
        <h2 id="answers-title">{t("verdictsTitle")}</h2>
        <ul className="answer-list">
          {VERDICTS.map((label) => (
            <li key={label} className={`answer verdict-${label}`}>
              <VerdictIcon label={label} />
              <h3>{verdict(label)}</h3>
              <p>{t(`answers.${label}`)}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="band" aria-labelledby="why-title">
        <h2 id="why-title">{t("why.title")}</h2>
        <div className="stats">
          <figure className="stat">
            <span className="stat-value">{t("why.gravityValue")}</span>
            <figcaption>
              {t("why.gravityLabel")}{" "}
              <a href={SOURCES.gravity} rel="noreferrer">
                {t("why.gravitySource")}
              </a>
            </figcaption>
          </figure>
          <figure className="stat">
            <span className="stat-value">{t("why.opinionValue")}</span>
            <figcaption>
              {t("why.opinionLabel")}{" "}
              <a href={SOURCES.morpheus} rel="noreferrer">
                {t("why.opinionSource")}
              </a>
            </figcaption>
          </figure>
        </div>
      </section>

      <section className="band scope" aria-labelledby="scope-title">
        <h2 id="scope-title">{t("scope.title")}</h2>
        <dl className="scope-grid">
          <div>
            <dt>{t("scope.checksTitle")}</dt>
            <dd>{t("scope.checks")}</dd>
          </div>
          <div>
            <dt>{t("scope.skipsTitle")}</dt>
            <dd>{t("scope.skips")}</dd>
          </div>
        </dl>
      </section>

      <footer className="site-footer">
        <span className="footer-lockup" aria-hidden="true">
          <span className="brand-mark" />
          <span className="wordmark">{brand("title")}</span>
        </span>
        <p>{t("footer.built")}</p>
        <a href={SOURCES.code} rel="noreferrer">
          {t("footer.code")}
        </a>
      </footer>
    </main>
  );
}
