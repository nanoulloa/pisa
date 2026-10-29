/*
 * Drawings for the landing page, on the same grid as the mark: strobe pictograms for what Pisa
 * checks, and one small frame per step of the pipeline. All of them are decorative; the text
 * next to each one says the same thing.
 */

export type Motion = "fall" | "throw" | "bounce" | "pair";
export type Skip = "faces" | "lips" | "voices";
export type Step = "watching" | "tracking" | "measuring" | "explaining";

/** A ball caught at equal time steps, oldest faintest: the gaps grow as it speeds up. */
const STROBE = [0, 1, 2, 3, 4, 5].map((step) => ({ y: 8 + 1.8 * step * step, opacity: 0.25 + 0.15 * step }));
const ARC = [0, 1, 2, 3, 4, 5, 6].map((step) => ({
  x: 8 + 8 * step,
  y: 50 - 38 * (1 - ((step - 3) / 3) ** 2),
  opacity: 0.25 + 0.125 * step,
}));

export function MotionPictogram({ motion }: { motion: Motion }) {
  const columns = motion === "pair" ? [22, 42] : [32];
  return (
    <svg className="pictogram" viewBox="0 0 64 64" aria-hidden="true">
      {(motion === "fall" || motion === "pair") &&
        columns.map((x) =>
          STROBE.map((ball) => (
            <circle key={`${x}-${ball.y}`} cx={x} cy={ball.y} r="3.5" opacity={ball.opacity} />
          )),
        )}
      {motion === "throw" &&
        ARC.map((ball) => <circle key={ball.x} cx={ball.x} cy={ball.y} r="3.5" opacity={ball.opacity} />)}
      {motion === "bounce" && (
        <>
          <path className="pictogram-line" opacity="0.45" d="M6 8 Q14 8 20 56 Q28 22 38 56 Q44 36 50 56" />
          <circle cx="50" cy="52.5" r="3.5" />
        </>
      )}
      <line className="pictogram-line" x1="2" y1="60" x2="62" y2="60" />
    </svg>
  );
}

export function SkipPictogram({ skip }: { skip: Skip }) {
  return (
    <svg className="pictogram pictogram-skip" viewBox="0 0 48 48" aria-hidden="true">
      {skip === "faces" && (
        <>
          <circle className="pictogram-line" cx="24" cy="24" r="14" />
          <circle cx="19" cy="21" r="1.8" />
          <circle cx="29" cy="21" r="1.8" />
          <path className="pictogram-line" d="M18.5 29 Q24 33 29.5 29" />
        </>
      )}
      {skip === "lips" && (
        <path
          className="pictogram-line"
          d="M8 24 Q16 14 24 19 Q32 14 40 24 Q32 34 24 34 Q16 34 8 24 Z M8 24 H40"
        />
      )}
      {skip === "voices" && (
        <path
          className="pictogram-line"
          d="M8 22v4M14 16v16M20 10v28M26 18v12M32 13v22M38 20v8"
        />
      )}
      <line className="pictogram-strike" x1="6" y1="42" x2="42" y2="6" />
    </svg>
  );
}

/** The same falling ball through the four steps, next to the ruler it is measured against. */
export function StepArt({ step }: { step: Step }) {
  return (
    <svg className="step-art" viewBox="0 0 176 120" aria-hidden="true">
      <rect className="step-frame" x="8" y="8" width="160" height="104" rx="3" />
      {step !== "measuring" && step !== "explaining" && (
        <g className="step-faint">
          <line x1="32" y1="20" x2="32" y2="76" />
          {[20, 34, 48, 62, 76].map((y) => (
            <line key={y} x1="26" y1={y} x2="32" y2={y} />
          ))}
        </g>
      )}
      {step === "watching" && (
        <>
          <circle className="step-ball" cx="88" cy="44" r="7" />
          <g className="step-faint">
            <line x1="24" y1="96" x2="152" y2="96" />
            {[24, 40, 56, 72, 88, 104, 120, 136, 152].map((x) => (
              <line key={x} x1={x} y1="93" x2={x} y2="99" />
            ))}
          </g>
          <path className="step-window" d="M64 89 v14 M120 89 v14 M64 96 H120" />
        </>
      )}
      {step === "tracking" && (
        <>
          {[22, 32].map((y) => (
            <circle key={y} className="step-ring-faint" cx="88" cy={y} r="11" />
          ))}
          <circle className="step-ball" cx="88" cy="56" r="7" />
          <circle className="step-ring-outer" cx="88" cy="56" r="12" />
          <circle className="step-ring" cx="88" cy="56" r="12" />
        </>
      )}
      {step === "measuring" && (
        <>
          <g className="step-faint">
            <line x1="22" y1="20" x2="22" y2="104" />
            <line x1="22" y1="104" x2="156" y2="104" />
          </g>
          {/* Both curves are y = t²: x(s) and y(s) of a quadratic Bézier with a flat start. */}
          <path className="step-ghost" d="M28 26 Q68 26 108 98" />
          <path className="step-fit" d="M28 26 Q88 26 148 98" />
          {[0, 1, 2, 3, 4, 5, 6].map((index) => (
            <circle
              key={index}
              className="step-point"
              cx={28 + index * 20}
              cy={26 + 72 * (index / 6) ** 2}
              r="3.2"
            />
          ))}
        </>
      )}
      {step === "explaining" && (
        <>
          <path
            className="step-bubble"
            d="M28 28 h120 a6 6 0 0 1 6 6 v38 a6 6 0 0 1 -6 6 H64 l-12 12 v-12 H28 a6 6 0 0 1 -6 -6 V34 a6 6 0 0 1 6 -6 Z"
          />
          <circle className="step-ring step-verdict" cx="45" cy="53" r="10" />
          <path className="step-ring step-verdict" d="M37.9 45.9 L52.1 60.1" />
          <text className="step-langs" x="64" y="58">
            ES EN 中文 PT
          </text>
        </>
      )}
    </svg>
  );
}
