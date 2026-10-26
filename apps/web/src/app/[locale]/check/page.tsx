import { getTranslations } from "next-intl/server";

import { resolveLocale } from "@/i18n/locale";

export default async function CheckPage({ params }: PageProps<"/[locale]/check">) {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "Check" });

  return (
    <main className="page">
      <h1>{t("title")}</h1>
      <p className="lede">{t("scope")}</p>
    </main>
  );
}
