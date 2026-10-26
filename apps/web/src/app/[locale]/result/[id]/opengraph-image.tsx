import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";

import { routing } from "@/i18n/routing";
import { CARD_SIZES, renderCard } from "@/lib/card";

/** The link preview WhatsApp and others show when the result page is shared. */
export const alt = "Pisa";
export const size = CARD_SIZES.preview;
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ locale: string; id: string }> }) {
  const { locale, id } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  return renderCard(locale, id, "preview");
}
