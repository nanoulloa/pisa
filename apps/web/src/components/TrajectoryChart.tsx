import type { EvidenceSeries } from "@pisa/contracts";
import { useTranslations } from "next-intl";

import { chartPoints, type Point } from "@/lib/result";

const WIDTH = 640;
const HEIGHT = 280;
const PAD = 24;

/** Height over time: the measured points in ink, the ghost in lime. */
export function TrajectoryChart({ series }: { series: EvidenceSeries }) {
  const t = useTranslations("Result.chart");
  const ghost = useTranslations("Result.evidence.ghost");
  const { measured, ghost: path } = chartPoints(series, WIDTH, HEIGHT, PAD);
  return (
    <figure className="chart">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={t("label", { ghost: ghost(series.model) })}
      >
        <line className="chart-axis" x1={PAD} y1={HEIGHT - PAD} x2={WIDTH - PAD} y2={HEIGHT - PAD} />
        <line className="chart-axis" x1={PAD} y1={PAD} x2={PAD} y2={HEIGHT - PAD} />
        <polyline className="chart-ghost-edge" points={polyline(path)} />
        <polyline className="chart-ghost" points={polyline(path)} />
        {measured.map(([x, y], index) => (
          <circle key={index} className="chart-measured" cx={x} cy={y} r={3.5} />
        ))}
      </svg>
      <figcaption className="legend">
        <span>
          <span className="swatch swatch-points" aria-hidden="true" /> {t("measured")}
        </span>
        <span>
          <span className="swatch swatch-ghost" aria-hidden="true" /> {ghost(series.model)}
        </span>
        <span className="hint">{t("axes")}</span>
      </figcaption>
    </figure>
  );
}

function polyline(points: Point[]): string {
  return points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
}
