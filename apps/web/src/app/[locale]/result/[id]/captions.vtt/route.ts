import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { routing } from "@/i18n/routing";
import { evidenceCues, toWebVtt } from "@/lib/captions";
import { getResult } from "@/lib/engine";

/** Captions for the evidence video, in the page's language: what is drawn, and when. */
export async function GET(_request: Request, { params }: RouteContext<"/[locale]/result/[id]/captions.vtt">) {
  const { locale, id } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const result = await getResult(id).catch(() => null);
  if (!result) notFound();
  const [t, verdicts] = await Promise.all([
    getTranslations({ locale, namespace: "Result.evidence.captions" }),
    getTranslations({ locale, namespace: "Verdict" }),
  ]);
  const cues = evidenceCues(result, {
    intro: t("intro"),
    ghost: (model) => t(model),
    verdict: result.verdict ? t("verdict", { verdict: verdicts(result.verdict.label) }) : null,
  });
  return new Response(toWebVtt(cues), {
    headers: { "Content-Type": "text/vtt; charset=utf-8", "Cache-Control": "public, max-age=3600" },
  });
}
