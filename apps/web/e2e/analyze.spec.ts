import { expect, type Page, test } from "@playwright/test";
import { join } from "node:path";

import { CLIPS_DIR } from "./global-setup";

async function check(page: Page, locale: string, clip: string, labels: { file: string; submit: string }) {
  await page.goto(`/${locale}/check`);
  await page.getByLabel(labels.file).setInputFiles(join(CLIPS_DIR, `${clip}.mp4`));
  await page.getByRole("button", { name: labels.submit }).click();
  await expect(page).toHaveURL(new RegExp(`/${locale}/result/[0-9a-f-]{36}$`));
}

const english = { file: "Choose a video", submit: "Check this video" };

test("a real fall is consistent with real physics, in Spanish", async ({ page }) => {
  await check(page, "es", "free_fall", { file: "Elige un video", submit: "Revisar este video" });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Consistente con la física real");
  await expect(page.getByText("Esto no prueba que el video sea real.")).toBeVisible();
  await expect(page.getByText("Constante", { exact: true })).toBeVisible();
});

test("eased motion is physically impossible", async ({ page }) => {
  await check(page, "en", "eased", english);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Physically impossible");
  await expect(page.getByText("The object slows down while it is still falling.")).toBeVisible();
  await page.getByText("Technical details").click();
  await expect(page.getByText("T1 Free-fall shape · violation")).toBeVisible();
});

test("constant speed is inconclusive, and says why", async ({ page }) => {
  await check(page, "en", "constant_velocity", english);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Inconclusive");
  await expect(page.getByText("The object moves at a steady speed")).toBeVisible();
});

test("a file that is not a video gets a clear error", async ({ page }) => {
  await page.goto("/en/check");
  await page.getByLabel(english.file).setInputFiles({
    name: "notes.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("not a video"),
  });
  await page.getByRole("button", { name: english.submit }).click();
  await expect(page).toHaveURL(/\/en\/result\//);
  await expect(page.getByText("This file isn't a video Pisa can read. Try an MP4 or MOV.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Try another video" })).toBeVisible();
});
