import type { VerdictLabel } from "@pisa/contracts";
import Image from "next/image";
import { getFormatter, getTranslations } from "next-intl/server";

import { GravityLab } from "@/components/GravityLab";
import { GravityScale } from "@/components/GravityScale";
import { type Motion, MotionPictogram, type Skip, SkipPictogram, StepArt } from "@/components/HomeArt";
import { LoopVideo } from "@/components/LoopVideo";
import { VerdictIcon } from "@/components/VerdictIcon";
import { Link } from "@/i18n/navigation";
import { resolveLocale } from "@/i18n/locale";

const VERDICTS: readonly VerdictLabel[] = [
  "physically_impossible",
  "consistent_with_real_physics",
  "inconclusive",
];

const STEPS = [
  { key: "watching", model: "Muse Spark" },
  { key: "tracking", model: "SAM 3.1" },
  { key: "measuring", model: null },
  { key: "explaining", model: "Muse Spark" },
] as const;

const CALLOUTS = ["ghost", "verdict", "numbers", "language"] as const;
const MOTIONS: readonly Motion[] = ["fall", "throw", "bounce", "pair"];
const SKIPS: readonly Skip[] = ["faces", "lips", "voices"];

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
  const explanations = await getTranslations({ locale, namespace: "Result.explanations" });
  const whatsapp = await getTranslations({ locale, namespace: "WhatsApp" });
  const format = await getFormatter({ locale });
  const gravity = (value: number) => format.number(value, { maximumFractionDigits: 2 });

  return (
    <main className="home">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-inner">
          <h1 id="hero-title" className="hero-title">
            <span>{t("taglineLead")}</span> <span className="hero-turn">{t("taglineTurn")}</span>
          </h1>
          <div className="hero-copy">
            <p className="hero-lede">{t("lede")}</p>
            <div className="hero-actions">
              <Link className="button-accent" href="/check">
                {t("cta")}
              </Link>
              <a className="hero-link" href="#how">
                {t("howLink")}
              </a>
            </div>
          </div>
          <GravityLab />
          <ul className="hero-key">
            <li>
              <span className="key-swatch key-ghost" aria-hidden="true" />
              {t("lab.keyGhost")}
            </li>
            <li>
              <span className="key-swatch key-ball" aria-hidden="true" />
              {t("lab.keyBall")}
            </li>
            <li>
              <span className="key-swatch key-instant" aria-hidden="true" />
              {t("lab.keyInstant")}
            </li>
          </ul>

        </div>
      </section>

      <section className="section proof" aria-labelledby="proof-title">
        <header className="section-head">
          <h2 id="proof-title">{t("proof.title")}</h2>
          <p>{t("proof.lede")}</p>
        </header>
        <figure className="proof-figure">
          <div className="phone">
            <div className="phone-bar">
              <span className="phone-avatar" aria-hidden="true">
                <span className="brand-mark" />
              </span>
              <span className="phone-name">{brand("title")}</span>
            </div>
            <div className="chat">
              <div className="bubble bubble-in">
                <span className="bubble-forwarded">{t("proof.forwarded")}</span>
                <span className="bubble-clip" aria-hidden="true">
                  <Image src="/demo/forwarded.jpg" alt="" width={240} height={240} />
                </span>
                <span>{t("proof.question")}</span>
              </div>
              <div className="bubble bubble-out">
                <span className="bubble-media">
                  <LoopVideo className="bubble-video" src="/demo/reply.mp4" poster="/demo/reply.jpg" />
                  <span className="callout-pin" data-pin="1" aria-hidden="true" />
                </span>
                <span className="bubble-verdict verdict-physically_impossible">
                  <VerdictIcon label="physically_impossible" />
                  {verdict("physically_impossible")}
                  <span className="callout-pin" data-pin="2" aria-hidden="true" />
                </span>
                <span>{explanations("pair_falls_apart")}</span>
                <span>{whatsapp("legend.partner")}</span>
                <span className="bubble-link">
                  {whatsapp("details", { link: "pisa-theta.vercel.app" })}
                  <span className="callout-pin" data-pin="3" aria-hidden="true" />
                </span>
              </div>
            </div>
          </div>
          <ol className="callouts">
            {CALLOUTS.map((callout) => (
              <li key={callout}>
                <h3>{t(`proof.callouts.${callout}`)}</h3>
                <p>{t(`proof.callouts.${callout}Text`)}</p>
              </li>
            ))}
          </ol>
          <figcaption className="hint">{t("proof.caption")}</figcaption>
        </figure>
      </section>

      <section id="how" className="section" aria-labelledby="how-title">
        <header className="section-head">
          <h2 id="how-title">{t("steps.title")}</h2>
        </header>
        <ol className="pipeline">
          {STEPS.map((step) => (
            <li key={step.key}>
              <StepArt step={step.key} />
              <span className="model-tag">{step.model ?? t("steps.engine")}</span>
              <h3>{steps(step.key)}</h3>
              <p>{t(`steps.${step.key}`)}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="section why" aria-labelledby="why-title">
        <header className="section-head">
          <h2 id="why-title">{t("why.title")}</h2>
        </header>
        <GravityScale
          generated={t("why.scale.generated")}
          moon={t("why.scale.moon")}
          mars={t("why.scale.mars")}
          earth={t("why.scale.earth")}
          summary={t("why.scale.summary")}
          format={gravity}
        />
        <div className="why-grid">
          <div className="why-fact">
            <p className="why-big">{t("why.scale.moonNote")}</p>
            <p>
              {t("why.gravityLabel")}{" "}
              <a href={SOURCES.gravity} rel="noreferrer">
                {t("why.gravitySource")}
              </a>
            </p>
          </div>
          <div className="why-fact">
            <p className="why-big">{t("why.opinionValue")}</p>
            <p>
              {t("why.opinionLabel")}{" "}
              <a href={SOURCES.morpheus} rel="noreferrer">
                {t("why.opinionSource")}
              </a>
            </p>
          </div>
        </div>
        <Link className="text-link" href="/how-we-know">
          {t("why.more")}
        </Link>
      </section>

      <section className="section" aria-labelledby="answers-title">
        <header className="section-head">
          <h2 id="answers-title">{t("verdictsTitle")}</h2>
        </header>
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

      <section className="section scope" aria-labelledby="scope-title">
        <header className="section-head">
          <h2 id="scope-title">{t("scope.title")}</h2>
        </header>
        <div className="scope-columns">
          <div>
            <h3>{t("scope.checksTitle")}</h3>
            <ul className="scope-list">
              {MOTIONS.map((motion) => (
                <li key={motion}>
                  <MotionPictogram motion={motion} />
                  {t(`scope.items.${motion}`)}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>{t("scope.skipsTitle")}</h3>
            <ul className="scope-list scope-skips">
              {SKIPS.map((skip) => (
                <li key={skip}>
                  <SkipPictogram skip={skip} />
                  {t(`scope.skipItems.${skip}`)}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="closing" aria-labelledby="closing-title">
        <div className="closing-inner">
          <h2 id="closing-title">{t("closing.title")}</h2>
          <p>{t("closing.lede")}</p>
          <Link className="button-ink" href="/check">
            {t("cta")}
          </Link>
        </div>
      </section>

      <footer className="site-footer">
        <span className="footer-lockup" aria-hidden="true">
          <span className="brand-mark" />
          <span className="wordmark">{brand("title")}</span>
        </span>
        <p>{t("footer.built")}</p>
        <nav className="footer-links" aria-label={brand("title")}>
          <Link href="/how-we-know">{t("footer.howWeKnow")}</Link>
          <Link href="/privacy">{t("footer.privacy")}</Link>
          <a href={SOURCES.code} rel="noreferrer">
            {t("footer.code")}
          </a>
        </nav>
      </footer>
    </main>
  );
}
