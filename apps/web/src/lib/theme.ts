export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "pisa-theme";

/**
 * Runs in <head> before the first paint, so a saved choice never flashes the other theme.
 * Without a saved choice nothing is set and the system preference applies.
 */
export const THEME_SCRIPT = `try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;
