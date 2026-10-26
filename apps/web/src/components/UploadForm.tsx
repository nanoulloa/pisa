"use client";

import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { useRouter } from "@/i18n/navigation";
import { createJob, EngineError, MAX_UPLOAD_BYTES } from "@/lib/engine";

import { ErrorMessage } from "./ErrorMessage";

export function UploadForm() {
  const t = useTranslations("Check");
  const locale = useLocale();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

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

  return (
    <form className="upload" onSubmit={onSubmit}>
      <label className="upload-label" htmlFor="video">
        {t("chooseFile")}
      </label>
      <input
        id="video"
        name="video"
        type="file"
        accept="video/mp4,video/quicktime,.mp4,.mov"
        aria-describedby="video-hint"
        onChange={(event) => {
          setFile(event.target.files?.[0] ?? null);
          setError(null);
        }}
      />
      <p id="video-hint" className="hint">
        {t("fileHint")}
      </p>
      <p className="privacy-note">{t("privacy")}</p>
      {error !== null && <ErrorMessage code={error} />}
      <button className="button-primary" type="submit" disabled={file === null || uploading}>
        {uploading ? t("uploading") : t("submit")}
      </button>
    </form>
  );
}
