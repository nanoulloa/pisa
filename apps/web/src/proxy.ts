import createMiddleware from "next-intl/middleware";

import { routing } from "./i18n/routing";

// Picks the locale from the URL, a cookie or Accept-Language, and redirects `/` to it.
export default createMiddleware(routing);

export const config = {
  matcher: "/((?!api|_next|_vercel|.*\\..*).*)",
};
