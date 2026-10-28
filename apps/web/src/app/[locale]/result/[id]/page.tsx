import { preconnect } from "react-dom";

import { JobView } from "@/components/JobView";
import { resolveLocale } from "@/i18n/locale";
import { ENGINE_URL, finishedResult } from "@/lib/engine";

export default async function ResultPage({ params }: PageProps<"/[locale]/result/[id]">) {
  await resolveLocale(params);
  const { id } = await params;
  preconnect(ENGINE_URL); // The evidence video comes from the engine.
  // A finished check arrives with its verdict in the HTML: a link opened from WhatsApp shows
  // the answer without waiting for scripts and two more trips to the engine.
  return <JobView id={id} initial={await finishedResult(id)} />;
}
