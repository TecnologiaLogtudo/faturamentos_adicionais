const { test } = require("@playwright/test");
const { readConfig, getInputFilePath, readSpreadsheet, mapRow } = require("./helpers");

async function login(page, config) {
  const loginUrl =
    "https://logtudo.e-login.net/?message_collection_id=msg_collection_69654311370983.91998362";
  await page.goto(loginUrl, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('input[name="usuario"]', { state: "visible" });
  await page.fill('input[name="usuario"]', config.username);
  await page.fill('input[name="senha"]', config.password);
  await page.press('input[name="senha"]', "Enter");
  await page.waitForLoadState("networkidle");
}

async function expandFilterIfClosed(page) {
  const isClosed = await page.evaluate(() => {
    const filterDiv = document.querySelector("div.rg-busca-rapida");
    return filterDiv && filterDiv.classList.contains("rg-busca-rapida-close");
  });
  if (isClosed) {
    const selectors = [
      "i.fa-chevron-up",
      'i[class*="chevron"]',
      ".expand-btn",
      '[class*="expand"]',
      "div.rg-busca-rapida",
    ];
    for (const sel of selectors) {
      if (await page.locator(sel).count()) {
        await page.locator(sel).first().click({ force: true });
        await page.waitForTimeout(500);
        break;
      }
    }
  }
}

async function searchNotaFiscal(page, notaFiscal) {
  await expandFilterIfClosed(page);
  await page.waitForSelector('input[name="busca_nDoc"]', { state: "visible" });
  const nfInput = page.locator('input[name="busca_nDoc"]');
  await nfInput.fill("");
  await nfInput.fill(notaFiscal);
  const filterBtn = page.locator('input[type="submit"][value="Filtrar"]');
  if (await filterBtn.count()) {
    await filterBtn.first().click({ force: true });
  } else {
    await page.evaluate(() => {
      const btn = document.querySelector('input[value="Filtrar"]');
      if (btn) btn.click();
    });
  }
  await page.waitForLoadState("networkidle");
}

async function waitForResultRow(page) {
  await page.waitForSelector("tbody tr", { state: "visible", timeout: 15000 });
}

test("fluxo nota fiscal", async ({ page }) => {
  const config = readConfig();
  const filePath = getInputFilePath();
  const spreadsheet = readSpreadsheet(filePath);
  const mapping = config.column_mapping || {};

  const firstRow = spreadsheet.rows.find((row) => {
    const mapped = mapRow(row, mapping);
    return mapped.nota_fiscal;
  });

  if (!firstRow) {
    test.skip(true, "Nenhuma linha valida na planilha");
  }

  const rowData = mapRow(firstRow, mapping);

  await login(page, config);
  await searchNotaFiscal(page, rowData.nota_fiscal);
  await waitForResultRow(page);
});
