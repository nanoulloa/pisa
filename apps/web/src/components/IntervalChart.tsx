import type { EvalRate } from "@pisa/contracts";
import { useFormatter, useTranslations } from "next-intl";

export type IntervalSeries = "pisa" | "opinion";

export type IntervalRow = { series: IntervalSeries; label: string; rate: EvalRate };

export type IntervalGroup = { title: string; rows: IntervalRow[] };

const TICKS = [0, 0.25, 0.5, 0.75, 1] as const;

/** Shares of videos as dots on a 0 to 100% track, each with its 95% interval as a line.
 * Pisa is the series that matters: a filled dot in ink. A model's opinion is context: a
 * hollow dot in muted ink, so the two never differ by color alone. */
export function IntervalChart({ groups }: { groups: IntervalGroup[] }) {
  const t = useTranslations("HowWeKnow.chart");
  const format = useFormatter();
  const percent = (value: number) =>
    format.number(value, { style: "percent", maximumFractionDigits: 0 });
  const position = (value: number) => `${(value * 100).toFixed(2)}%`;
  const series = [...new Set(groups.flatMap((group) => group.rows.map((row) => row.series)))];

  return (
    <figure className="intervals">
      {series.length > 1 && (
        <div className="intervals-legend">
          {groups[0]?.rows.map((row) => (
            <span key={row.series}>
              <span className={`interval-key interval-key-${row.series}`} aria-hidden="true" />
              {row.label}
            </span>
          ))}
        </div>
      )}
      {groups.map((group) => (
        <div key={group.title} className="interval-group">
          <h3>{group.title}</h3>
          {group.rows.map((row) => {
            const { count, total, value, ci_low: low, ci_high: high } = row.rate;
            if (value === null || low === null || high === null) return null;
            const summary = t("row", {
              who: row.label,
              count,
              total,
              value: percent(value),
              low: percent(low),
              high: percent(high),
            });
            return (
              <div key={row.series} className={`interval-row interval-${row.series}`}>
                <span className="interval-label">{row.label}</span>
                <svg className="interval-track" role="img" aria-label={summary}>
                  <title>{summary}</title>
                  {TICKS.map((tick) => (
                    <line
                      key={tick}
                      className="interval-grid"
                      x1={position(tick)}
                      x2={position(tick)}
                      y1="0"
                      y2="100%"
                    />
                  ))}
                  <line
                    className="interval-range"
                    x1={position(low)}
                    x2={position(high)}
                    y1="50%"
                    y2="50%"
                  />
                  <circle className="interval-dot" cx={position(value)} cy="50%" r="6" />
                </svg>
                <span className="interval-value">{percent(value)}</span>
              </div>
            );
          })}
        </div>
      ))}
      <div className="interval-row interval-axis" aria-hidden="true">
        <span />
        <span className="interval-ticks">
          {TICKS.filter((tick) => tick !== 0.25 && tick !== 0.75).map((tick) => (
            <span key={tick} style={{ left: position(tick) }}>
              {percent(tick)}
            </span>
          ))}
        </span>
        <span />
      </div>
      <figcaption className="hint">{t("caption")}</figcaption>
    </figure>
  );
}
