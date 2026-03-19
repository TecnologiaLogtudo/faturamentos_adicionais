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

const syncJobIdInputs = (jobId) => {
  jobIdInputs.forEach((id) => {
    const input = qs(id);
    if (input) {
      input.value = jobId || "";
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
  return value || selectedJobId;
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
  if (!res.ok) return;
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
  if (!res.ok) return;
  const data = await res.json();
  const tbody = qs("jobsTable").querySelector("tbody");
  tbody.innerHTML = "";
  const items = data.items || [];
  items.forEach((j) => {
    const tr = document.createElement("tr");
    tr.dataset.jobId = j.id;
    tr.classList.add("jobs-row");
    tr.innerHTML = `
      <td>${j.id}</td>
      <td>${j.status}</td>
      <td>${j.username || "-"}</td>
      <td>${j.ip || "-"}</td>
      <td>${j.started_at || "-"}</td>
      <td>${j.duration_sec || "-"}</td>
    `;
    tr.addEventListener("click", async () => {
      await selectJob(j.id);
    });
    tbody.appendChild(tr);
  });

  if (!items.length) {
    selectedJobId = "";
    syncJobIdInputs("");
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
  if (!res.ok) return;
  const data = await res.json();
  const tbody = qs("actionsTable").querySelector("tbody");
  tbody.innerHTML = "";
  (data.items || []).forEach((a) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${a.action_type}</td>
      <td>${a.actor || "-"}</td>
      <td>${a.ip || "-"}</td>
      <td>${a.timestamp || "-"}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadSteps(jobId) {
  if (!jobId) return;
  const res = await fetch(withBasePath(`/api/admin/jobs/${jobId}/steps`));
  if (!res.ok) return;
  const data = await res.json();
  const tbody = qs("stepsTable").querySelector("tbody");
  tbody.innerHTML = "";
  (data.items || []).forEach((s) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${s.name}</td>
      <td>${s.status}</td>
      <td>${s.started_at || "-"}</td>
      <td>${s.ended_at || "-"}</td>
      <td>${s.metadata ? JSON.stringify(s.metadata) : "-"}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadArtifacts(jobId) {
  if (!jobId) return;
  const res = await fetch(withBasePath(`/api/admin/jobs/${jobId}/artifacts`));
  if (!res.ok) return;
  const data = await res.json();
  const tbody = qs("artifactsTable").querySelector("tbody");
  tbody.innerHTML = "";
  (data.items || []).forEach((a) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${a.type}</td>
      <td>${a.file_path}</td>
      <td>${a.created_at || "-"}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadBrowserLogs(jobId) {
  if (!jobId) return;
  const res = await fetch(withBasePath(`/api/admin/jobs/${jobId}/browser-logs`));
  if (!res.ok) return;
  const data = await res.json();
  const tbody = qs("browserTable").querySelector("tbody");
  tbody.innerHTML = "";
  (data.items || []).forEach((l) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${l.level}</td>
      <td>${l.type}</td>
      <td>${l.message}</td>
      <td>${l.url || "-"}</td>
      <td>${l.timestamp || "-"}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadErrors(jobId) {
  if (!jobId) return;
  const res = await fetch(withBasePath(`/api/admin/jobs/${jobId}/errors`));
  if (!res.ok) return;
  const data = await res.json();
  const tbody = qs("errorsTable").querySelector("tbody");
  tbody.innerHTML = "";
  (data.items || []).forEach((e) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${e.message}</td>
      <td>${e.timestamp || "-"}</td>
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

qs("statusFilter").addEventListener("change", loadJobs);
qs("btnLoadActions").addEventListener("click", async () => {
  const jobId = getJobIdFromInputOrSelected("actionsJobId");
  await selectJob(jobId);
  await loadActions(jobId);
});
qs("btnLoadSteps").addEventListener("click", async () => {
  const jobId = getJobIdFromInputOrSelected("stepsJobId");
  await selectJob(jobId);
  await loadSteps(jobId);
});
qs("btnLoadArtifacts").addEventListener("click", async () => {
  const jobId = getJobIdFromInputOrSelected("artifactsJobId");
  await selectJob(jobId);
  await loadArtifacts(jobId);
});
qs("btnLoadBrowser").addEventListener("click", async () => {
  const jobId = getJobIdFromInputOrSelected("browserJobId");
  await selectJob(jobId);
  await loadBrowserLogs(jobId);
});
qs("btnLoadErrors").addEventListener("click", async () => {
  const jobId = getJobIdFromInputOrSelected("errorsJobId");
  await selectJob(jobId);
  await loadErrors(jobId);
});
qs("btnRefresh").addEventListener("click", async () => {
  await loadSummary();
  await loadJobs();
});

loadSummary();
loadJobs();
