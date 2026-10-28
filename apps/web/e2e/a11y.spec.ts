import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";
import { join } from "node:path";

import { CLIPS_DIR } from "./global-setup";

const WCAG_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const VERDICT = /^(Physically impossible|Consistent with real physics|Inconclusive)$/;

/** Every rule of WCAG 2.2 AA that axe can check, with every disclosure open. */
async function expectAccessible(page: Page) {
  await page.evaluate(() => {
    for (const details of document.querySelectorAll("details")) details.open = true;
  });
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_AA).analyze();
  const found = violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(" | ")}`);
  expect(found).toEqual([]);
}

for (const colorScheme of ["light", "dark"] as const) {
  test.describe(`in the ${colorScheme} theme`, () => {
    test.use({ colorScheme });

    for (const path of ["/en", "/en/check", "/en/how-we-know", "/en/privacy", "/zh-CN", "/es/check"]) {
      test(`${path} passes WCAG 2.2 AA checks`, async ({ page }) => {
        await page.goto(path);
        await expectAccessible(page);
      });
    }

    for (const clip of ["eased", "free_fall", "constant_velocity"]) {
      test(`the result for ${clip} passes WCAG 2.2 AA checks`, async ({ page }) => {
        await page.goto("/en/check");
        await page.getByLabel("Choose a video").setInputFiles(join(CLIPS_DIR, `${clip}.mp4`));
        await page.getByRole("button", { name: "Check this video" }).click();
        await expect(page.getByRole("heading", { level: 1 })).toHaveText(VERDICT);
        await expectAccessible(page);
      });
    }

    test("an error passes WCAG 2.2 AA checks", async ({ page }) => {
      await page.goto("/en/check");
      await page.getByLabel("Choose a video").setInputFiles({
        name: "notes.mp4",
        mimeType: "video/mp4",
        buffer: Buffer.from("not a video"),
      });
      await page.getByRole("button", { name: "Check this video" }).click();
      await expect(page.getByText("This file isn't a video Pisa can read.", { exact: false })).toBeVisible();
      await expectAccessible(page);
    });
  });
}

test("the check page works from the keyboard alone, with a visible focus ring", async ({ page }) => {
  await page.goto("/en/check");
  const reached: string[] = [];
  for (let step = 0; step < 15; step += 1) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const element = document.activeElement as HTMLElement | null;
      if (!element || element === document.body) return null;
      const style = getComputedStyle(element);
      return {
        name: element.getAttribute("aria-label") ?? element.textContent?.trim() ?? element.tagName,
        tag: element.tagName,
        type: element.getAttribute("type"),
        ring: style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) >= 2,
      };
    });
    if (!focused) continue;
    expect(focused.ring, `focus ring on ${focused.name}`).toBe(true);
    reached.push(focused.type === "file" ? "file input" : focused.name);
  }
  expect(reached).toContain("file input");
});

test("the evidence video has a name and captions in the page's language", async ({ page }) => {
  await page.goto("/es/check");
  await page.getByLabel("Elige un video").setInputFiles(join(CLIPS_DIR, "bounce.mp4"));
  await page.getByRole("button", { name: "Revisar este video" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Consistente con la física real");
  await expect(page.locator("video")).toHaveAttribute("aria-label", "Video de evidencia");
  const track = page.locator("video track");
  await expect(track).toHaveAttribute("kind", "captions");
  await expect(track).toHaveAttribute("srclang", "es");
  const captions = await page.request.get(new URL((await track.getAttribute("src")) ?? "", page.url()).href);
  expect(captions.headers()["content-type"]).toContain("text/vtt");
  const vtt = await captions.text();
  expect(vtt.startsWith("WEBVTT")).toBe(true);
  expect(vtt).toContain("El anillo marca el objeto que siguió Pisa.");
  expect(vtt).toContain("El fantasma sigue el camino más cercano que permite la gravedad real.");
  expect(vtt).toContain("Veredicto de Pisa: Consistente con la física real.");
});
