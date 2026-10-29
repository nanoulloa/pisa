import type { Metadata } from "next";
import { Cormorant_Garamond, Schibsted_Grotesk } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getTranslations } from "next-intl/server";

import { LocaleMenu } from "@/components/LocaleMenu";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Link } from "@/i18n/navigation";
import { resolveLocale } from "@/i18n/locale";
import { routing } from "@/i18n/routing";
import { THEME_SCRIPT } from "@/lib/theme";

import "../globals.css";

const sans = Schibsted_Grotesk({
  subsets: ["latin", "latin-ext"],
  variable: "--font-schibsted",
  display: "swap",
});

const display = Cormorant_Garamond({
  subsets: ["latin", "latin-ext"],
  weight: "500",
  style: "italic",
  variable: "--font-cormorant",
  display: "swap",
});

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: LayoutProps<"/[locale]">): Promise<Metadata> {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "Metadata" });
  return { title: t("title"), description: t("description") };
}

export default async function LocaleLayout({ children, params }: LayoutProps<"/[locale]">) {
  const locale = await resolveLocale(params);
  const t = await getTranslations({ locale, namespace: "Header" });
  const brand = await getTranslations({ locale, namespace: "Metadata" });

  return (
    // The theme script may set data-theme before React hydrates.
    <html lang={locale} className={`${sans.variable} ${display.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <NextIntlClientProvider>
          <header className="site-header">
            <Link className="brand-link" href="/" aria-label={t("home")}>
              <span className="brand-mark" aria-hidden="true" />
              <span className="wordmark" aria-hidden="true">
                {brand("title")}
              </span>
            </Link>
            <nav className="header-nav" aria-label={brand("title")}>
              <Link className="header-link" href="/how-we-know">
                {t("howWeKnow")}
              </Link>
              <div className="header-controls">
                <LocaleMenu />
                <ThemeToggle />
              </div>
            </nav>
          </header>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
