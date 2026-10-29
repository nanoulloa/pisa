"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";
import { type FormEvent, useEffect, useState } from "react";

import { useRouter } from "@/i18n/navigation";
import { createJob, EngineError, MAX_UPLOAD_BYTES } from "@/lib/engine";

import { ErrorMessage } from "./ErrorMessage";

/** The file input covers the whole drop area, so a click or a drop anywhere on it works. Once a
 * video is chosen, its first frame and size show before anything is sent. */
export function UploadForm() {
  const t = useTranslations("Check");
  const locale = useLocale();
  const format = useFormatter();
  const router = useRouter();
  const [chosen, setChosen] = useState<{ file: File; preview: string } | null>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const file = chosen?.file ?? null;

  // Each preview link is released once another video replaces it, or the form goes away.
  useEffect(() => {
    if (chosen === null) return;
    return () => URL.revokeObjectURL(chosen.preview);
  }, [chosen]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (file === null) return;
    if (file.size > MAX_UPLOAD_BYTES) {
      setError("file_too_large");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const job = await createJob(file, locale);
      router.push(`/result/${job.id}`);
    } catch (caught) {
      setError(caught instanceof EngineError ? caught.code : "internal_error");
      setUploading(false);
    }
  }

  const megabytes = (file?.size ?? 0) / 1_000_000;
  const size =
    megabytes >= 1
      ? format.number(megabytes, { style: "unit", unit: "megabyte", maximumFractionDigits: 1 })
      : format.number(megabytes * 1000, { style: "unit", unit: "kilobyte", maximumFractionDigits: 0 });

  return (
    <form className="upload" onSubmit={onSubmit}>
      <div className={["dropzone", dragging && "is-dragging", file && "has-file"].filter(Boolean).join(" ")}>
        <input
          id="video"
          name="video"
          type="file"
          className="dropzone-input"
          accept="video/mp4,video/quicktime,.mp4,.mov"
          aria-describedby="video-hint"
          onDragEnter={() => setDragging(true)}
          onDragLeave={() => setDragging(false)}
          onDrop={() => setDragging(false)}
          onChange={(event) => {
            const picked = event.target.files?.[0];
            setChosen(picked ? { file: picked, preview: URL.createObjectURL(picked) } : null);
            setError(null);
          }}
        />
        {chosen !== null ? (
          <div className="dropzone-file">
            <video className="dropzone-preview" src={`${chosen.preview}#t=0.1`} muted playsInline preload="metadata" aria-hidden="true" />
            <div className="dropzone-file-text">
              <span className="dropzone-file-label">{t("selected")}</span>
              <span className="dropzone-file-name">{chosen.file.name}</span>
              <span className="hint">{size}</span>
              <label className="dropzone-change" htmlFor="video">
                {t("change")}
              </label>
            </div>
          </div>
        ) : (
          <div className="dropzone-empty">
            <svg className="dropzone-icon" viewBox="0 0 64 64" aria-hidden="true">
              <rect className="dropzone-frame" x="6" y="10" width="52" height="44" rx="3" />
              {[0, 1, 2, 3, 4].map((step) => (
                <circle
                  key={step}
                  cx={16 + 8 * step}
                  cy={20 + 1.5 * step * step}
                  r="3.5"
                  opacity={0.3 + 0.175 * step}
                />
              ))}
            </svg>
            <label className="dropzone-title" htmlFor="video">
              {t("chooseFile")}
            </label>
            <span className="dropzone-or">{t("drop")}</span>
          </div>
        )}
      </div>
      <p id="video-hint" className="hint">
        {t("fileHint")}
      </p>
      {error !== null && <ErrorMessage code={error} />}
      <button className="button-primary button-wide" type="submit" disabled={file === null || uploading}>
        {uploading ? t("uploading") : t("submit")}
      </button>
      <p className="privacy-note">{t("privacy")}</p>
    </form>
  );
}
