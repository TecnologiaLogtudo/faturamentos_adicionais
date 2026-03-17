const qs = (id) => document.getElementById(id);

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    panels.forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    qs(`panel-${tab.dataset.tab}`).classList.add("active");
  });
});

async function loadSummary() {
  const res = await fetch("/api/admin/summary");
  if (!res.ok) return;
  const data = await res.json();
  qs("kpiTotal").textContent = data.total_jobs ?? 0;
  qs("kpiSuccess").textContent = data.success_jobs ?? 0;
  qs("kpiError").textContent = data.error_jobs ?? 0;
  qs("kpiRunning").textContent = data.running_jobs ?? 0;
}

async function loadJobs() {
  const status = qs("statusFilter").value;
  const url = new URL("/api/admin/jobs", window.location.origin);
  if (status) url.searchParams.set("status", status);
  const res = await fetch(url.toString());
  if (!res.ok) return;
  const data = await res.json();
  const tbody = qs("jobsTable").querySelector("tbody");
  tbody.innerHTML = "";
  (data.items || []).forEach((j) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${j.id}</td>
      <td>${j.status}</td>
      <td>${j.username || "-"}</td>
      <td>${j.ip || "-"}</td>
      <td>${j.started_at || "-"}</td>
      <td>${j.duration_sec || "-"}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadActions(jobId) {
  if (!jobId) return;
  const res = await fetch(`/api/admin/jobs/${jobId}/actions`);
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
  const res = await fetch(`/api/admin/jobs/${jobId}/steps`);
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
  const res = await fetch(`/api/admin/jobs/${jobId}/artifacts`);
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
  const res = await fetch(`/api/admin/jobs/${jobId}/browser-logs`);
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
  const res = await fetch(`/api/admin/jobs/${jobId}/errors`);
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

qs("statusFilter").addEventListener("change", loadJobs);
qs("btnLoadActions").addEventListener("click", () => loadActions(qs("actionsJobId").value.trim()));
qs("btnLoadSteps").addEventListener("click", () => loadSteps(qs("stepsJobId").value.trim()));
qs("btnLoadArtifacts").addEventListener("click", () => loadArtifacts(qs("artifactsJobId").value.trim()));
qs("btnLoadBrowser").addEventListener("click", () => loadBrowserLogs(qs("browserJobId").value.trim()));
qs("btnLoadErrors").addEventListener("click", () => loadErrors(qs("errorsJobId").value.trim()));
qs("btnRefresh").addEventListener("click", () => {
  loadSummary();
  loadJobs();
});

qs("btnLogout").addEventListener("click", async () => {
  await fetch("/admin/logout", { method: "POST" });
  window.location.href = "/admin/login";
});

loadSummary();
loadJobs();
