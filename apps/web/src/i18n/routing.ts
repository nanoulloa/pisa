import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["en", "es", "zh-CN", "pt-BR"],
  defaultLocale: "en",
});

/** Each language's name in that language, for the switcher. */
export const localeNames: Record<(typeof routing.locales)[number], string> = {
  en: "English",
  es: "Español",
  "zh-CN": "中文",
  "pt-BR": "Português",
};
