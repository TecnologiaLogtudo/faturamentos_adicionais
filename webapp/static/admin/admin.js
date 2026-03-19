const qs = (id) => document.getElementById(id);
const RAW_BASE_PATH = window.LOGTUDO_BASE_PATH || "";
const BASE_PATH = RAW_BASE_PATH.replace(/\/+$/, "");
const withBasePath = (path) => {
  if (!BASE_PATH) {
    return path;
  }
  const trimmed = path.replace(/^\/+/, "");
  return `${BASE_PATH}/${trimmed}`;
};

const backHomeLink = qs("backHomeLink");
if (backHomeLink) {
  backHomeLink.href = withBasePath("/");
}

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");
const jobIdInputs = ["actionsJobId", "stepsJobId", "artifactsJobId", "browserJobId", "errorsJobId"];
let selectedJobId = "";
const jobMetaByFullId = new Map();
const fullIdByShortId = new Map();

const toDate = (value) => {
  if (!value) return null;
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return null;
  return dt;
};

const pad2 = (n) => String(n).padStart(2, "0");

const formatDateTime = (value) => {
  const dt = toDate(value);
  if (!dt) return "-";
  return `${pad2(dt.getDate())}/${pad2(dt.getMonth() + 1)}/${dt.getFullYear()} ${pad2(dt.getHours())}:${pad2(dt.getMinutes())}`;
};

const buildBaseShortId = (value) => {
  const dt = toDate(value);
  if (!dt) return "";
  return `${pad2(dt.getDate())}${pad2(dt.getMonth() + 1)}${dt.getFullYear()}-${pad2(dt.getHours())}${pad2(dt.getMinutes())}`;
};

const uniqueShortId = (baseId, usageMap) => {
  if (!baseId) return "";
  const count = (usageMap.get(baseId) || 0) + 1;
  usageMap.set(baseId, count);
  if (count === 1) return baseId;
  return `${baseId}-${count}`;
};

const buildFallbackShortId = (fullId) => {
  if (!fullId) return "";
  return fullId.slice(0, 8);
};

const shortIdFromFullId = (fullId) => {
  return jobMetaByFullId.get(fullId)?.shortId || fullId || "";
};

const resolveJobId = (value) => {
  if (!value) return "";
  if (jobMetaByFullId.has(value)) return value;
  if (fullIdByShortId.has(value)) return fullIdByShortId.get(value);
  return value;
};

const copyToClipboard = async (text) => {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (_error) {
    try {
      const tmp = document.createElement("textarea");
      tmp.value = text;
      tmp.style.position = "fixed";
      tmp.style.left = "-9999px";
      document.body.appendChild(tmp);
      tmp.focus();
      tmp.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(tmp);
      return !!ok;
    } catch (_fallbackError) {
      return false;
    }
  }
};

const syncJobIdInputs = (jobId) => {
  const displayId = shortIdFromFullId(jobId);
  jobIdInputs.forEach((id) => {
    const input = qs(id);
    if (input) {
      input.value = displayId || "";
    }
  });
};

const highlightSelectedJobRow = () => {
  document.querySelectorAll("#jobsTable tbody tr").forEach((row) => {
    const isSelected = row.dataset.jobId === selectedJobId;
    row.classList.toggle("active", isSelected);
  });
};

const getActiveTab = () => {
  const activeTab = document.querySelector(".tab.active");
  return activeTab?.dataset?.tab || "overview";
};

const getJobIdFromInputOrSelected = (inputId) => {
  const value = qs(inputId)?.value?.trim() || "";
  return resolveJobId(value) || selectedJobId;
};

const ensureToastRoot = () => {
  let root = document.getElementById("toastRoot");
  if (!root) {
    root = document.createElement("div");
    root.id = "toastRoot";
    root.className = "toast-root";
    document.body.appendChild(root);
  }
  return root;
};

const showToast = (message, type = "info") => {
  const root = ensureToastRoot();
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  root.appendChild(toast);
  setTimeout(() => toast.classList.add("show"), 10);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 180);
  }, 2300);
};

const withLoading = async (buttonId, fn) => {
  const btn = qs(buttonId);
  if (!btn) {
    await fn();
    return;
  }
  const oldText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Carregando...";
  try {
    await fn();
  } finally {
    btn.disabled = false;
    btn.textContent = oldText;
  }
};

const renderEmptyRow = (tbody, colSpan, message) => {
  tbody.innerHTML = `<tr><td colspan="${colSpan}" class="table-empty">${message}</td></tr>`;
};

tabs.forEach((tab) => {
  tab.addEventListener("click", async () => {
    tabs.forEach((t) => t.classList.remove("active"));
    panels.forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    qs(`panel-${tab.dataset.tab}`).classList.add("active");
    await loadPanelData(tab.dataset.tab, selectedJobId);
  });
});

async function loadSummary() {
  const res = await fetch(withBasePath("/api/admin/summary"));
  if (!res.ok) {
    showToast("Falha ao carregar resumo", "error");
    return;
  }
  const data = await res.json();
  qs("kpiTotal").textContent = data.total_jobs ?? 0;
  qs("kpiSuccess").textContent = data.success_jobs ?? 0;
  qs("kpiError").textContent = data.error_jobs ?? 0;
  qs("kpiRunning").textContent = data.running_jobs ?? 0;
}

async function loadJobs() {
  const status = qs("statusFilter").value;
  const url = new URL(withBasePath("/api/admin/jobs"), window.location.origin);
  if (status) url.searchParams.set("status", status);
  const res = await fetch(url.toString());
  if (!res.ok) {
    showToast("Falha ao carregar jobs", "error");
    return;
  }
  const data = await res.json();
  const tbody = qs("jobsTable").querySelector("tbody");
  tbody.innerHTML = "";
  jobMetaByFullId.clear();
  fullIdByShortId.clear();
  const shortIdUsage = new Map();
  const items = data.items || [];
  items.forEach((j) => {
    const shortBase = buildBaseShortId(j.started_at);
    const shortId = uniqueShortId(shortBase, shortIdUsage) || buildFallbackShortId(j.id);
    jobMetaByFullId.set(j.id, {
      shortId,
      startedAtFormatted: formatDateTime(j.started_at),
    });
    fullIdByShortId.set(shortId, j.id);

    const tr = document.createElement("tr");
    tr.dataset.jobId = j.id;
    tr.classList.add("jobs-row");
    tr.innerHTML = `
      <td><button class="job-id-copy" type="button" data-short-id="${shortId}" data-full-id="${j.id}" title="Clique para copiar">${shortId}</button></td>
      <td>${j.status}</td>
      <td>${j.username || "-"}</td>
      <td>${j.ip || "-"}</td>
      <td>${formatDateTime(j.started_at)}</td>
      <td>${j.duration_sec || "-"}</td>
    `;
    const copyBtn = tr.querySelector(".job-id-copy");
    if (copyBtn) {
      copyBtn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const shortToCopy = copyBtn.dataset.shortId || "";
        const copied = await copyToClipboard(shortToCopy);
        if (copied) {
          copyBtn.classList.add("copied");
          copyBtn.textContent = "Copiado";
          showToast(`ID ${shortToCopy} copiado`, "success");
          setTimeout(() => {
            copyBtn.classList.remove("copied");
            copyBtn.textContent = shortToCopy;
          }, 1100);
        } else {
          showToast("Nao foi possivel copiar o ID", "error");
        }

        const oldTitle = copyBtn.title;
        copyBtn.title = copied ? "ID copiado" : "Falha ao copiar";
        setTimeout(() => {
          copyBtn.title = oldTitle;
        }, 1000);
      });
    }
    tr.addEventListener("click", async () => {
      await selectJob(j.id);
    });
    tbody.appendChild(tr);
  });

  if (!items.length) {
    selectedJobId = "";
    syncJobIdInputs("");
    renderEmptyRow(tbody, 6, "Nenhum job encontrado para o filtro atual.");
    return;
  }

  const exists = items.some((item) => item.id === selectedJobId);
  if (!exists) {
    selectedJobId = items[0].id;
    syncJobIdInputs(selectedJobId);
  }

  highlightSelectedJobRow();
  await loadPanelData(getActiveTab(), selectedJobId);
}

async function loadActions(jobId) {
  if (!jobId) return;
  const res = await fetch(withBasePath(`/api/admin/jobs/${jobId}/actions`));
  const tbody = qs("actionsTable").querySelector("tbody");
  if (!res.ok) {
    showToast("Falha ao carregar acoes", "error");
    renderEmptyRow(tbody, 4, "Nao foi possivel carregar as acoes.");
    return;
  }
  const data = await res.json();
  tbody.innerHTML = "";
  if (!(data.items || []).length) {
    renderEmptyRow(tbody, 4, "Nenhuma acao encontrada para este job.");
    return;
  }
  (data.items || []).forEach((a) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${a.action_type}</td>
      <td>${a.actor || "-"}</td>
      <td>${a.ip || "-"}</td>
      <td>${formatDateTime(a.timestamp)}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadSteps(jobId) {
  if (!jobId) return;
  const res = await fetch(withBasePath(`/api/admin/jobs/${jobId}/steps`));
  const tbody = qs("stepsTable").querySelector("tbody");
  if (!res.ok) {
    showToast("Falha ao carregar passos", "error");
    renderEmptyRow(tbody, 5, "Nao foi possivel carregar os passos.");
    return;
  }
  const data = await res.json();
  tbody.innerHTML = "";
  if (!(data.items || []).length) {
    renderEmptyRow(tbody, 5, "Nenhum passo encontrado para este job.");
    return;
  }
  (data.items || []).forEach((s) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${s.name}</td>
      <td>${s.status}</td>
      <td>${formatDateTime(s.started_at)}</td>
      <td>${formatDateTime(s.ended_at)}</td>
      <td>${s.metadata ? JSON.stringify(s.metadata) : "-"}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadArtifacts(jobId) {
  if (!jobId) return;
  const res = await fetch(withBasePath(`/api/admin/jobs/${jobId}/artifacts`));
  const tbody = qs("artifactsTable").querySelector("tbody");
  if (!res.ok) {
    showToast("Falha ao carregar artefatos", "error");
    renderEmptyRow(tbody, 3, "Nao foi possivel carregar os artefatos.");
    return;
  }
  const data = await res.json();
  tbody.innerHTML = "";
  if (!(data.items || []).length) {
    renderEmptyRow(tbody, 3, "Nenhum artefato encontrado para este job.");
    return;
  }
  (data.items || []).forEach((a) => {
    const artifactUrl = withBasePath(`/api/admin/artifacts/${a.id}/file`);
    const fileName = (a.file_path || "").split(/[\\/]/).pop() || "arquivo";
    const isAvailable = !!a.available;
    const linkHtml = isAvailable
      ? `<a class="artifact-link" href="${artifactUrl}" target="_blank" rel="noopener noreferrer">${fileName}</a>`
      : `<span class="artifact-missing" title="Arquivo nao encontrado no disco">${fileName}</span>`;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${a.type}</td>
      <td>
        ${linkHtml}
      </td>
      <td>${formatDateTime(a.created_at)}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadBrowserLogs(jobId) {
  if (!jobId) return;
  const res = await fetch(withBasePath(`/api/admin/jobs/${jobId}/browser-logs`));
  const tbody = qs("browserTable").querySelector("tbody");
  if (!res.ok) {
    showToast("Falha ao carregar logs do browser", "error");
    renderEmptyRow(tbody, 5, "Nao foi possivel carregar os logs do browser.");
    return;
  }
  const data = await res.json();
  tbody.innerHTML = "";
  if (!(data.items || []).length) {
    renderEmptyRow(tbody, 5, "Nenhum log de browser encontrado para este job.");
    return;
  }
  (data.items || []).forEach((l) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${l.level}</td>
      <td>${l.type}</td>
      <td>${l.message}</td>
      <td>${l.url || "-"}</td>
      <td>${formatDateTime(l.timestamp)}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadErrors(jobId) {
  if (!jobId) return;
  const res = await fetch(withBasePath(`/api/admin/jobs/${jobId}/errors`));
  const tbody = qs("errorsTable").querySelector("tbody");
  if (!res.ok) {
    showToast("Falha ao carregar erros", "error");
    renderEmptyRow(tbody, 3, "Nao foi possivel carregar os erros.");
    return;
  }
  const data = await res.json();
  tbody.innerHTML = "";
  if (!(data.items || []).length) {
    renderEmptyRow(tbody, 3, "Nenhum erro encontrado para este job.");
    return;
  }
  (data.items || []).forEach((e) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${e.message}</td>
      <td>${formatDateTime(e.timestamp)}</td>
      <td>${e.context ? JSON.stringify(e.context) : "-"}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadPanelData(tabName, jobId) {
  if (!jobId) return;
  if (tabName === "actions") {
    await loadActions(jobId);
  }
  if (tabName === "steps") {
    await loadSteps(jobId);
  }
  if (tabName === "artifacts") {
    await loadArtifacts(jobId);
  }
  if (tabName === "browser") {
    await loadBrowserLogs(jobId);
  }
  if (tabName === "errors") {
    await loadErrors(jobId);
  }
}

async function selectJob(jobId) {
  if (!jobId) return;
  selectedJobId = jobId;
  syncJobIdInputs(jobId);
  highlightSelectedJobRow();
  await loadPanelData(getActiveTab(), jobId);
}

async function resetLogsWithConfirmation() {
  const password = window.prompt("Confirme a senha para apagar todos os dados de log:");
  if (password === null) {
    return;
  }
  if (!password.trim()) {
    showToast("Senha obrigatoria para reset", "error");
    return;
  }

  await withLoading("btnResetLogs", async () => {
    const res = await fetch(withBasePath("/api/admin/reset-logs"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const detail = data?.detail || "Nao foi possivel resetar os logs.";
      showToast(detail, "error");
      return;
    }

    selectedJobId = "";
    jobMetaByFullId.clear();
    fullIdByShortId.clear();
    syncJobIdInputs("");
    document.querySelectorAll("table tbody").forEach((tbody) => {
      tbody.innerHTML = "";
    });

    await loadSummary();
    await loadJobs();
    showToast("Historico de logs apagado com sucesso", "success");
  });
}

qs("statusFilter").addEventListener("change", loadJobs);
qs("btnLoadActions").addEventListener("click", async () => {
  await withLoading("btnLoadActions", async () => {
    const jobId = getJobIdFromInputOrSelected("actionsJobId");
    await selectJob(jobId);
    await loadActions(jobId);
  });
});
qs("btnLoadSteps").addEventListener("click", async () => {
  await withLoading("btnLoadSteps", async () => {
    const jobId = getJobIdFromInputOrSelected("stepsJobId");
    await selectJob(jobId);
    await loadSteps(jobId);
  });
});
qs("btnLoadArtifacts").addEventListener("click", async () => {
  await withLoading("btnLoadArtifacts", async () => {
    const jobId = getJobIdFromInputOrSelected("artifactsJobId");
    await selectJob(jobId);
    await loadArtifacts(jobId);
  });
});
qs("btnLoadBrowser").addEventListener("click", async () => {
  await withLoading("btnLoadBrowser", async () => {
    const jobId = getJobIdFromInputOrSelected("browserJobId");
    await selectJob(jobId);
    await loadBrowserLogs(jobId);
  });
});
qs("btnLoadErrors").addEventListener("click", async () => {
  await withLoading("btnLoadErrors", async () => {
    const jobId = getJobIdFromInputOrSelected("errorsJobId");
    await selectJob(jobId);
    await loadErrors(jobId);
  });
});
qs("btnRefresh").addEventListener("click", async () => {
  await withLoading("btnRefresh", async () => {
    await loadSummary();
    await loadJobs();
    showToast("Painel atualizado", "success");
  });
});
qs("btnResetLogs")?.addEventListener("click", resetLogsWithConfirmation);

jobIdInputs.forEach((inputId, idx) => {
  const input = qs(inputId);
  if (!input) return;
  const actionButtonIds = ["btnLoadActions", "btnLoadSteps", "btnLoadArtifacts", "btnLoadBrowser", "btnLoadErrors"];
  const targetButton = qs(actionButtonIds[idx]);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      targetButton?.click();
    }
  });
});

loadSummary();
loadJobs();
