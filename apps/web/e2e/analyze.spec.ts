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
  await expect(page.getByText("What Pisa watched")).toBeVisible();
  await expect(page.getByText("Fall, from 0 s to 0.75 s: ball")).toBeVisible();
});

test("constant speed is inconclusive, and says why", async ({ page }) => {
  await check(page, "en", "constant_velocity", english);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Inconclusive");
  await expect(page.getByText("The object moves at a steady speed")).toBeVisible();
});

test("a real bounce keeps less than all of its speed, in Portuguese", async ({ page }) => {
  await check(page, "pt-BR", "bounce", { file: "Escolha um vídeo", submit: "Verificar este vídeo" });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Consistente com a física real");
  await expect(page.getByText("Velocidade depois do quique")).toBeVisible();
  await expect(page.getByText("70%", { exact: true })).toBeVisible();
});

test("two balls that fall apart give the fake away", async ({ page }) => {
  await check(page, "en", "pair_falls_apart", english);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Physically impossible");
  await expect(page.getByText("Two objects released together fall at different rates.")).toBeVisible();
  await expect(page.getByText("1.64×", { exact: true })).toBeVisible();

  // The evidence video is served, with a legend that does not rely on color.
  const video = page.locator("video");
  await expect(video).toBeVisible();
  const source = await video.getAttribute("src");
  expect(source).toMatch(/\/jobs\/[0-9a-f-]{36}\/evidence\.mp4$/);
  const evidence = await page.request.get(source ?? "");
  expect(evidence.headers()["content-type"]).toBe("video/mp4");
  await expect(page.getByText("Where it would be if both fell together").first()).toBeVisible();
  await expect(page.getByText("Played at half speed.")).toBeVisible();

  // The share card and the link preview are images made from the result.
  await expect(page.getByRole("button", { name: "Share" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Send on WhatsApp" })).toHaveAttribute("href", /^https:\/\/wa\.me\//);
  const card = await page.request.get(`${page.url()}/card`);
  expect(card.headers()["content-type"]).toBe("image/png");
  const preview = page.locator('meta[property="og:image"]');
  const previewUrl = await preview.getAttribute("content");
  expect((await page.request.get(previewUrl ?? "")).headers()["content-type"]).toBe("image/png");
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
