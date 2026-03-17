const { test } = require("@playwright/test");
const { readConfig } = require("./helpers");

test("fluxo de login", async ({ page }) => {
  const config = readConfig();
  const loginUrl =
    "https://logtudo.e-login.net/?message_collection_id=msg_collection_69654311370983.91998362";

  await page.goto(loginUrl, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('input[name="usuario"]', { state: "visible" });
  await page.fill('input[name="usuario"]', config.username);
  await page.fill('input[name="senha"]', config.password);

  const submit = page.locator('input[type="submit"], button[type="submit"]');
  if (await submit.count()) {
    await submit.first().click();
  } else {
    await page.press('input[name="senha"]', "Enter");
  }

  await page.waitForLoadState("networkidle");
});
