import { getTranslations } from "next-intl/server";

import { UploadForm } from "@/components/UploadForm";
import { resolveLocale } from "@/i18n/locale";

const TIPS = ["still", "whole", "alone", "light"] as const;

export default async function CheckPage({ params }: PageProps<"/[locale]/check">) {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "Check" });

  return (
    <main className="check">
      <header className="check-head">
        <h1>{t("title")}</h1>
        <p className="lede">{t("scope")}</p>
      </header>
      <UploadForm />
      <section className="check-tips" aria-labelledby="tips-title">
        <h2 id="tips-title">{t("tips.title")}</h2>
        <ol>
          {TIPS.map((tip) => (
            <li key={tip}>{t(`tips.${tip}`)}</li>
          ))}
        </ol>
      </section>
    </main>
  );
}
