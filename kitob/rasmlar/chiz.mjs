// HTML → PNG: salom.png (/start rasmi) va avatar.png (bot profil rasmi).
// Ishlatish: kitob/rasmlar ichida `node chiz.mjs` (playwright kerak).
import { chromium } from "playwright";
import { fileURLToPath } from "url";
import path from "path";
const dir = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
for (const [nom, w, h] of [["salom", 1280, 720], ["avatar", 640, 640]]) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.goto("file://" + path.join(dir, nom + ".html"));
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(dir, nom + ".png") });
  await page.close();
}
await browser.close();
