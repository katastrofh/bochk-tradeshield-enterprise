let token = localStorage.getItem("ts_token") || "";
let selectedCaseId = null;
let selectedCase = null;

function headers() {
  return token ? { "Authorization": `Bearer ${token}` } : {};
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { ...(opts.headers || {}), ...headers() }
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || res.statusText);
  }
  return res.json();
}

async function login() {
  const body = new URLSearchParams();
  body.append("email", document.getElementById("email").value.trim());
  body.append("password", document.getElementById("password").value);
  try {
    const data = await api("/auth/login", { method: "POST", body });
    token = data.access_token;
    localStorage.setItem("ts_token", token);
    document.getElementById("currentUser").textContent = data.full_name;
    document.getElementById("currentRole").textContent = data.role;
    document.getElementById("loginStatus").textContent = `Logged in as ${data.email}`;
    await loadCases();
    await loadAudit();
    await loadGovernance();
  } catch (e) {
    document.getElementById("loginStatus").textContent = `Login failed: ${e.message}`;
  }
}

function money(x) {
  if (x === null || x === undefined) return "—";
  return `HK$${Number(x).toLocaleString()}`;
}

function statusPill(s) {
  return `<span class="pill">${s || "—"}</span>`;
}
function riskPill(r) {
  if (!r) return `<span class="pill">Not scored</span>`;
  return `<span class="pill ${r.category}">${r.category} • ${r.score}</span>`;
}

async function loadCases() {
  const data = await api("/cases");
  const cases = data.cases;
  const latest = data.latest_risk || {};
  document.getElementById("kpiCases").textContent = cases.length;
  const risky = Object.values(latest).filter(r => r && (r.category === "MEDIUM" || r.category === "HIGH")).length;
  document.getElementById("kpiRisk").textContent = risky;
  document.getElementById("kpiPending").textContent = cases.filter(c => !c.decision).length;
  const rows = [
    `<div class="row header"><div>Case</div><div>Route</div><div>Amount</div><div>Status</div><div>Risk</div><div>Action</div></div>`
  ];
  for (const c of cases) {
    const r = latest[c.id];
    rows.push(`
      <div class="row" onclick="selectCase(${c.id})">
        <div><b>${c.case_ref}</b><br><span class="small">${c.sme_name}</span></div>
        <div>${c.origin_country} → ${c.destination_country}<br><span class="small">${c.goods_description}</span></div>
        <div>${money(c.requested_financing_hkd)}<br><span class="small">invoice ${money(c.invoice_amount_hkd)}</span></div>
        <div>${statusPill(c.status)}</div>
        <div>${riskPill(r)}</div>
        <div><button class="secondary">Open</button></div>
      </div>
    `);
  }
  document.getElementById("caseTable").innerHTML = rows.join("");
  if (cases.length && !selectedCaseId) await selectCase(cases[1]?.id || cases[0].id);
}

async function selectCase(id) {
  selectedCaseId = id;
  const data = await api(`/cases/${id}/passport`);
  selectedCase = data.case;
  renderPassport(data);
  await loadFraud();
}

function workflowHtml(workflow) {
  return workflow.map(w => `<div class="field"><span>${w.step}</span><b>${w.complete ? "Complete" : "Pending"}</b></div>`).join("");
}

function renderPassport(data) {
  const c = data.case;
  const r = data.latest_risk;
  const docs = data.documents || [];
  const scoreHtml = r ? `
    <div class="score">${r.overall_score}</div>
    <span class="pill ${r.category}">${r.category} risk</span>
    <p>${r.narrative}</p>
  ` : `<p>No risk passport generated yet. Click “Generate / Refresh Risk Passport”.</p>`;

  const bars = r ? Object.entries(r.sub_scores).map(([k, v]) => `
    <div class="bar"><span>${k.replaceAll("_", " ")}</span><div class="track"><div class="fill" style="width:${v}%"></div></div><b>${v}</b></div>
  `).join("") : "";

  const drivers = r ? r.risk_drivers.map(x => `<li>${x}</li>`).join("") : "<li>Not scored</li>";
  const mitigants = r ? r.mitigating_factors.map(x => `<li>${x}</li>`).join("") : "<li>Not scored</li>";
  const required = r ? r.required_actions.map(x => `<li>${x}</li>`).join("") : "<li>Not scored</li>";
  const fraud = r ? r.fraud_indicators.map(x => `<li>${x}</li>`).join("") : "<li>No risk score yet</li>";

  document.getElementById("passportView").innerHTML = `
    <div class="passport">
      <div class="card">
        <h3>${c.case_ref} — ${c.sme_name}</h3>
        <div class="grid2">
          <div class="field"><span>Route</span><b>${c.origin_country} → ${c.destination_country}</b></div>
          <div class="field"><span>Status</span><b>${c.status}</b></div>
          <div class="field"><span>Supplier</span><b>${c.supplier_name}</b></div>
          <div class="field"><span>Buyer</span><b>${c.buyer_name}</b></div>
          <div class="field"><span>Invoice</span><b>${money(c.invoice_amount_hkd)}</b></div>
          <div class="field"><span>Requested financing</span><b>${money(c.requested_financing_hkd)}</b></div>
          <div class="field"><span>Supplier account</span><b>${c.supplier_bank_account}</b></div>
          <div class="field"><span>Previous account</span><b>${c.previous_supplier_bank_account || "None"}</b></div>
          <div class="field"><span>Settlement status</span><b>${c.settlement_status}</b></div>
          <div class="field"><span>ESG status</span><b>${c.esg_status}</b></div>
        </div>
        <h3>Workflow readiness</h3>
        <div class="grid2">${workflowHtml(data.workflow)}</div>
      </div>
      <div class="card">
        <h3>Risk Summary</h3>
        ${scoreHtml}
        <div class="bars">${bars}</div>
      </div>
      <div class="card">
        <h3>Top risk drivers</h3>
        <ul>${drivers}</ul>
        <h3>Required controls</h3>
        <ul>${required}</ul>
      </div>
      <div class="card">
        <h3>Mitigating factors</h3>
        <ul>${mitigants}</ul>
        <h3>Fraud indicators</h3>
        <ul>${fraud}</ul>
      </div>
      <div class="card">
        <h3>Document evidence</h3>
        ${docs.length ? docs.map(d => `<div class="field"><span>${d.doc_type} • ${d.filename}</span><b>SHA-256 ${d.file_hash.slice(0,16)}...</b></div>`).join("") : "<p class='small'>No uploaded documents yet. Use sample invoices through the API or upload later.</p>"}
      </div>
      <div class="card">
        <h3>Audit chain</h3>
        <p>Valid: <b>${data.audit_chain.valid}</b></p>
        <p class="small">Latest hash: ${data.audit_chain.latest_hash || "—"}</p>
      </div>
    </div>
  `;
}

async function scoreSelected() {
  if (!selectedCaseId) return alert("Select a case first.");
  try {
    await api(`/cases/${selectedCaseId}/score`, { method: "POST" });
    await selectCase(selectedCaseId);
    await loadCases();
    await loadAudit();
  } catch (e) { alert(e.message); }
}

async function submitDecision() {
  if (!selectedCaseId) return alert("Select a case first.");
  const payload = {
    decision: document.getElementById("decisionType").value,
    approved_amount_hkd: Number(document.getElementById("approvedAmount").value || 0),
    reason: document.getElementById("decisionReason").value
  };
  try {
    const c = await api(`/cases/${selectedCaseId}/decision`, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "Content-Type": "application/json" }
    });
    document.getElementById("decisionResult").textContent = `Decision recorded: ${c.status}.`;
    await selectCase(selectedCaseId);
    await loadCases();
    await loadAudit();
  } catch (e) { document.getElementById("decisionResult").textContent = e.message; }
}

async function verifySupplier() {
  await action(`/cases/${selectedCaseId}/settlement/verify-supplier`, "Supplier verified.");
}
async function verifyShipment() {
  await action(`/cases/${selectedCaseId}/settlement/verify-shipment`, "Shipment verified.");
}
async function releaseSettlement() {
  await action(`/cases/${selectedCaseId}/settlement/release`, "Settlement released.");
}
async function verifyESG() {
  const payload = { certificate_id: "ESG-HK-2026-771", issuer: "Hong Kong Green Trade Registry", expiry_date: "2027-12-31", scope: "Low-carbon electronics supply chain" };
  try {
    await api(`/cases/${selectedCaseId}/esg/verify`, { method: "POST", body: JSON.stringify(payload), headers: { "Content-Type": "application/json" } });
    document.getElementById("decisionResult").textContent = "ESG certificate recorded.";
    await selectCase(selectedCaseId); await loadAudit();
  } catch (e) { document.getElementById("decisionResult").textContent = e.message; }
}
async function action(path, msg) {
  if (!selectedCaseId) return alert("Select a case first.");
  try {
    await api(path, { method: "POST" });
    document.getElementById("decisionResult").textContent = msg;
    await selectCase(selectedCaseId); await loadCases(); await loadAudit();
  } catch (e) { document.getElementById("decisionResult").textContent = e.message; }
}

async function loadFraud() {
  if (!selectedCaseId) return;
  const g = await api(`/cases/${selectedCaseId}/fraud-graph`);
  document.getElementById("fraudNarrative").innerHTML = `<b>Fraud narrative:</b> ${g.narrative}<br><b>Indicators:</b> ${g.indicators.length ? g.indicators.join(" • ") : "No material graph indicator detected."}`;
  document.getElementById("graph").innerHTML = g.nodes.map(n => `<div class="node ${n.type}"><b>${n.label}</b><span class="small">${n.type.replaceAll("_", " ")}</span></div>`).join("");
}

async function loadAudit() {
  try {
    const a = await api("/audit");
    document.getElementById("kpiAudit").textContent = a.chain.valid ? "valid" : "broken";
    document.getElementById("auditView").innerHTML = a.events.slice(0, 20).map(ev => `
      <div class="audit-item">
        <b>${ev.event_type}</b> <span class="small">${ev.actor_email} • ${ev.created_at}</span>
        <p>${ev.event_summary}</p>
        <code>${ev.event_hash}</code>
      </div>
    `).join("");
  } catch (e) { document.getElementById("auditView").textContent = e.message; }
}

async function loadGovernance() {
  try {
    const models = await api("/governance/model-registry");
    document.getElementById("modelRegistry").innerHTML = models.map(m => `
      <div class="field"><span>${m.model_name} ${m.version}</span><b>${m.validation_status}</b><p class="small">${m.limitations}</p></div>
    `).join("");
  } catch (e) {}
}

function downloadReport() {
  if (!selectedCaseId) return alert("Select a case first.");
  window.open(`/cases/${selectedCaseId}/report.pdf`, "_blank");
}

window.onload = async () => {
  if (token) {
    try {
      const u = await api("/auth/me");
      document.getElementById("currentUser").textContent = u.full_name;
      document.getElementById("currentRole").textContent = u.role;
      await loadCases(); await loadAudit(); await loadGovernance();
    } catch (_) { token = ""; localStorage.removeItem("ts_token"); }
  }
};


window.demoOfficerLogin = async function () {
  const email = document.getElementById("email");
  const password = document.getElementById("password");
  const status = document.getElementById("loginStatus");

  email.value = "officer@tradeshield.ai";
  password.value = "demo12345";
  if (status) status.textContent = "Logging in as officer@tradeshield.ai...";
  await login();
};

Object.assign(window, {
  login,
  demoOfficerLogin,
  loadCases,
  selectCase,
  scoreSelected,
  submitDecision,
  verifySupplier,
  verifyShipment,
  releaseSettlement,
  verifyESG,
  loadFraud,
  loadAudit,
  loadGovernance,
  downloadReport
});
