"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { Link, usePathname } from "@/i18n/navigation";
import { localeNames, routing } from "@/i18n/routing";

/** One button that opens the list of languages, each named in its own language. */
export function LocaleMenu() {
  const t = useTranslations("LocaleSwitcher");
  const current = useLocale();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="locale-menu" ref={root}>
      <button
        ref={button}
        type="button"
        className="header-button"
        aria-expanded={open}
        aria-controls="locale-list"
        aria-label={t("button", { name: localeNames[current] })}
        onClick={() => setOpen((isOpen) => !isOpen)}
      >
        <span aria-hidden="true">{localeNames[current]}</span>
        <span className="chevron" aria-hidden="true" />
      </button>
      <ul id="locale-list" className="locale-list" hidden={!open}>
        {routing.locales.map((locale) => (
          <li key={locale}>
            <Link
              href={pathname}
              locale={locale}
              lang={locale}
              aria-current={locale === current ? "true" : undefined}
              onClick={() => setOpen(false)}
            >
              {localeNames[locale]}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
