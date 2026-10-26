import type { VerdictLabel } from "@pisa/contracts";
import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import { resolveLocale } from "@/i18n/locale";

const VERDICTS: readonly VerdictLabel[] = [
  "physically_impossible",
  "consistent_with_real_physics",
  "inconclusive",
];

export default async function HomePage({ params }: PageProps<"/[locale]">) {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "Home" });
  const verdict = await getTranslations({ locale, namespace: "Verdict" });

  return (
    <main className="page">
      <h1>{t("tagline")}</h1>
      <p className="lede">{t("lede")}</p>
      <Link className="button-primary" href="/check">
        {t("cta")}
      </Link>
      <section aria-labelledby="verdicts-title">
        <h2 id="verdicts-title">{t("verdictsTitle")}</h2>
        <ul className="verdict-list">
          {VERDICTS.map((label) => (
            <li key={label}>{verdict(label)}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
