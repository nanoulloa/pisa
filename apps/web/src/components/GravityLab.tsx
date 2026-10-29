"use client";

import type { VerdictLabel } from "@pisa/contracts";
import { useFormatter, useTranslations } from "next-intl";
import { type CSSProperties, useId, useState } from "react";

import { VerdictIcon } from "./VerdictIcon";

/*
 * A strobe photograph of one 1.5 m drop, taken 15 times a second: on the left under Earth's
 * gravity (the ghost), on the right under the gravity the visitor picks. Dashed lines join the
 * two balls at the same instant, so a wrong gravity shows as lines that tilt. The moving balls
 * use the easing cubic-bezier(1/3, 0, 2/3, 1/3), which is exactly y = t², so they fall with
 * true constant acceleration, slowed down so the eye can follow.
 */

const EARTH_G = 9.81;
const GENERATED_G = 2.0;
const MIN_G = 1;
const MAX_G = 25;
const HEIGHT_M = 1.5;
const FRAME_S = 1 / 15;
const SLOWDOWN = 4;
const TOLERANCE = 0.1; // Within 10 % of Earth's gravity the illustration calls it consistent.
const PRESETS = [
  { key: "generated", value: GENERATED_G },
  { key: "filmed", value: EARTH_G },
] as const;

const TOP = 64;
const GROUND = 444;
const PX_PER_M = (GROUND - TOP) / HEIGHT_M;
const GHOST_X = 128;
const VIDEO_X = 232;
const RADIUS = 10;
const RULER_X = 58;

function landing(g: number): number {
  return Math.sqrt((2 * HEIGHT_M) / g);
}

/** Where a 15 fps camera catches the ball, from release until it lands. */
function strobe(g: number): { t: number; y: number }[] {
  const frames = Math.floor(landing(g) / FRAME_S + 1e-9);
  return Array.from({ length: frames + 1 }, (_, index) => {
    const t = index * FRAME_S;
    return { t, y: TOP + 0.5 * g * t * t * PX_PER_M };
  });
}

export function GravityLab() {
  const t = useTranslations("Home.lab");
  const verdicts = useTranslations("Verdict");
  const format = useFormatter();
  const sliderId = useId();
  const [g, setG] = useState(GENERATED_G);
  const [take, setTake] = useState(0);
  const [playing, setPlaying] = useState(true);

  const ghost = strobe(EARTH_G);
  const video = strobe(g);
  const ratio = g / EARTH_G;
  const verdict: VerdictLabel =
    Math.abs(ratio - 1) <= TOLERANCE ? "consistent_with_real_physics" : "physically_impossible";
  const gText = t("value", { value: format.number(g, { maximumFractionDigits: 1, minimumFractionDigits: 1 }) });
  const earthText = t("value", { value: format.number(EARTH_G) });
  const times = (value: number) => format.number(value, { maximumFractionDigits: 1 });
  const comparison =
    verdict === "consistent_with_real_physics"
      ? t("same")
      : ratio < 1
        ? t("weaker", { ratio: times(1 / ratio) })
        : t("stronger", { ratio: times(ratio) });

  const drop = (value: number) => {
    setG(value);
    setPlaying(true);
    setTake((count) => count + 1);
  };

  return (
    <figure className="lab">
      <div className="lab-plate">
        <div className="lab-presets" role="group" aria-label={t("presets")}>
          {PRESETS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              className="lab-preset"
              aria-pressed={Math.abs(g - preset.value) < 0.05}
              onClick={() => drop(preset.value)}
            >
              {t(preset.key)}
            </button>
          ))}
        </div>

        <svg
          className={playing ? "lab-scene is-playing" : "lab-scene"}
          viewBox="0 0 280 480"
          role="img"
          aria-label={t("summary", { video: gText, earth: earthText, verdict: verdicts(verdict) })}
        >
          <Ruler format={(value) => format.number(value, { minimumFractionDigits: 1 })} unit={t("meters")} />
          <text className="lab-column-label lab-ghost-label" x={GHOST_X} y={28} textAnchor="middle">
            {t("ghost")}
          </text>
          <text className="lab-column-label" x={VIDEO_X} y={28} textAnchor="middle">
            {t("video")}
          </text>
          <line className="lab-ground" x1={RULER_X} x2={272} y1={GROUND + RADIUS} y2={GROUND + RADIUS} />

          <g key={take}>
            {ghost.slice(0, video.length).map((point, index) => (
              <line
                key={`pair-${index}`}
                className="lab-instant"
                x1={GHOST_X + RADIUS + 4}
                y1={point.y}
                x2={VIDEO_X - RADIUS - 4}
                y2={video[index]?.y ?? point.y}
                style={delay(point.t)}
              />
            ))}
            {ghost.map((point, index) => (
              <circle
                key={`ghost-${index}`}
                className="lab-flash lab-ghost"
                cx={GHOST_X}
                cy={point.y}
                r={RADIUS}
                style={delay(point.t)}
              />
            ))}
            {video.map((point, index) => (
              <circle
                key={`video-${index}`}
                className="lab-flash lab-ball"
                cx={VIDEO_X}
                cy={point.y}
                r={RADIUS}
                style={delay(point.t)}
              />
            ))}
            <circle className="lab-falling lab-ghost" cx={GHOST_X} cy={TOP} r={RADIUS + 2} style={fall(EARTH_G)} />
            <circle className="lab-falling lab-ball" cx={VIDEO_X} cy={TOP} r={RADIUS + 2} style={fall(g)} />
          </g>
        </svg>

        <div className="lab-readout">
          <div>
            <span className="lab-readout-label">{t("videoGravity")}</span>
            <span className="lab-readout-value">{gText}</span>
          </div>
          <div>
            <span className="lab-readout-label">{t("earthGravity")}</span>
            <span className="lab-readout-value lab-readout-earth">{earthText}</span>
          </div>
        </div>

        <label className="lab-slider-label" htmlFor={sliderId}>
          {t("slider")}
        </label>
        <input
          id={sliderId}
          className="lab-slider"
          type="range"
          min={MIN_G}
          max={MAX_G}
          step={0.1}
          value={g}
          aria-valuetext={gText}
          onChange={(event) => {
            setG(Number(event.target.value));
            setPlaying(false);
          }}
        />

        <div className="lab-footer">
          <output className={`lab-verdict verdict-${verdict}`} htmlFor={sliderId} aria-live="polite">
            <VerdictIcon label={verdict} />
            <span>
              <strong>{verdicts(verdict)}</strong>
              <span className="lab-comparison">{comparison}</span>
            </span>
          </output>
          <button type="button" className="lab-replay" onClick={() => drop(g)}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="5.5" r="3" />
              <path d="M12 11.5v9m-3.5-3.5 3.5 3.5 3.5-3.5" />
            </svg>
            {t("replay")}
          </button>
        </div>
      </div>
      <figcaption>{t("caption")}</figcaption>
    </figure>
  );
}

function Ruler({ format, unit }: { format: (value: number) => string; unit: string }) {
  const ticks = Array.from({ length: 16 }, (_, index) => index / 10);
  return (
    <g className="lab-ruler" aria-hidden="true">
      <line x1={RULER_X} x2={RULER_X} y1={TOP} y2={GROUND} />
      {ticks.map((meters) => {
        const y = TOP + meters * PX_PER_M;
        const major = Math.round(meters * 10) % 5 === 0;
        return (
          <g key={meters}>
            <line x1={RULER_X - (major ? 12 : 6)} x2={RULER_X} y1={y} y2={y} />
            {major && (
              <text x={RULER_X - 16} y={y + 4} textAnchor="end">
                {meters === HEIGHT_M ? `${format(meters)} ${unit}` : format(meters)}
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}

function delay(seconds: number): CSSProperties {
  return { "--at": `${(seconds * SLOWDOWN).toFixed(3)}s` } as CSSProperties;
}

function fall(g: number): CSSProperties {
  return {
    "--drop": `${(GROUND - TOP).toFixed(1)}px`,
    "--fall-s": `${(landing(g) * SLOWDOWN).toFixed(3)}s`,
  } as CSSProperties;
}
