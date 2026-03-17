const { test, expect } = require("@playwright/test");
const {
  readConfig,
  getInputFilePath,
  readSpreadsheet,
  readKnownErrors,
  mapRow,
} = require("./helpers");

const LOGIN_URL =
  "https://logtudo.e-login.net/?message_collection_id=msg_collection_69654311370983.91998362";
const CONHECIMENTOS_URL =
  "https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=trans_conhecimento&menu=s";
const COTACOES_URL =
  "https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=transp_cotacoesFrete&menu=s";

function getDelays(config) {
  return {
    step: parseInt(config.step_delay || 1500, 10),
    network: parseInt(config.network_delay || 3000, 10),
    interaction: parseInt(config.interaction_delay || 500, 10),
    typing: parseInt(config.typing_delay || 75, 10),
  };
}

async function delay(page, ms) {
  await page.waitForTimeout(Math.max(0, ms));
}

async function login(page, config) {
  await page.goto(LOGIN_URL, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('input[name="usuario"]', { state: "visible" });
  await page.fill('input[name="usuario"]', config.username);
  await page.fill('input[name="senha"]', config.password);
  await page.press('input[name="senha"]', "Enter");
  await page.waitForLoadState("networkidle");
  await page.goto(CONHECIMENTOS_URL, { waitUntil: "networkidle" });
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

async function expandFilterAndSearch(page, notaFiscal, delays) {
  try {
    await page.waitForLoadState("networkidle", { timeout: 8000 });
  } catch {}

  await delay(page, delays.interaction);
  await expandFilterIfClosed(page);
  await delay(page, delays.interaction * 2);

  const inputSelector = 'input[name="busca_nDoc"]';
  await page.waitForSelector(inputSelector, { state: "visible", timeout: 5000 });
  const nfInput = page.locator(inputSelector);
  await nfInput.fill("");
  await delay(page, Math.floor(delays.interaction / 2));
  await nfInput.fill(notaFiscal);
  await delay(page, delays.interaction * 2);

  const filterSelector = 'input[type="submit"][value="Filtrar"]';
  try {
    const filterBtn = await page.waitForSelector(filterSelector, {
      state: "visible",
      timeout: 5000,
    });
    await filterBtn.click({ force: true });
  } catch {
    await page.evaluate(() => {
      const btn = document.querySelector('input[value="Filtrar"]');
      if (btn) btn.click();
    });
  }
  await delay(page, delays.network);
}

async function waitForResultsAndGetCte(page) {
  await page.waitForSelector("tbody tr", { state: "visible", timeout: 15000 });
  const result = await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("tbody tr"));
    let targetRow = null;
    for (const row of rows) {
      if (row.classList.contains("cabec")) continue;
      const noCell = row.querySelector('td[swni="no"]');
      if (noCell) {
        const text = noCell.textContent.trim();
        if (text && text !== "N.º" && text !== "Nº") {
          targetRow = row;
          break;
        }
      }
    }
    if (!targetRow) {
      if (rows.length > 1) targetRow = rows[1];
      else if (rows.length === 1) targetRow = rows[0];
      else return { error: "Nenhuma linha de dados valida encontrada" };
    }
    const noCellElement = targetRow.querySelector('td[swni="no"]');
    const cteNumber = noCellElement ? noCellElement.textContent.trim() : null;
    const checkboxElement = targetRow.querySelector(
      'input[type="checkbox"][name="id"]'
    );
    const checkboxId = checkboxElement ? checkboxElement.value : null;
    return { cteNumber, checkboxId, error: null };
  });

  if (result.error) {
    throw new Error(result.error);
  }
  if (!result.cteNumber) {
    throw new Error("Nao foi possivel encontrar numero CT-e na linha");
  }
  if (["N.º", "Nº", "No", "Numero"].includes(result.cteNumber)) {
    throw new Error(`Valor extraido parece cabecalho: ${result.cteNumber}`);
  }
  if (!result.checkboxId) {
    throw new Error("Nao foi possivel encontrar ID do checkbox");
  }
  return { number: result.cteNumber, id: result.checkboxId };
}

async function clickAdicionar(page, delays) {
  await delay(page, delays.interaction);
  const selector = '#_boop img[title="Adicionar"]';
  try {
    await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
    await page.click(selector, { force: true });
  } catch {
    await page.click("#_boop > a", { force: true });
  }
  await delay(page, delays.interaction * 3);
}

async function selectPreenchimentoManual(page, delays) {
  try {
    await page.waitForLoadState("networkidle", { timeout: 8000 });
  } catch {}
  await delay(page, delays.interaction * 2);
  const selector = 'span:has-text("Preenchimento Manual")';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.click(selector, { force: true });
  await delay(page, delays.network);
}

async function selectAgencia(page, uf, delays) {
  const ufMap = {
    PE: "PERNAMBUCO",
    CE: "CEARÁ",
    BA: "BAHIA",
    SP: "SÃO PAULO",
    RJ: "RIO DE JANEIRO",
    MG: "MINAS GERAIS",
    RS: "RIO GRANDE DO SUL",
    PR: "PARANÁ",
    SC: "SANTA CATARINA",
    GO: "GOIÁS",
    MT: "MATO GROSSO",
    MS: "MATO GROSSO DO SUL",
    DF: "DISTRITO FEDERAL",
    ES: "ESPÍRITO SANTO",
    AM: "AMAZONAS",
    PA: "PARÁ",
    MA: "MARANHÃO",
    PB: "PARAÍBA",
    RN: "RIO GRANDE DO NORTE",
    AL: "ALAGOAS",
    SE: "SERGIPE",
    PI: "PIAUÍ",
    TO: "TOCANTINS",
    RO: "RONDÔNIA",
    AC: "ACRE",
    RR: "RORAIMA",
    AP: "AMAPÁ",
  };
  const ufClean = String(uf || "").trim().toUpperCase();
  const targetUf = ufMap[ufClean] || ufClean;

  await delay(page, delays.interaction * 1.5);
  const selector = 'select[name="dados_agencias_id"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  try {
    await page.click(selector, { force: true });
    await delay(page, delays.interaction);
  } catch {}

  const optionValue = await page.evaluate((target) => {
    const select = document.querySelector('select[name="dados_agencias_id"]');
    if (!select) return null;
    const options = Array.from(select.options);
    const opt = options.find((o) => {
      const text = o.text.trim().toUpperCase();
      const search = target.toUpperCase();
      return text.endsWith(search) || text.includes(search);
    });
    return opt ? opt.value : null;
  }, targetUf);

  if (optionValue) {
    await page.selectOption(selector, optionValue);
  } else {
    try {
      await page.selectOption(selector, { label: targetUf });
    } catch {
      await page.selectOption(selector, { label: ufClean });
    }
  }
  await delay(page, delays.interaction * 1.5);
}

async function selectTalao(page, delays) {
  await delay(page, delays.interaction * 1.5);
  const selector = 'select[name="dados_tiposTaloes_id"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  try {
    await page.click(selector, { force: true });
    await delay(page, delays.interaction);
  } catch {}
  const optionValue = await page.evaluate(() => {
    const select = document.querySelector('select[name="dados_tiposTaloes_id"]');
    if (!select) return null;
    const options = Array.from(select.options);
    const opt = options.find((o) => o.text.trim().startsWith("CT-e"));
    return opt ? opt.value : null;
  });
  if (!optionValue) {
    throw new Error("Nenhum Talao iniciado com CT-e encontrado");
  }
  await page.selectOption(selector, optionValue);
  await delay(page, delays.interaction * 1.5);
}

async function fillIdentificacaoPedido(page, tipoAdc, delays) {
  let valor = "";
  const tipoLower = String(tipoAdc || "").toLowerCase();
  if (tipoLower.startsWith("descarga")) valor = "Descarga";
  else if (tipoLower.startsWith("pedagio")) valor = "Pedagio";
  else valor = tipoAdc || "";

  const selector = 'input[name="dados_complementoPedido"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.fill(selector, "");
  await delay(page, Math.floor(delays.interaction / 2));
  await page.locator(selector).type(valor, { delay: delays.typing });
  await delay(page, delays.interaction * 1.5);
}

async function fillIdentificacaoCustom(page, valor, delays) {
  const selector = 'input[name="dados_complementoPedido"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.fill(selector, "");
  await delay(page, Math.floor(delays.interaction / 2));
  await page.locator(selector).type(valor, { delay: delays.typing });
  await delay(page, delays.interaction * 1.5);
}

async function selectTipoCteComplemento(page, delays) {
  await delay(page, delays.interaction * 1.5);
  const selector = 'select[name="dados_tpCTe"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  try {
    await page.click(selector, { force: true });
    await delay(page, delays.interaction);
  } catch {}
  await page.selectOption(selector, "1");
  await delay(page, delays.interaction * 1.5);
}

async function pesquisarCteComplementar(page, cteNumber, delays) {
  await delay(page, delays.interaction * 1.5);
  const selectorInput = 'input[name="pesquisa_complementou_id"]';
  await page.waitForSelector(selectorInput, { state: "visible", timeout: 5000 });
  await page.locator(selectorInput).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.fill(selectorInput, "");
  await delay(page, Math.floor(delays.interaction / 2));
  await page.locator(selectorInput).type(cteNumber, { delay: delays.typing });
  await delay(page, delays.interaction * 2);
  const selectorBtn = 'i[name="botaoPesquisa_complementou_id"]';
  try {
    const locator = page.locator(selectorBtn);
    await locator.waitFor({ state: "visible", timeout: 5000 });
    await locator.scrollIntoViewIfNeeded();
    await delay(page, delays.interaction);
    await locator.click({ force: true, timeout: 3000 });
  } catch {
    await page.evaluate((sel) => {
      const btn = document.querySelector(sel);
      if (btn) btn.click();
    }, selectorBtn);
  }
  await delay(page, delays.network);
}

async function checkEmitirNotaFiscal(page, delays) {
  const selector = 'input[name="dados_emitirReciboFrete[]"][value="S"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  if (!(await page.isChecked(selector))) {
    await page.click(selector, { force: true });
  }
  await delay(page, delays.interaction);
}

async function runCotacoesTask(context, senhaRavex, delays) {
  const page = await context.newPage();
  let cotacaoNumero = null;
  let cotacaoData = null;
  try {
    await page.goto(COTACOES_URL, { waitUntil: "domcontentloaded" });
    try {
      const expandBtn = await page.waitForSelector("i.fa-chevron-up, .expand-btn", {
        timeout: 5000,
      });
      if (expandBtn) {
        await expandBtn.click();
        await delay(page, delays.interaction);
      }
    } catch {}

    const selectsToClear = [
      "busca_cliente",
      "busca_agencia",
      "busca_status",
      "busca_possuiConhecimento",
      "busca_possuiOC",
      "busca_minhasCotacoes",
    ];
    for (const name of selectsToClear) {
      try {
        const sel = page.locator(`select[name="${name}"]`);
        if (await sel.isVisible()) {
          await sel.selectOption("");
        }
      } catch {}
    }
    const inputsToClear = [
      "pesquisa_busca_cliente",
      "busca_nro",
      "busca_contatos",
    ];
    for (const name of inputsToClear) {
      try {
        const inp = page.locator(`input[name="${name}"]`);
        if (await inp.isVisible()) {
          await inp.fill("");
        }
      } catch {}
    }

    await delay(page, delays.interaction);
    try {
      await page.fill('input[name="busca_nro"]', String(senhaRavex || ""));
    } catch {}

    await delay(page, delays.interaction);
    try {
      await page.click('input[value="Filtrar"]', { force: true });
      await delay(page, delays.interaction * 2);
    } catch {}

    try {
      await page.waitForSelector('td[swni="no_cliente"]', {
        state: "visible",
        timeout: 10000,
      });
      cotacaoNumero = await page.evaluate(() => {
        const cells = Array.from(document.querySelectorAll('td[swni="no_cliente"]'));
        for (const cell of cells) {
          const text = cell.textContent.trim();
          if (text && /^\d+$/.test(text)) {
            return text;
          }
        }
        return null;
      });
      cotacaoData = await page.evaluate(() => {
        const cells = Array.from(document.querySelectorAll('td[swni="emissao"]'));
        for (const cell of cells) {
          const text = cell.textContent.trim();
          if (
            text &&
            text.toLowerCase() !== "emissão" &&
            text.toLowerCase() !== "emissao"
          ) {
            return text;
          }
        }
        return null;
      });
    } catch {}
  } finally {
    await page.close();
  }
  return { cotacaoNumero, cotacaoData };
}

async function preencherCotacaoEPesquisar(page, cotacaoNumero, delays) {
  if (!cotacaoNumero) return;
  await page.bringToFront();
  const selectorInput = 'input[name="pesquisa_pedidos_id"]';
  await page.waitForSelector(selectorInput, { state: "visible", timeout: 5000 });
  await page.locator(selectorInput).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.fill(selectorInput, "");
  await delay(page, Math.floor(delays.interaction / 2));
  await page.locator(selectorInput).type(cotacaoNumero, { delay: delays.typing });
  await delay(page, delays.interaction);
  const selectorBtn = 'i[name="botaoPesquisa_pedidos_id"]';
  await page.waitForSelector(selectorBtn, { state: "visible", timeout: 5000 });
  await page.click(selectorBtn, { force: true });
  await delay(page, delays.network);
}

async function avancarPagina(page, delays) {
  await delay(page, delays.interaction * 1.5);
  let selector = 'input[name="botao_finalizacao"][value="Avançar »"]';
  if (!(await page.isVisible(selector))) {
    selector = 'input[name="botao_finalizacao"][value*="Avançar"]';
  }
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.click(selector, { force: true });
  await page.waitForLoadState("networkidle", { timeout: 10000 });
  await delay(page, delays.network);
}

async function clickPesquisarNatureza(page, delays) {
  await delay(page, delays.interaction * 1.5);
  const selector = 'i[name="botaoPesquisa_cfops_id"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.click(selector, { force: true });
  await delay(page, delays.network);
}

async function preencherFreteValor(page, valor, delays) {
  await delay(page, delays.interaction * 1.5);
  const selector = 'input[name="dados_valorFrete"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.fill(selector, "");
  await delay(page, Math.floor(delays.interaction / 2));
  const formatado = String(valor || "").replace(".", ",");
  await page.locator(selector).type(formatado, { delay: delays.typing });
  await delay(page, delays.interaction * 1.5);
}

async function preencherSenhaRavex(page, senha, delays) {
  await delay(page, delays.interaction * 1.5);
  const selector = 'input[name="dados_tagsCTe[ravex]"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.fill(selector, "");
  await delay(page, Math.floor(delays.interaction / 2));
  await page.locator(selector).type(String(senha || ""), { delay: delays.typing });
  await delay(page, delays.interaction * 1.5);
}

async function preencherObservacaoConhecimento(
  page,
  tipoAdc,
  notaFiscal,
  senhaRavex,
  transporte,
  delays
) {
  await delay(page, delays.interaction * 1.5);
  const selector = 'textarea[name="dados_observacaoConhecimento"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  const observacao = `Referente ${tipoAdc} NF ${notaFiscal}\nSenha ${senhaRavex}\nTransporte ${transporte}`;
  await page.fill(selector, "");
  await delay(page, Math.floor(delays.interaction / 2));
  await page.locator(selector).type(observacao, { delay: delays.typing });
  await delay(page, delays.interaction * 1.5);
}

async function salvarFormulario(page, delays) {
  await delay(page, delays.interaction * 1.5);
  const selector = 'input[name="botao_finalizacao"][value="Salvar"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.click(selector, { force: true });
  await delay(page, delays.network);
  try {
    await page.waitForLoadState("networkidle", { timeout: 10000 });
  } catch {}
}

async function preencherTabelaFrete(page, delays) {
  const selector = 'select[name="dados_freteMinimo_tabela"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.selectOption(selector, "A");
  await delay(page, delays.interaction);
}

async function preencherTipoCarga(page, delays) {
  const selector = 'select[name="dados_freteMinimo_tipoCarga"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.selectOption(selector, "FRI");
  await delay(page, delays.interaction);
}

async function aplicarTratativaTipoCarga(page, delays, value) {
  const selector = 'select[name="dados_freteMinimo_tipoCarga"]';
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.selectOption(selector, value);
  await delay(page, delays.interaction);
}

function matchesKnownError(errorMessage, knownErrors) {
  if (!errorMessage) return null;
  const normalized = String(errorMessage);
  for (const [key, data] of Object.entries(knownErrors)) {
    const patterns = data.match_any || [];
    if (patterns.some((p) => normalized.includes(p))) {
      return { key, data };
    }
  }
  return null;
}

async function executeTreatment(page, delays, treatment) {
  const steps = treatment?.steps || [];
  for (const step of steps) {
    if (step.action === "select_tipo_carga") {
      await aplicarTratativaTipoCarga(page, delays, step.value);
      continue;
    }
    throw new Error(`Tratativa nao suportada: ${step.action}`);
  }
}

async function clicarAvancarFinal(page, delays) {
  await delay(page, delays.interaction * 1.5);
  let selector = 'input[name="botao_finalizacao"][value="Avançar »"]';
  if (!(await page.isVisible(selector))) {
    selector = 'input[name="botao_finalizacao"][value*="Avançar"]';
  }
  await page.waitForSelector(selector, { state: "visible", timeout: 5000 });
  await page.locator(selector).scrollIntoViewIfNeeded();
  await delay(page, delays.interaction);
  await page.click(selector, { force: true });
  await page.waitForLoadState("networkidle", { timeout: 10000 });
  await delay(page, delays.network);
}

async function handleOkPopup(page, delays) {
  const selector = 'span.ui-button-text:has-text("OK")';
  try {
    const locator = page.locator(selector);
    await locator.waitFor({ state: "visible", timeout: 5000 });
    await locator.click();
    await delay(page, delays.network);
  } catch {}
}

async function preencherContratoFrete(page, data, cotacaoData, delays) {
  await handleOkPopup(page, delays);
  await delay(page, delays.interaction * 2);

  await page.fill('input[name="pesquisa_dados_perfisApropriacao_id"]', "Lac");
  await page.click('i[name="botaoPesquisa_dados_perfisApropriacao_id"]');
  await delay(page, delays.interaction * 2);

  const dtEmissao = await page.inputValue('input[name="dados_dtEmissaoRF"]');
  await page.fill('input[name="dados_dtFimViagem"]', dtEmissao);

  await page.fill('input[name="dados_kms"]', "1");

  await page.fill('input[name="pesquisa_dados_ncm"]', "0403");
  await page.click('i[name="botaoPesquisa_dados_ncm"]');
  await delay(page, delays.interaction * 2);

  await page.click('select[name="dados_regrasCarreto_id"]');
  await delay(page, delays.interaction);
  await page.evaluate(() => {
    const select = document.querySelector('select[name="dados_regrasCarreto_id"]');
    if (!select) return;
    const options = Array.from(select.options);
    const opt = options.find((o) => o.text.includes("Regra terceiros"));
    if (opt) {
      select.value = opt.value;
      select.dispatchEvent(new Event("change"));
    }
  });
  await delay(page, delays.interaction);

  const obsAnterior = `Referente ${data.tipo_adc} NF ${data.nota_fiscal}\nSenha ${data.senha_ravex}\nTransporte ${data.transporte}`;
  const validade = cotacaoData || "N/A";
  const novaObs = `${obsAnterior}\nData da validade ${validade}`;
  await page.fill('textarea[name="dados_obs"]', novaObs);

  const cartaoVal = await page.inputValue(
    'input[name="dados_nroCartaoOperadoraCredito"]'
  );
  if (!cartaoVal.trim()) {
    await page.fill('input[name="dados_nroCartaoOperadoraCredito"]', "0");
  }

  await page.selectOption('select[name="dados_operacaoRepom"]', "1");
  await page.selectOption('select[name="dados_tipoSaldoRepom"]', "P");
  await delay(page, delays.interaction * 2);

  if (cotacaoData) {
    try {
      const [d, m, y] = cotacaoData.split("/").map((v) => parseInt(v, 10));
      let nextMonth = m + 1;
      let year = y;
      if (nextMonth > 12) {
        nextMonth = 1;
        year += 1;
      }
      const dtStr = String(d).padStart(2, "0") + "/" +
        String(nextMonth).padStart(2, "0") + "/" + year;
      const dateSelector = 'input[name="dados_dataSaldoRepom"]';
      await page.waitForSelector(dateSelector, { state: "visible", timeout: 5000 });
      await page.fill(dateSelector, dtStr);
    } catch {}
  }

  await page.evaluate(() => {
    document
      .querySelectorAll("input.confirmacao_concorda")
      .forEach((c) => c.click());
  });

  const currentUrl = page.url();
  await page.click('input[value="Salvar"].swbotao_salvar');

  try {
    await page.waitForURL((url) => url !== currentUrl, { timeout: 15000 });
    await page.waitForLoadState("networkidle", { timeout: 10000 });
  } catch (err) {
    const freteSelector = 'input[name="dados_freteMinimo_valor"]';
    let freteValor = "";
    try {
      freteValor = await page.locator(freteSelector).inputValue({ timeout: 1000 });
    } catch {}
    if (!freteValor || ["", "0,00"].includes(freteValor.trim())) {
      const knownErrors = readKnownErrors();
      const message =
        "Erro ao salvar Contrato: Frete minimo vazio/zerado (cotacao nao aplicada)";
      const match = matchesKnownError(message, knownErrors);
      if (match && match.key === "frete_minimo_nao_preenchido") {
        await aplicarTratativaTipoCarga(page, delays, "");
        await aplicarTratativaTipoCarga(page, delays, "FRI");
        await page.click('input[value="Salvar"].swbotao_salvar');
        await page.waitForURL((url) => url !== currentUrl, { timeout: 15000 });
        await page.waitForLoadState("networkidle", { timeout: 10000 });
        return;
      }
      throw new Error(message);
    }
    throw err;
  }
}

async function processDescargaPedagio(page, data, cteNumber, delays) {
  await selectAgencia(page, data.uf, delays);
  await selectTalao(page, delays);
  await fillIdentificacaoPedido(page, data.tipo_adc, delays);
  await selectTipoCteComplemento(page, delays);
  await pesquisarCteComplementar(page, cteNumber, delays);
  await avancarPagina(page, delays);
  await clickPesquisarNatureza(page, delays);
  await preencherFreteValor(page, data.valor_cte, delays);
  await preencherSenhaRavex(page, data.senha_ravex, delays);
  await preencherObservacaoConhecimento(
    page,
    data.tipo_adc,
    data.nota_fiscal,
    data.senha_ravex,
    data.transporte,
    delays
  );
  await salvarFormulario(page, delays);
}

async function processPernoiteReentrega(page, data, cteNumber, delays) {
  await selectAgencia(page, data.uf, delays);
  await selectTalao(page, delays);
  let identificacao = "REENTREGA";
  if (String(data.tipo_adc || "").toLowerCase().startsWith("pernoite")) {
    identificacao = "DIARIA NO CLIENTE";
  }
  await fillIdentificacaoCustom(page, identificacao, delays);
  await selectTipoCteComplemento(page, delays);
  await pesquisarCteComplementar(page, cteNumber, delays);
  await checkEmitirNotaFiscal(page, delays);

  const { cotacaoNumero, cotacaoData } = await runCotacoesTask(
    page.context(),
    data.senha_ravex,
    delays
  );

  await preencherCotacaoEPesquisar(page, cotacaoNumero, delays);
  await avancarPagina(page, delays);
  await clickPesquisarNatureza(page, delays);
  await preencherTabelaFrete(page, delays);
  await preencherTipoCarga(page, delays);
  await preencherFreteValor(page, data.valor_cte, delays);
  await preencherSenhaRavex(page, data.senha_ravex, delays);
  await preencherObservacaoConhecimento(
    page,
    data.tipo_adc,
    data.nota_fiscal,
    data.senha_ravex,
    data.transporte,
    delays
  );
  await clicarAvancarFinal(page, delays);
  await preencherContratoFrete(page, data, cotacaoData, delays);
}

async function executeNotaFiscal(page, rowData, delays) {
  await expandFilterAndSearch(page, rowData.nota_fiscal, delays);
  const cteInfo = await waitForResultsAndGetCte(page);
  await clickAdicionar(page, delays);
  await selectPreenchimentoManual(page, delays);

  const tipoLower = String(rowData.tipo_adc || "").toLowerCase();
  if (tipoLower.startsWith("descarga") || tipoLower.startsWith("pedagio")) {
    await processDescargaPedagio(page, rowData, cteInfo.number, delays);
  } else if (tipoLower.startsWith("pernoite") || tipoLower.startsWith("reentrega")) {
    await processPernoiteReentrega(page, rowData, cteInfo.number, delays);
  } else {
    throw new Error(`Tipo ADC nao reconhecido: ${rowData.tipo_adc}`);
  }
}

async function recoverFromError(page, config) {
  const dropdown = page.locator("i.fas.fa-chevron-down.chevronicon");
  await dropdown.first().click({ timeout: 10000 });
  await page.waitForTimeout(1000);
  const logout = page.locator('p.regular-small-text:has-text("Sair")');
  await logout.first().click();
  await page.waitForSelector('input[name="usuario"]', { timeout: 60000 });
  await login(page, config);
}

test("pipeline completo", async ({ page }) => {
  test.setTimeout(30 * 60 * 1000);
  const config = readConfig();
  const knownErrors = readKnownErrors();
  const delays = getDelays(config);
  const filePath = getInputFilePath();
  const spreadsheet = readSpreadsheet(filePath);
  const mapping = config.column_mapping || {};

  await login(page, config);

  for (const row of spreadsheet.rows) {
    const rowData = mapRow(row, mapping);
    if (!rowData.nota_fiscal) continue;
    if (rowData.cte_output && rowData.cte_output.toLowerCase() !== "nan") {
      continue;
    }
    rowData.uf = config.uf;
    try {
      await executeNotaFiscal(page, rowData, delays);
    } catch (err) {
      const message = err?.message || String(err);
      const match = matchesKnownError(message, knownErrors);
      if (match && match.data?.treatment) {
        await executeTreatment(page, delays, match.data.treatment);
      } else {
        await recoverFromError(page, config);
      }
    }
  }
});
