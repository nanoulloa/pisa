"use client";

import { useEffect, useRef } from "react";

/** A short silent loop that only plays when the visitor has not asked for less motion. Its
 * content is also given in text next to it, so it is hidden from assistive technology. */
export function LoopVideo({ src, poster, className }: { src: string; poster: string; className?: string }) {
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const element = video.current;
    if (element === null || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    element.play().catch(() => undefined); // Some browsers refuse autoplay; the poster stays.
  }, []);

  return (
    <video
      ref={video}
      className={className}
      src={src}
      poster={poster}
      muted
      loop
      playsInline
      preload="metadata"
      aria-hidden="true"
      tabIndex={-1}
    />
  );
}
