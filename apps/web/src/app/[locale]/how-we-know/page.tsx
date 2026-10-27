import type { EvalRate, EvalReport } from "@pisa/contracts";
import type { Metadata } from "next";
import { getFormatter, getTranslations } from "next-intl/server";

import { IntervalChart, type IntervalGroup } from "@/components/IntervalChart";
import { VerdictIcon } from "@/components/VerdictIcon";
import { resolveLocale } from "@/i18n/locale";
import { LAWS, NEEDS_SCALE, lawNumber, publishedReport } from "@/lib/evaluation";

const ROLES = ["plan", "track", "measure", "explain"] as const;
const LIMITS = ["notProof", "slowMotion", "learning", "scope", "small"] as const;
const RESEARCH = [
  { key: "gravity", href: "https://arxiv.org/abs/2512.02016", source: "arXiv 2512.02016" },
  { key: "morpheus", href: "https://arxiv.org/abs/2504.02918", source: "Morpheus, ICML 2026" },
  { key: "motionphys", href: "https://arxiv.org/abs/2608.20770", source: "MotionPhys, arXiv 2608.20770" },
] as const;
const CODE_URL = "https://github.com/nanoulloa/pisa";

export async function generateMetadata({ params }: PageProps<"/[locale]/how-we-know">): Promise<Metadata> {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "HowWeKnow" });
  return { title: t("eyebrow"), description: t("lede") };
}

/** Answer first: how well Pisa works and how sure we are. Then why it works, then every
 * number behind it, then what it cannot do. */
export default async function HowWeKnowPage({ params }: PageProps<"/[locale]/how-we-know">) {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "HowWeKnow" });
  const format = await getFormatter({ locale });
  const report: EvalReport = publishedReport;
  const percent = (value: number | null) =>
    format.number(value ?? 0, { style: "percent", maximumFractionDigits: 0 });
  const real = report.false_positive_rate.total;
  const generated = report.detection_rate.total;
  const baseline = report.baseline;

  const share = (rate: EvalRate) =>
    `${t("results.count", { count: rate.count, total: rate.total })} (${percent(rate.value)})`;
  const pisa = t("compare.pisa");
  const opinion = t("compare.museSpark");
  const groups: IntervalGroup[] = [
    { title: t("chart.falsePositives"), pick: (r: Rates) => r.false_positive_rate },
    { title: t("chart.detection"), pick: (r: Rates) => r.detection_rate },
  ].map(({ title, pick }) => ({
    title,
    rows: [
      { series: "pisa" as const, label: pisa, rate: pick(report) },
      ...(baseline ? [{ series: "opinion" as const, label: opinion, rate: pick(baseline) }] : []),
    ],
  }));

  return (
    <article className="how" aria-labelledby="how-title">
      <header className="how-intro">
        <span className="eyebrow">{t("eyebrow")}</span>
        <h1 id="how-title">{t("title")}</h1>
        <p className="lede">{t("lede")}</p>
      </header>

      <section className="band" aria-labelledby="results-title">
        <h2 id="results-title">{t("results.title")}</h2>
        <p className={report.synthetic ? "how-notice" : "how-text"}>
          {report.synthetic
            ? t("results.synthetic", { count: report.clips.length, real, generated })
            : t("results.filmed", { count: report.clips.length, real, generated })}
        </p>
        <div className="stats">
          <Stat
            value={t("results.count", { count: report.false_positive_rate.count, total: real })}
            label={t("results.falsePositives")}
            note={t("results.falsePositivesNote", {
              total: real,
              high: percent(report.false_positive_rate.ci_high),
            })}
          />
          <Stat
            value={t("results.count", { count: report.detection_rate.count, total: generated })}
            label={t("results.detection")}
            note={t("results.detectionNote", {
              low: percent(report.detection_rate.ci_low),
              high: percent(report.detection_rate.ci_high),
            })}
          />
          <Stat
            value={t("results.count", {
              count: report.inconclusive_rate.count,
              total: report.inconclusive_rate.total,
            })}
            label={t("results.inconclusive")}
            note={t("results.inconclusiveNote")}
          />
        </div>
        <div className="how-chart">
          <h3 className="how-chart-title">{t("chart.title")}</h3>
          <IntervalChart groups={groups} />
        </div>
      </section>

      <section className="band" aria-labelledby="compare-title">
        <h2 id="compare-title">{t("compare.title")}</h2>
        <p className="how-text">{t("compare.lede")}</p>
        {baseline ? (
          <div className="table-wrap">
            <table className="how-table">
              <thead>
                <tr>
                  <th scope="col">{t("compare.measure")}</th>
                  <th scope="col">{pisa}</th>
                  <th scope="col">{opinion}</th>
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ["falsePositives", report.false_positive_rate, baseline.false_positive_rate],
                    ["detection", report.detection_rate, baseline.detection_rate],
                    ["silent", report.inconclusive_rate, baseline.unsure_rate],
                  ] as const
                ).map(([key, mine, theirs]) => (
                  <tr key={key}>
                    <th scope="row">{t(`compare.${key}`)}</th>
                    <td className="num">{share(mine)}</td>
                    <td className="num">{share(theirs)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="how-text">{t("compare.pending")}</p>
        )}
      </section>

      <section className="band" aria-labelledby="laws-title">
        <h2 id="laws-title">{t("laws.title")}</h2>
        <p className="how-text">{t("laws.lede")}</p>
        <ol className="laws">
          {LAWS.map((law) => (
            <li key={law}>
              <span className="step-number">{t("laws.number", { number: lawNumber(law) })}</span>
              <h3>{t(`laws.${law}.name`)}</h3>
              <p>{t(`laws.${law}.body`)}</p>
              <p className="law-needs">
                {NEEDS_SCALE.has(law) ? t("laws.needsScale") : t("laws.scaleFree")}
              </p>
            </li>
          ))}
        </ol>
      </section>

      <section className="band" aria-labelledby="roles-title">
        <h2 id="roles-title">{t("roles.title")}</h2>
        <dl className="roles">
          {ROLES.map((role) => (
            <div key={role} className={role === "measure" ? "role role-decides" : "role"}>
              <dt>{t(`roles.${role}.who`)}</dt>
              <dd>{t(`roles.${role}.what`)}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="band" aria-labelledby="limits-title">
        <h2 id="limits-title">{t("limits.title")}</h2>
        <ul className="limits">
          {LIMITS.map((limit) => (
            <li key={limit}>{t(`limits.${limit}`)}</li>
          ))}
        </ul>
      </section>

      <section className="band" aria-labelledby="details-title">
        <Details report={report} />
      </section>

      <section className="band" aria-labelledby="research-title">
        <h2 id="research-title">{t("research.title")}</h2>
        <ul className="research">
          {RESEARCH.map(({ key, href, source }) => (
            <li key={key}>
              <p>{t(`research.${key}`)}</p>
              <a href={href} rel="noreferrer">
                {source}
              </a>
            </li>
          ))}
          <li>
            <p>{t("research.code")}</p>
            <a href={CODE_URL} rel="noreferrer">
              github.com/nanoulloa/pisa
            </a>
          </li>
        </ul>
      </section>
    </article>
  );
}

type Rates = Pick<EvalReport, "false_positive_rate" | "detection_rate">;

function Stat({ value, label, note }: { value: string; label: string; note: string }) {
  return (
    <figure className="stat">
      <span className="stat-value">{value}</span>
      <figcaption>
        <strong>{label}</strong> {note}
      </figcaption>
    </figure>
  );
}

/** Progressive disclosure: every law's contribution and every video's verdict. */
async function Details({ report }: { report: EvalReport }) {
  const t = await getTranslations("HowWeKnow.details");
  const laws = await getTranslations("HowWeKnow.laws");
  const verdicts = await getTranslations("Verdict");
  const format = await getFormatter();
  const truth = report.synthetic ? "truthSynthetic" : "truthFilmed";
  const pair = (counts: { real: number; generated: number }) => t("pair", counts);
  return (
    <details className="how-details">
      <summary id="details-title">{t("summary")}</summary>
      <h3>{t("lawsTitle")}</h3>
      <p className="hint">{t("lawsNote")}</p>
      <div className="table-wrap">
        <table className="how-table">
          <thead>
            <tr>
              <th scope="col">{t("law")}</th>
              <th scope="col">{t("measured")}</th>
              <th scope="col">{t("broken")}</th>
              <th scope="col">{t("decisive")}</th>
            </tr>
          </thead>
          <tbody>
            {LAWS.map((law) => {
              const stats = report.tests.find((entry) => entry.test === law);
              if (!stats) return null;
              return (
                <tr key={law}>
                  <th scope="row">{laws(`${law}.name`)}</th>
                  <td className="num">{pair(stats.measured)}</td>
                  <td className="num">{pair(stats.violated)}</td>
                  <td className="num">{pair(stats.decisive)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <h3>{t("clipsTitle")}</h3>
      <div className="table-wrap">
        <table className="how-table how-clips">
          <thead>
            <tr>
              <th scope="col">{t("clip")}</th>
              <th scope="col">{t("truth")}</th>
              <th scope="col">{t("verdict")}</th>
              {report.baseline && <th scope="col">{t("opinion")}</th>}
            </tr>
          </thead>
          <tbody>
            {report.clips.map((clip) => (
              <tr key={clip.id}>
                <th scope="row">
                  <code>{clip.id}</code>
                </th>
                <td>{t(`${truth}.${clip.truth}`)}</td>
                <td>
                  <span className={`verdict-chip verdict-${clip.verdict}`}>
                    <VerdictIcon label={clip.verdict} />
                    {verdicts(clip.verdict)}
                  </span>
                </td>
                {report.baseline && <td>{clip.baseline ? t(`opinions.${clip.baseline}`) : ""}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="hint">
        {t("report", {
          name: report.name,
          date: format.dateTime(new Date(report.created_at), { dateStyle: "long" }),
          policy: report.policy_version,
        })}
      </p>
    </details>
  );
}
