"use client";

import type { EvidenceVideo as Video, GhostModel } from "@pisa/contracts";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { ENGINE_URL } from "@/lib/engine";

/** The clip with the object outlined and its ghost; it plays by itself unless motion is reduced. */
export function EvidenceVideo({ id, video, model }: { id: string; video: Video; model: GhostModel }) {
  const t = useTranslations("Result.evidence");
  const ref = useRef<HTMLVideoElement>(null);
  const [openedAt] = useState(() => Date.now());

  useEffect(() => {
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      ref.current?.play().catch(() => undefined); // Browsers may still refuse; controls remain.
    }
  }, []);

  if (openedAt >= Date.parse(video.expires_at)) return <p className="note">{t("expired")}</p>;
  return (
    <figure className="evidence">
      <video
        ref={ref}
        src={`${ENGINE_URL}/jobs/${encodeURIComponent(id)}/evidence.mp4`}
        width={video.width}
        height={video.height}
        controls
        muted
        loop
        playsInline
        preload="metadata"
        aria-describedby="evidence-legend"
      />
      <figcaption id="evidence-legend">
        <ul className="legend">
          <li>
            <span className="swatch swatch-outline" aria-hidden="true" /> {t("object")}
          </li>
          <li>
            <span className="swatch swatch-points" aria-hidden="true" /> {t("points")}
          </li>
          <li>
            <span className="swatch swatch-ghost" aria-hidden="true" /> {t(`ghost.${model}`)}
          </li>
        </ul>
        {video.playback_rate < 1 && <p className="hint">{t("slowed")}</p>}
        <p className="hint">{t("kept")}</p>
      </figcaption>
    </figure>
  );
}
