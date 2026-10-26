"use client";

import { useTranslations } from "next-intl";

const KNOWN_CODES = [
  "unsupported_format",
  "video_too_long",
  "file_too_large",
  "unknown_duration",
  "resolution_too_high",
  "transcode_failed",
  "empty_window",
  "paid_calls_disabled",
  "spend_cap_reached",
  "network",
  "job_not_found",
  "internal_error",
] as const;

type KnownCode = (typeof KNOWN_CODES)[number];

function isKnown(code: string): code is KnownCode {
  return (KNOWN_CODES as readonly string[]).includes(code);
}

/** Explains an engine error code in the visitor's language. Unknown codes read as a generic failure. */
export function ErrorMessage({ code }: { code: string }) {
  const t = useTranslations("Errors");
  return (
    <p role="alert" className="error">
      {t(isKnown(code) ? code : "internal_error")}
    </p>
  );
}
