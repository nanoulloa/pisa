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
  const label = theme === null ? t("toggle") : t(next === "dark" ? "toDark" : "toLight");

  return (
    <button
      type="button"
      className="pill-button"
      aria-label={label}
      title={label}
      onClick={() => applyTheme(next)}
    >
      {/* Sun and moon after Lucide's icons (ISC license). */}
      <svg className="pill-icon" viewBox="0 0 24 24" aria-hidden="true">
        {theme === "dark" ? (
          <>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
          </>
        ) : (
          <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
        )}
      </svg>
    </button>
  );
}
