"use client";

import { useLocale, useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

const noSubscription = () => () => undefined;

/** Share the card as an image where the device allows it; otherwise a WhatsApp link. */
export function ShareButtons({ id, verdict }: { id: string; verdict: string }) {
  const t = useTranslations("Result.share");
  const locale = useLocale();
  const pageUrl = useSyncExternalStore(
    noSubscription,
    () => window.location.href,
    () => "",
  );
  const cardPath = `/${locale}/result/${encodeURIComponent(id)}/card`;
  const text = t("text", { verdict });
  const whatsapp = `https://wa.me/?text=${encodeURIComponent(`${text} ${pageUrl}`)}`;

  async function share() {
    try {
      const blob = await (await fetch(cardPath)).blob();
      const file = new File([blob], "pisa.png", { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], text: `${text} ${pageUrl}` });
        return;
      }
      if (typeof navigator.share === "function") {
        await navigator.share({ text, url: pageUrl });
        return;
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return; // Dismissed.
    }
    window.open(whatsapp, "_blank", "noopener");
  }

  return (
    <section className="share" aria-labelledby="share-title">
      <h2 id="share-title">{t("title")}</h2>
      <div className="share-actions">
        <button type="button" className="button-secondary" onClick={() => void share()}>
          {t("share")}
        </button>
        <a className="button-secondary" href={whatsapp} target="_blank" rel="noopener noreferrer">
          {t("whatsapp")}
        </a>
        <a className="text-link" href={cardPath} download="pisa.png">
          {t("download")}
        </a>
      </div>
    </section>
  );
}
