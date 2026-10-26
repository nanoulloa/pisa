import { expect, test } from "@playwright/test";

test("the root redirects to the visitor's language and leads to the check page", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/en$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "AI can fake pixels. It can't fake physics.",
  );

  await page.getByRole("link", { name: "Check a video" }).click();
  await expect(page).toHaveURL(/\/en\/check$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check a video");
});

test("the language switcher keeps the page and translates it", async ({ page }) => {
  await page.goto("/en/check");
  await page.getByRole("button", { name: "Language: English" }).click();
  await page.getByRole("link", { name: "Español" }).click();
  await expect(page).toHaveURL(/\/es\/check$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Revisar un video");
});

test("Chinese renders the agreed verdict terms", async ({ page }) => {
  await page.goto("/zh-CN");
  await expect(page.getByRole("heading", { name: "物理上不可能" })).toBeVisible();
  await expect(page.getByRole("link", { name: "检查视频" })).toBeVisible();
});

test("the theme toggle switches themes and remembers the choice", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/en");
  await expect(page.locator("html")).not.toHaveAttribute("data-theme", /./);
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByRole("button", { name: "Switch to light theme" })).toBeVisible();
});

test("the header shows the mark and links home", async ({ page }) => {
  await page.goto("/es/check");
  await page.getByRole("link", { name: "Pisa, inicio" }).click();
  await expect(page).toHaveURL(/\/es$/);
});
