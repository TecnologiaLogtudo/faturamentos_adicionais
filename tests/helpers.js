const fs = require("fs");
const path = require("path");
const xlsx = require("xlsx");

function readConfig() {
  const configPath = path.resolve(__dirname, "..", "config", "config.json");
  if (!fs.existsSync(configPath)) {
    throw new Error(`config.json nao encontrado em ${configPath}`);
  }
  return JSON.parse(fs.readFileSync(configPath, "utf-8"));
}

function getInputFilePath() {
  if (process.env.PLAYWRIGHT_INPUT_PATH) {
    return process.env.PLAYWRIGHT_INPUT_PATH;
  }
  const uploadsDir = path.resolve(__dirname, "..", "webapp", "uploads");
  if (!fs.existsSync(uploadsDir)) {
    throw new Error("Pasta webapp/uploads nao encontrada");
  }
  const files = fs
    .readdirSync(uploadsDir)
    .filter((f) => f.endsWith(".xlsx") || f.endsWith(".xls") || f.endsWith(".csv"))
    .map((f) => ({
      name: f,
      full: path.join(uploadsDir, f),
      mtime: fs.statSync(path.join(uploadsDir, f)).mtimeMs,
    }))
    .sort((a, b) => b.mtime - a.mtime);
  if (!files.length) {
    throw new Error("Nenhuma planilha encontrada em webapp/uploads");
  }
  return files[0].full;
}

function readSpreadsheet(filePath) {
  const workbook = xlsx.readFile(filePath);
  const sheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[sheetName];
  const rows = xlsx.utils.sheet_to_json(sheet, { header: 1, raw: false });
  const headers = rows.shift() || [];
  return { headers, rows };
}

function readKnownErrors() {
  const errorsPath = path.resolve(__dirname, "known-errors.json");
  if (!fs.existsSync(errorsPath)) {
    throw new Error(`known-errors.json nao encontrado em ${errorsPath}`);
  }
  return JSON.parse(fs.readFileSync(errorsPath, "utf-8"));
}

function mapRow(row, mapping) {
  const get = (key) => {
    const idx = mapping[key];
    if (idx === undefined || idx === null) return "";
    return row[idx] ?? "";
  };
  return {
    nota_fiscal: String(get("nota_fiscal")).trim(),
    tipo_adc: String(get("tipo_adc")).trim(),
    valor_cte: String(get("valor_cte")).trim(),
    senha_ravex: String(get("senha_ravex")).trim(),
    transporte: String(get("transporte")).trim(),
    cte_output: String(get("cte_output")).trim(),
  };
}

module.exports = {
  readConfig,
  getInputFilePath,
  readSpreadsheet,
  readKnownErrors,
  mapRow,
};
