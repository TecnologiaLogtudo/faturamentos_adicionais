const state = {
  fileId: null,
  jobId: null,
  headers: [],
  logs: [],
  results: [],
  autoScroll: true,
  logFilter: "ALL",
};

const el = (id) => document.getElementById(id);

const navButtons = document.querySelectorAll(".nav-btn");
const views = {
  processamento: el("view-processamento"),
  configuracoes: el("view-configuracoes"),
  resultados: el("view-resultados"),
};

navButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    navButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    Object.values(views).forEach((v) => v.classList.remove("active"));
    views[btn.dataset.view].classList.add("active");
  });
});

function loadSettings() {
  const raw = localStorage.getItem("logtudo_settings");
  const data = raw ? JSON.parse(raw) : {};
  el("cfgUser").value = data.username || "";
  el("cfgPass").value = data.password || "";
  el("cfgUf").value = data.uf || "Bahia";
  el("cfgStepDelay").value = data.step_delay || 1500;
  el("cfgTimeout").value = data.page_timeout || 30000;
  el("cfgNetworkDelay").value = data.network_delay || 3000;
  el("cfgInteractionDelay").value = data.interaction_delay || 500;
  el("cfgTypingDelay").value = data.typing_delay || 75;
}

function getSettingsPayload() {
  return {
    username: el("cfgUser").value.trim(),
    password: el("cfgPass").value.trim(),
    uf: el("cfgUf").value,
    step_delay: el("cfgStepDelay").value,
    page_timeout: el("cfgTimeout").value,
    network_delay: el("cfgNetworkDelay").value,
    interaction_delay: el("cfgInteractionDelay").value,
    typing_delay: el("cfgTypingDelay").value,
  };
}

function saveSettings() {
  const payload = getSettingsPayload();
  localStorage.setItem("logtudo_settings", JSON.stringify(payload));
  el("settingsStatus").textContent = "Salvo (local)";
}

el("btnSaveSettings").addEventListener("click", saveSettings);

function fillMappingOptions(headers) {
  const selects = [
    el("map-nf"),
    el("map-adc"),
    el("map-valor"),
    el("map-senha"),
    el("map-transporte"),
    el("map-cte"),
  ];
  selects.forEach((s) => {
    s.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "Selecione...";
    s.appendChild(empty);
    headers.forEach((h, idx) => {
      const opt = document.createElement("option");
      opt.value = idx;
      opt.textContent = h || `Coluna ${idx + 1}`;
      s.appendChild(opt);
    });
  });
}

function applyAutoMapping(mapping) {
  const map = {
    "map-nf": "nota_fiscal",
    "map-adc": "tipo_adc",
    "map-valor": "valor_cte",
    "map-senha": "senha_ravex",
    "map-transporte": "transporte",
    "map-cte": "cte_output",
  };
  Object.entries(map).forEach(([id, key]) => {
    if (mapping && mapping[key] !== undefined) {
      el(id).value = String(mapping[key]);
    }
  });
}

function renderPreview(preview) {
  const thead = el("previewTable").querySelector("thead");
  const tbody = el("previewTable").querySelector("tbody");
  thead.innerHTML = "";
  tbody.innerHTML = "";
  const headerRow = document.createElement("tr");
  preview.headers.forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h || "-";
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  preview.rows.forEach((row) => {
    const tr = document.createElement("tr");
    row.forEach((cell) => {
      const td = document.createElement("td");
      td.textContent = cell === null ? "" : String(cell);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  el("previewRows").textContent = `${preview.total_rows} linhas`;
}

function resetFile() {
  state.fileId = null;
  state.headers = [];
  state.jobId = null;
  el("fileName").textContent = "-";
  el("fileStats").textContent = "0 linhas, 0 colunas";
  el("fileBadge").textContent = "Nenhum arquivo";
  el("previewRows").textContent = "0 linhas";
  const thead = el("previewTable").querySelector("thead");
  const tbody = el("previewTable").querySelector("tbody");
  thead.innerHTML = "";
  tbody.innerHTML = "";
  ["map-nf", "map-adc", "map-valor", "map-senha", "map-transporte", "map-cte"].forEach((id) => {
    el(id).innerHTML = "";
  });
  el("fileInput").value = "";
  el("btnStart").disabled = false;
  el("btnStartTop").disabled = false;
  el("btnPause").disabled = true;
  el("btnStop").disabled = true;
}


el("fileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const settings = getSettingsPayload();
  if (settings.uf) {
    form.append("uf", settings.uf);
  }
  const res = await fetch("/api/files", { method: "POST", body: form });
  if (!res.ok) return;
  const data = await res.json();
  state.fileId = data.fileId;
  state.headers = data.preview.headers;
  el("fileName").textContent = data.fileInfo.name || file.name;
  el("fileStats").textContent = `${data.preview.total_rows} linhas, ${data.preview.total_columns} colunas`;
  el("fileBadge").textContent = "Pronto";
  fillMappingOptions(state.headers);
  applyAutoMapping(data.autoMapping);
  renderPreview(data.preview);
});

function getMapping() {
  return {
    nota_fiscal: parseInt(el("map-nf").value, 10),
    tipo_adc: parseInt(el("map-adc").value, 10),
    valor_cte: parseInt(el("map-valor").value, 10),
    senha_ravex: parseInt(el("map-senha").value, 10),
    transporte: parseInt(el("map-transporte").value, 10),
    cte_output: parseInt(el("map-cte").value, 10),
  };
}

function validateMapping(mapping) {
  return Object.values(mapping).every((v) => Number.isInteger(v));
}

async function startJob() {
  if (!state.fileId) return;
  const mapping = getMapping();
  if (!validateMapping(mapping)) return;
  const settings = getSettingsPayload();
  const payload = {
    fileId: state.fileId,
    columnMapping: mapping,
    executeEnvios: el("toggleEnvios").checked,
    settings,
  };
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) return;
  const data = await res.json();
  state.jobId = data.jobId;
  el("btnStart").disabled = true;
  el("btnStartTop").disabled = true;
  el("btnPause").disabled = false;
  el("btnStop").disabled = false;
  connectLogs();
  pollStatus();
}

async function pauseJob() {
  if (!state.jobId) return;
  await fetch(`/api/jobs/${state.jobId}/pause`, { method: "POST" });
}

async function resumeJob() {
  if (!state.jobId) return;
  await fetch(`/api/jobs/${state.jobId}/resume`, { method: "POST" });
}

async function stopJob() {
  if (!state.jobId) return;
  await fetch(`/api/jobs/${state.jobId}/stop`, { method: "POST" });
}

el("btnStart").addEventListener("click", startJob);
el("btnStartTop").addEventListener("click", startJob);
el("btnPause").addEventListener("click", async () => {
  if (el("btnPause").dataset.state === "paused") {
    await resumeJob();
    el("btnPause").dataset.state = "";
    el("btnPause").textContent = "Pausar";
  } else {
    await pauseJob();
    el("btnPause").dataset.state = "paused";
    el("btnPause").textContent = "Retomar";
  }
});
el("btnStop").addEventListener("click", stopJob);

function updateStatus(status) {
  el("runStatus").textContent = status;
  el("connStatus").textContent = state.jobId ? "Conectado" : "Desconectado";
}

async function pollStatus() {
  if (!state.jobId) return;
  const res = await fetch(`/api/jobs/${state.jobId}/status`);
  if (!res.ok) return;
  const data = await res.json();
  updateStatus(data.status);
  const pct = data.progress || 0;
  el("progressBar").style.width = `${pct}%`;
  el("progressBadge").textContent = `${pct}%`;
  el("progressText").textContent = `${pct}% - ${data.currentStep} de ${data.totalSteps}`;
  el("currentNF").textContent = `NF: ${data.currentNF}`;
  if (data.status === "completed" || data.status === "stopped" || data.status === "error") {
    el("btnPause").disabled = true;
    el("btnStop").disabled = true;
    el("btnStart").disabled = false;
    el("btnStartTop").disabled = false;
    loadResults();
    return;
  }
  setTimeout(pollStatus, 1500);
}

function connectLogs() {
  if (!state.jobId) return;
  const stream = new EventSource(`/api/jobs/${state.jobId}/logs/stream`);
  stream.onmessage = (event) => {
    if (!event.data) return;
    const entry = JSON.parse(event.data);
    state.logs.push(entry);
    renderLogs();
  };
  stream.addEventListener("ping", () => {});
  stream.onerror = () => {
    stream.close();
  };
}

function renderLogs() {
  const container = el("logStream");
  container.innerHTML = "";
  const filtered =
    state.logFilter === "ALL"
      ? state.logs
      : state.logs.filter((l) => l.level === state.logFilter);
  filtered.forEach((log) => {
    const div = document.createElement("div");
    div.className = `log-entry ${log.level.toLowerCase()}`;
    div.innerHTML = `<span>${log.timestamp}</span><span class="level">${log.level}</span><span>${log.message}</span>`;
    container.appendChild(div);
  });
  if (state.autoScroll) {
    container.parentElement.scrollTop = container.parentElement.scrollHeight;
  }
}

el("logFilter").addEventListener("change", (e) => {
  state.logFilter = e.target.value;
  renderLogs();
});

el("btnClearLogs")?.addEventListener("click", async () => {
  if (!state.jobId) return;
  const res = await fetch(`/api/jobs/${state.jobId}/logs/clear`, { method: "POST" });
  if (res.ok) {
    state.logs = [];
    renderLogs();
  }
});

el("autoScroll").addEventListener("change", (e) => {
  state.autoScroll = e.target.checked;
});

async function loadResults() {
  if (!state.jobId) return;
  const res = await fetch(`/api/jobs/${state.jobId}/results`);
  if (!res.ok) return;
  const data = await res.json();
  state.results = data.results || [];
  renderResults();
}

function renderResults() {
  const tbody = el("resultsTable").querySelector("tbody");
  tbody.innerHTML = "";
  const query = el("resultSearch").value.toLowerCase();
  const filtered = state.results.filter((r) => {
    const target = `${r.nota_fiscal || ""} ${r.cte_number || ""}`.toLowerCase();
    return target.includes(query);
  });
  filtered.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.status}</td>
      <td>${r.nota_fiscal}</td>
      <td>${r.tipo_adc}</td>
      <td>${r.cte_number}</td>
      <td>${r.message}</td>
      <td>${r.timestamp}</td>
    `;
    tbody.appendChild(tr);
  });
  const total = state.results.length;
  const success = state.results.filter((r) => r.status === "success").length;
  const error = state.results.filter((r) => r.status === "error").length;
  const pending = total - success - error;
  el("sumSuccess").textContent = success;
  el("sumError").textContent = error;
  el("sumPending").textContent = pending;
  el("sumRate").textContent = total ? `${Math.round((success / total) * 100)}%` : "0%";
}

el("resultSearch").addEventListener("input", renderResults);

async function exportResults(format) {
  if (!state.jobId) return;
  const res = await fetch(`/api/jobs/${state.jobId}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format }),
  });
  if (!res.ok) return;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `resultados.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

el("btnExportCsv").addEventListener("click", () => exportResults("csv"));
el("btnExportXlsx").addEventListener("click", () => exportResults("xlsx"));

el("btnQuickLogs").addEventListener("click", () => {
  views.processamento.scrollIntoView({ behavior: "smooth" });
});

loadSettings();


el("btnClearFile").addEventListener("click", resetFile);
