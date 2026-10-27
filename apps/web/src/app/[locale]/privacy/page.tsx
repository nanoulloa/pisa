import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { resolveLocale } from "@/i18n/locale";

const SECTIONS = ["what", "kept", "models", "whatsapp", "browser", "services", "rights"] as const;
const ISSUES_URL = "https://github.com/nanoulloa/pisa/issues";

export async function generateMetadata({ params }: PageProps<"/[locale]/privacy">): Promise<Metadata> {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "Privacy" });
  return { title: t("title") };
}

/** What happens to a video and to the data around it, in the order a reader wonders about it. */
export default async function PrivacyPage({ params }: PageProps<"/[locale]/privacy">) {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "Privacy" });
  return (
    <article className="page privacy" aria-labelledby="privacy-title">
      <span className="eyebrow">{t("eyebrow")}</span>
      <h1 id="privacy-title">{t("title")}</h1>
      <p className="lede">{t("lede")}</p>
      {SECTIONS.map((section) => (
        <section key={section}>
          <h2>{t(`${section}.title`)}</h2>
          <p>{t(`${section}.body`)}</p>
        </section>
      ))}
      <p>
        <a className="text-link" href={ISSUES_URL} rel="noreferrer">
          github.com/nanoulloa/pisa/issues
        </a>
      </p>
      <p className="hint">{t("updated")}</p>
    </article>
  );
}
