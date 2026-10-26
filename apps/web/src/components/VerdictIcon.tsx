import type { VerdictLabel } from "@pisa/contracts";

/** Each verdict has its own shape, so color is never the only signal. */
export function VerdictIcon({ label }: { label: VerdictLabel }) {
  return (
    <svg className="verdict-icon" viewBox="0 0 24 24" aria-hidden="true">
      {label === "inconclusive" ? (
        <>
          <circle cx="12" cy="12" r="9" strokeDasharray="3.2 3" />
          <circle cx="12" cy="12" r="1.2" fill="currentColor" />
        </>
      ) : (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d={label === "physically_impossible" ? "M5.7 5.7l12.6 12.6" : "M7.5 12.5l3 3 6-7"} />
        </>
      )}
    </svg>
  );
}
