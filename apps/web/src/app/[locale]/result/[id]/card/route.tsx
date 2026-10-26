import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";

import { renderCard } from "@/lib/card";
import { routing } from "@/i18n/routing";

/** The 4:5 share card as a PNG, to send as an image on WhatsApp. */
export async function GET(_request: Request, { params }: RouteContext<"/[locale]/result/[id]/card">) {
  const { locale, id } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  return renderCard(locale, id, "card");
}
