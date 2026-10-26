import type { VerdictLabel } from "@pisa/contracts";
import type { CSSProperties } from "react";

import { VerdictIcon } from "./VerdictIcon";

/*
 * The same 1.5 m drop twice. Each sphere is drawn over its ghost, the place real gravity puts
 * it. Filmed: they fall together. Generated: the sphere falls with g = 2 m/s², the weak gravity
 * generated clips often show, and the ghost leaves it behind. The CSS easing
 * cubic-bezier(1/3, 0, 2/3, 1/3) is exactly y = t², so both falls are true constant
 * acceleration; only the distance covered in the same time differs.
 */

const EARTH_G = 9.81;
const GENERATED_G = 2.0;
const DROP_PX = 137; // From the release point to the ground, in the panel's units.

// The tower from the Plumb mark (64-unit grid), scaled into the panel.
const TOWER = [
  "17.25,54 29.25,54 29.809,46 17.809,46",
  "17.949,44 29.949,44 30.509,36 18.509,36",
  "18.649,34 30.649,34 31.208,26 19.208,26",
  "19.348,24 31.348,24 31.907,16 19.907,16",
  "22.047,14 30.047,14 30.327,10 22.327,10",
];

type Panel = {
  label: string;
  verdict: VerdictLabel;
  verdictLabel: string;
  note: string;
  gravity: number;
};

export function GhostDemo({
  filmed,
  generated,
  legend,
  caption,
}: {
  filmed: Omit<Panel, "gravity" | "verdict">;
  generated: Omit<Panel, "gravity" | "verdict">;
  legend: string;
  caption: string;
}) {
  return (
    <figure className="ghost-demo">
      <div className="ghost-panels">
        <DemoPanel {...filmed} verdict="consistent_with_real_physics" gravity={EARTH_G} />
        <DemoPanel {...generated} verdict="physically_impossible" gravity={GENERATED_G} />
      </div>
      <p className="ghost-legend">
        <span className="ghost-swatch" aria-hidden="true" />
        {legend}
      </p>
      <figcaption className="hint">{caption}</figcaption>
    </figure>
  );
}

function DemoPanel({ label, verdict, verdictLabel, note, gravity }: Panel) {
  const ballFall = { "--fall": `${(DROP_PX * gravity) / EARTH_G}px` } as CSSProperties;
  const ghostFall = { "--fall": `${DROP_PX}px` } as CSSProperties;
  return (
    <div className="ghost-panel">
      <span className="eyebrow">{label}</span>
      <svg viewBox="0 112 240 200" role="img" aria-label={`${label}. ${verdictLabel}. ${note}`}>
        <rect className="panel-ground" x="16" y="300" width="208" height="2" />
        <g className="panel-tower" transform="translate(9.4 105.6) scale(3.6)">
          {TOWER.map((points) => (
            <polygon key={points} points={points} />
          ))}
        </g>
        <line className="panel-plumb" x1="148" y1="140" x2="148" y2="300" />
        <g className="demo-fall" style={ghostFall}>
          <circle className="panel-ghost" cx="148" cy="152" r="14" />
        </g>
        <g className="demo-fall" style={ballFall}>
          <circle className="panel-ball" cx="148" cy="152" r="10" />
        </g>
      </svg>
      <span className={`verdict-chip verdict-${verdict}`}>
        <VerdictIcon label={verdict} />
        {verdictLabel}
      </span>
      <span className="hint">{note}</span>
    </div>
  );
}
