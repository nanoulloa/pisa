import { defineConfig, devices } from "@playwright/test";
import { join } from "node:path";

const webPort = 3100;
const enginePort = 8100;
const repoRoot = join(__dirname, "../..");

/**
 * Runs the real engine (with the free color segmenter, never a paid API) next to the built
 * web app. Build the web app with NEXT_PUBLIC_ENGINE_URL=http://localhost:8100 first:
 * `make e2e` does both.
 */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://localhost:${webPort}`,
    locale: "en-US",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run uvicorn pisa_engine.api:app --port ${enginePort}`,
      cwd: repoRoot,
      url: `http://localhost:${enginePort}/healthz`,
      reuseExistingServer: !process.env.CI,
      env: {
        PISA_SEGMENTER: "fake",
        PISA_PAID_CALLS_ENABLED: "false",
        PISA_DATA_DIR: join(__dirname, "e2e/.data"),
        SUPABASE_URL: "", // Local files only, even when a developer's .env points at Supabase.
        PISA_WEB_ORIGINS: `http://localhost:${webPort}`,
      },
    },
    {
      command: `npm run start -- --port ${webPort}`,
      url: `http://localhost:${webPort}/en`,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
