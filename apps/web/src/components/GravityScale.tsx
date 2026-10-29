import type { CSSProperties } from "react";

/*
 * Gravity on one axis from 0 to 10 m/s²: the band generated videos fall in (arXiv 2512.02016)
 * next to the Moon, Mars and Earth. Built from HTML so its labels stay readable on a phone.
 */

const MAX = 10;
const GENERATED = [0.38, 2.27] as const;

type Labels = {
  generated: string;
  moon: string;
  mars: string;
  earth: string;
  summary: string;
  format: (value: number) => string;
};

export function GravityScale({ generated, moon, mars, earth, summary, format }: Labels) {
  const at = (value: number) => ({ "--at": `${(value / MAX) * 100}%` }) as CSSProperties;
  const bodies = [
    { name: moon, value: 1.62, className: "scale-body" },
    { name: mars, value: 3.71, className: "scale-body" },
    { name: earth, value: 9.81, className: "scale-body scale-earth" },
  ];

  return (
    <figure className="gravity-scale">
      <p className="visually-hidden">{summary}</p>
      <div className="scale-plot" aria-hidden="true">
        <div
          className="scale-band"
          style={
            {
              "--from": `${(GENERATED[0] / MAX) * 100}%`,
              "--to": `${(GENERATED[1] / MAX) * 100}%`,
            } as CSSProperties
          }
        >
          <span className="scale-band-label">
            {generated}
            <span>
              {format(GENERATED[0])}–{format(GENERATED[1])}
            </span>
          </span>
        </div>
        <div className="scale-axis">
          {Array.from({ length: MAX + 1 }, (_, value) => (
            <span key={value} className="scale-tick" style={at(value)}>
              <span>{value}</span>
            </span>
          ))}
        </div>
        {bodies.map((body) => (
          <span key={body.name} className={body.className} style={at(body.value)}>
            <span className="scale-body-name">{body.name}</span>
            <span>{format(body.value)}</span>
          </span>
        ))}
        <span className="scale-unit">m/s²</span>
      </div>
    </figure>
  );
}
