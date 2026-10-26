"use client";

import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

import { type Theme, THEME_STORAGE_KEY } from "@/lib/theme";

const DARK_QUERY = "(prefers-color-scheme: dark)";
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  const media = window.matchMedia(DARK_QUERY);
  media.addEventListener("change", listener);
  listeners.add(listener);
  return () => {
    media.removeEventListener("change", listener);
    listeners.delete(listener);
  };
}

/** The theme on screen: the saved choice if there is one, otherwise the system's. */
function currentTheme(): Theme {
  const chosen = document.documentElement.dataset.theme;
  if (chosen === "light" || chosen === "dark") return chosen;
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Private windows can refuse storage; the choice still holds for this page.
  }
  listeners.forEach((listener) => listener());
}

export function ThemeToggle() {
  const t = useTranslations("Theme");
  const theme = useSyncExternalStore(subscribe, currentTheme, () => null);
  const next: Theme = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      className="header-button icon-button"
      aria-label={theme === null ? t("toggle") : t(next === "dark" ? "toDark" : "toLight")}
      onClick={() => applyTheme(next)}
    >
      <svg className="theme-icon" viewBox="0 0 24 24" aria-hidden="true">
        {theme === "dark" ? (
          <>
            <circle cx="12" cy="12" r="4.5" />
            <path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8" />
          </>
        ) : (
          <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />
        )}
      </svg>
    </button>
  );
}
