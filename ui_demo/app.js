const view = document.getElementById("view");
const breadcrumb = document.getElementById("breadcrumb");

const initialRecords = [
  { id: "TG-26018", company: "Tonle Garment Co.", supplier: "Eastline Machines", type: "CDC", importYear: "2026", cdcListId: "CDC-DEMO-TG-2026", invoice: "TG-26018", hbl: "DEMO-HBL-018", eta: "24 Oct", status: "At port", docs: "4 of 5", container: "DEMO-CT-018" },
  { id: "AL-26041", company: "Angkor Loom Co.", supplier: "Lotus Equipment Ltd.", type: "CDC", importYear: "2026", cdcListId: null, invoice: "AL-26041", hbl: "DEMO-HBL-041", eta: "29 Oct", status: "Needs review", docs: "3 of 5", container: "DEMO-CT-041" },
  { id: "MF-26044", company: "Mekhala Foods", supplier: "Pioneer Packaging", type: "General", invoice: "MF-26044", hbl: "DEMO-HBL-044", eta: "28 Oct", status: "In transit", docs: "2 of 5", container: "DEMO-CT-044" },
];

const sampleDetails = {
  "TG-26018": {
    invoiceDate: "2026-10-18", origin: "Shanghai, China", destination: "Sihanoukville, Cambodia",
    amount: 25400, currency: "USD", packages: 10, grossWeight: 1800, netWeight: 1630, volume: 9.6,
    invoiceLines: [
      { hsCode: "DEMO-HS-01", chinese: "工业缝纫机", english: "Industrial sewing machine", quantity: 6, unit: "SET", unitPrice: 3600, amount: 21600 },
      { hsCode: "DEMO-HS-02", chinese: "验布台", english: "Fabric inspection table", quantity: 4, unit: "PCS", unitPrice: 950, amount: 3800 },
    ],
    packingLines: [
      { hsCode: "DEMO-HS-01", chinese: "工业缝纫机", english: "Industrial sewing machine", quantity: 6, unit: "SET", packages: 6, grossWeight: 1320, netWeight: 1200, volume: 7.2 },
      { hsCode: "DEMO-HS-02", chinese: "验布台", english: "Fabric inspection table", quantity: 4, unit: "PCS", packages: 4, grossWeight: 480, netWeight: 430, volume: 2.4 },
    ],
  },
  "AL-26041": {
    invoiceDate: "2026-10-21", origin: "Shenzhen, China", destination: "Sihanoukville, Cambodia",
    amount: 15000, currency: "USD", packages: 7, grossWeight: 840, netWeight: 760, volume: 4.5,
    invoiceLines: [
      { hsCode: "DEMO-HS-03", chinese: "织机控制箱", english: "Loom control panel", quantity: 3, unit: "SET", unitPrice: 4200, amount: 12600 },
      { hsCode: "DEMO-HS-04", chinese: "备用电机", english: "Spare motor", quantity: 8, unit: "PCS", unitPrice: 300, amount: 2400 },
    ],
    packingLines: [
      { hsCode: "DEMO-HS-03", chinese: "织机控制箱", english: "Loom control panel", quantity: 3, unit: "SET", packages: 3, grossWeight: 600, netWeight: 540, volume: 3.4 },
      { hsCode: "DEMO-HS-04", chinese: "备用电机", english: "Spare motor", quantity: 8, unit: "PCS", packages: 4, grossWeight: 240, netWeight: 220, volume: 1.1 },
    ],
  },
  "MF-26044": {
    invoiceDate: "2026-10-22", origin: "Guangzhou, China", destination: "Sihanoukville, Cambodia",
    amount: 12800, currency: "USD", packages: 5, grossWeight: 1110, netWeight: 1000, volume: 7.6,
    invoiceLines: [
      { hsCode: "DEMO-HS-05", chinese: "封箱机", english: "Carton sealing machine", quantity: 2, unit: "SET", unitPrice: 5200, amount: 10400 },
      { hsCode: "DEMO-HS-06", chinese: "不锈钢料斗", english: "Stainless steel hopper", quantity: 3, unit: "PCS", unitPrice: 800, amount: 2400 },
    ],
    packingLines: [
      { hsCode: "DEMO-HS-05", chinese: "封箱机", english: "Carton sealing machine", quantity: 2, unit: "SET", packages: 2, grossWeight: 720, netWeight: 650, volume: 5.2 },
      { hsCode: "DEMO-HS-06", chinese: "不锈钢料斗", english: "Stainless steel hopper", quantity: 3, unit: "PCS", packages: 3, grossWeight: 390, netWeight: 350, volume: 2.4 },
    ],
  },
};
const companyOptions = ["Tonle Garment Co.", "Angkor Loom Co.", "Mekhala Foods", "XIN CAI FU (CAMBODIA) CO., LTD.", "NEW FOCUS APPAREL (CAMBODIA) CO., LTD.", "KING SG APPAREL (CAMBODIA) CO., LTD."];
const demoCdcLists = [{
  id: "CDC-DEMO-TG-2026", company: "Tonle Garment Co.", cycleYear: "2026",
  validFrom: "2026-01-01", validTo: "2026-12-31", qip: "DEMO-QIP-2026",
  approvalReference: "Demo preset", approvalFile: "Fictional sample", fileName: "Fictional sample master list",
  layout: "Demo preset", itemCount: 2, status: "verified", demo: true,
  items: [{ row: 6, description: "Industrial sewing machine", unit: "SET", approved: 20, remaining: 20 },
    { row: 7, description: "Fabric inspection table", unit: "PCS", approved: 10, remaining: 10 }]
}, {
  id: "CDC-DEMO-TG-2025", company: "Tonle Garment Co.", cycleYear: "2025",
  validFrom: "2025-01-01", validTo: "2025-12-31", qip: "DEMO-QIP-2025",
  approvalReference: "Demo preset", approvalFile: "Fictional sample", fileName: "Fictional 2025 master list",
  layout: "Demo preset", itemCount: 3, status: "verified", demo: true,
  items: [{ row: 11, description: "Industrial sewing machine", unit: "SET", approved: 12, remaining: 6 },
    { row: 12, description: "Fabric inspection table", unit: "PCS", approved: 8, remaining: 4 },
    { row: 13, description: "Fabric roll rack", unit: "PCS", approved: 15, remaining: 9 }]
}];
for (const record of initialRecords) {
  const sample = sampleDetails[record.id];
  Object.assign(record, {
    sample: true, invoiceDate: sample.invoiceDate, origin: sample.origin, destination: sample.destination,
    amount: sample.amount, currency: sample.currency, packages: sample.packages,
    grossWeight: sample.grossWeight, netWeight: sample.netWeight, volume: sample.volume,
    extracted: { invoiceLines: sample.invoiceLines.map(line => ({...line})), packingLines: sample.packingLines.map(line => ({...line})), issues: [] },
  });
}

const state = {
  screen: "register",
  records: [...initialRecords],
  cdcLists: [...demoCdcLists],
  workspaceCompany: "Tonle Garment Co.",
  cdcYear: "2026",
  cdcUploadOpen: false,
  cdcSearch: "",
  cdcDraft: { company: "XIN CAI FU (CAMBODIA) CO., LTD.", cycleYear: "2026", validFrom: "", validTo: "", qip: "", approvalReference: "", approvalFile: "", fileName: "", parsed: null, acknowledged: false, error: "" },
  cdcNotice: "",
  cdcReturn: "register",
  importYear: "2026",
  selectedId: initialRecords[0].id,
  detailTab: "Overview",
  documentMode: "details",
  attachments: {},
  wizardAttachments: {},
  uploadError: "",
  extractedData: null,
  sampleFlow: false,
  search: "",
  statusFilter: "All stages",
  quickFilter: "all",
  reviewIndex: null,
  reviewDraft: null,
  reviewError: "",
  wizardStep: 0,
  method: "upload",
  importType: "CDC",
  company: "Tonle Garment Co.",
  supplier: "",
  invoice: "",
  invoiceFile: "",
  packingFile: "",
  extracted: false,
  decisions: { term: "pending", quantity: "pending", cdc: "pending" },
  permitChecks: {},
  error: "",
};

function e(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}
function badge(text, tone = "") { return `<span class="badge ${tone}">${e(text)}</span>`; }
function shown(value, unit = "") { return value === null || value === undefined || value === "" ? "—" : `${value}${unit}`; }
function money(value, currency = "USD") { return value === null || value === undefined || value === "" ? "—" : `${currency ? currency + " " : ""}${Number(value).toLocaleString("en-US", {maximumFractionDigits:2})}`; }
function button(label, action, cls = "") { return `<button class="btn ${cls}" type="button" data-action="${action}">${e(label)}</button>`; }
function itemTab(record) { return record.type === "CDC" ? "Items & CDC" : "Items"; }
function invoiceItems(record) { return record.extracted?.invoiceLines || []; }
function reviewAt(record, index) { return record.reviews?.[index] || { status: "pending", description: "", quantity: "", note: "" }; }
function pendingReviewCount(record) { return invoiceItems(record).filter((_, index) => reviewAt(record, index).status !== "confirmed").length; }
function reviewBadge(status) { return badge(status === "confirmed" ? "Confirmed" : status === "followup" ? "Follow up" : "Pending", status === "confirmed" ? "" : "amber"); }
function lineDifferences(record, index) {
  const inv = invoiceItems(record)[index];
  const pack = record.extracted?.packingLines?.[index];
  const found = [];
  if (!pack) found.push("No matching packing line");
  else {
    if (inv.quantity !== pack.quantity || inv.unit.toUpperCase() !== pack.unit.toUpperCase()) found.push("Quantity or unit differs between invoice and packing list");
    if (inv.hsCode !== pack.hsCode || inv.chinese !== pack.chinese) found.push("Item identity differs between documents");
  }
  if (inv.english && invoiceItems(record).some((other, otherIndex) => otherIndex !== index && other.english.toLowerCase() === inv.english.toLowerCase() && other.chinese !== inv.chinese)) found.push("Supplier English repeats for a different Chinese item");
  return found;
}
function sameCompany(left, right) { return window.cdcMasterReader.companyKey(left) === window.cdcMasterReader.companyKey(right); }
function activeCdcList(company, year) {
  return [...state.cdcLists].reverse().find(list => list.status === "verified" && sameCompany(list.company,company) && list.cycleYear === String(year));
}
function linkedCdcList(record) {
  const list = state.cdcLists.find(entry => entry.id === record.cdcListId);
  return list?.status === "verified" && sameCompany(list.company,record.company) && list.cycleYear === String(record.importYear) ? list : null;
}
function cdcCandidate(list, item) {
  if (!list || !item) return null;
  const key = value => String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  return list.items.find(entry => key(entry.description) === key(item.english));
}
function cdcDraftIssues() {
  const draft = state.cdcDraft;
  const issues = [];
  if (!draft.parsed) return ["Upload a CDC master-list workbook."];
  if (!draft.parsed.structureOk) issues.push("Workbook headings or item rows could not be verified.");
  if (draft.parsed.detectedCompany && !sameCompany(draft.company,draft.parsed.detectedCompany)) issues.push("Workbook company differs from the selected company.");
  if (!draft.qip.trim()) issues.push("Enter and check the QIP or CIB reference.");
  if (draft.qip.trim() && draft.parsed.qip && draft.qip.replace(/[^a-z0-9]/gi, "").toUpperCase() !== draft.parsed.qip.replace(/[^a-z0-9]/gi, "").toUpperCase()) issues.push("Entered QIP/CIB reference differs from the workbook.");
  if (!draft.validFrom || !draft.validTo || draft.validFrom > draft.validTo) issues.push("Enter a valid start and end date.");
  if (draft.validFrom && draft.cycleYear && draft.validFrom.slice(0,4) !== String(draft.cycleYear)) issues.push("The cycle year should match the start date of this version.");
  if (!draft.approvalReference.trim() || !draft.approvalFile) issues.push("Attach the approval document and enter its reference.");
  if (!draft.acknowledged) issues.push("An admin must confirm the workbook and approval document were checked.");
  return issues;
}
function openCdcLibrary(returnScreen = state.screen) {
  if (returnScreen === "detail") state.workspaceCompany = selectedRecord().company;
  if (returnScreen === "wizard") state.workspaceCompany = state.company;
  state.cdcDraft.company = state.workspaceCompany;
  state.cdcYear = activeCdcList(state.workspaceCompany, state.cdcYear)?.cycleYear ||
    [...state.cdcLists].filter(list => sameCompany(list.company, state.workspaceCompany)).sort((a,b) => b.cycleYear.localeCompare(a.cycleYear))[0]?.cycleYear || "2026";
  state.cdcReturn = returnScreen === "cdc" ? "register" : returnScreen;
  state.screen = "cdc"; state.cdcNotice = ""; render();
}
function field(label, key, value, placeholder = "") {
  return `<div class="field"><label for="field-${key}">${e(label)}</label><input id="field-${key}" data-field="${key}" value="${e(value)}" placeholder="${e(placeholder)}" /></div>`;
}
function setBreadcrumb(parts) { breadcrumb.innerHTML = parts.map(e).join(" <span>/</span> "); }
function render() {
  const companySwitcher = document.getElementById("workspace-company");
  companySwitcher.innerHTML = companyOptions.map(name => `<option value="${e(name)}" ${sameCompany(name, state.workspaceCompany) ? "selected" : ""}>${e(name)}</option>`).join("");
  if (state.screen === "register") renderRegister();
  if (state.screen === "wizard") renderWizard();
  if (state.screen === "detail") renderDetail();
  if (state.screen === "cdc") renderCdcLibrary();
  document.querySelectorAll?.("[data-nav]").forEach(node => {
    if (node.dataset.nav === "cdc") node.classList.toggle("active-parent", state.screen === "cdc");
    if (node.dataset.nav === "imports" && node.classList.contains("nav-item")) node.classList.toggle("active-parent", state.screen !== "cdc");
    if (node.dataset.nav === "imports" && node.closest(".subnav")) node.classList.toggle("active", state.screen !== "cdc");
  });
}

function cdcField(label, key, value, type = "text") {
  return `<label class="field"><span>${e(label)}</span><input type="${type}" data-cdc-field="${key}" value="${e(value)}" /></label>`;
}
function renderCdcLibrary() {
  const company = state.workspaceCompany;
  const companyLists = state.cdcLists.filter(list => list.status === "verified" && sameCompany(list.company, company));
  const years = [...new Set([state.cdcYear, ...companyLists.map(list => list.cycleYear)])].sort((a, b) => b.localeCompare(a));
  const selected = activeCdcList(company, state.cdcYear);
  const search = state.cdcSearch.trim().toLowerCase();
  const items = selected?.items.filter(item => !search || [item.row, item.description, item.unit].join(" ").toLowerCase().includes(search)) || [];
  const draft = state.cdcDraft;
  const parsed = draft.parsed;
  const issues = cdcDraftIssues();
  setBreadcrumb(["Workspace", company, "CDC master list"]);
  view.innerHTML = `<div class="page-heading"><div><div class="eyebrow">CDC master list</div><h1>${e(company)}</h1><p>View this company's list by year. Choose another company from the sidebar.</p></div><div class="button-row">${button(state.cdcUploadOpen ? "Close upload" : "Upload year list", "toggle-cdc-upload", state.cdcUploadOpen ? "" : "primary")}${button("← Back", "return-cdc")}</div></div>
    <div class="cdc-year-tabs" role="tablist" aria-label="CDC year">${years.map(year => `<button type="button" role="tab" aria-selected="${year === state.cdcYear}" class="${year === state.cdcYear ? "active" : ""}" data-cdc-year="${e(year)}">${e(year)}</button>`).join("")}</div>
    ${state.cdcNotice ? `<div class="sample-callout cdc-notice">${e(state.cdcNotice)}</div>` : ""}
    ${selected ? `<section class="card cdc-list-card"><div class="cdc-list-heading"><div><div class="eyebrow">${e(state.cdcYear)} list</div><h2>${e(selected.qip)}</h2><p>${e(selected.fileName)} · ${e(selected.validFrom)} to ${e(selected.validTo)}</p></div><div class="cdc-list-heading-right">${badge(selected.demo ? "Fictional demo" : "Internally verified", selected.demo ? "blue" : "")}<strong>${selected.items.length} items</strong></div></div>
      <div class="cdc-table-toolbar"><div><strong>All CDC items</strong><span>Approved and remaining quantities from this year's workbook</span></div><input class="search" id="cdc-item-search" value="${e(state.cdcSearch)}" placeholder="Search description, row or unit…" aria-label="Search CDC items" /></div>
      <div class="table-scroll"><table class="cdc-items-table"><thead><tr><th>No.</th><th>Source row</th><th>Item description</th><th>Unit</th><th>Approved</th><th>Remaining in source</th></tr></thead><tbody>${items.map((item, index) => `<tr><td>${index + 1}</td><td>${e(shown(item.row))}</td><td class="cdc-description">${e(item.description)}</td><td>${e(item.unit)}</td><td>${e(shown(item.approved))}</td><td>${e(shown(item.remaining))}</td></tr>`).join("") || `<tr><td colspan="6" class="empty-state">No items match this search.</td></tr>`}</tbody></table></div><div class="table-footer"><span>Showing ${items.length} of ${selected.items.length} items</span><span>Source balances are shown as stored. No stock is deducted.</span></div></section>` : `<section class="card cdc-empty-year"><h2>No CDC list for ${e(company)} in ${e(state.cdcYear)}</h2><p>Upload this company's approved workbook to show its items here.</p>${button("Upload year list", "toggle-cdc-upload", "primary")}</section>`}
    ${state.cdcUploadOpen ? `<section class="card card-pad cdc-upload-panel"><div class="eyebrow">Add a year list</div><h2 class="section-title">${e(company)}</h2><p class="section-help">Upload the workbook and its approval file, then check the detected company and QIP before internal verification.</p>
      <div class="form-grid">${cdcField("Cycle year", "cycleYear", draft.cycleYear, "number")}${cdcField("Valid from", "validFrom", draft.validFrom, "date")}${cdcField("Valid to", "validTo", draft.validTo, "date")}</div>
      <div class="upload-grid cdc-upload-grid"><label class="upload-box"><span class="upload-icon">⇧</span><strong>${e(draft.fileName || "CDC workbook")}</strong><small>XLS or XLSX</small><input type="file" data-cdc-master-upload accept=".xls,.xlsx" /></label><label class="upload-box"><span class="upload-icon">⇧</span><strong>${e(draft.approvalFile || "Approval document")}</strong><small>PDF or image</small><input type="file" data-cdc-approval-upload accept=".pdf,.png,.jpg,.jpeg" /></label></div>
      ${parsed ? `<div class="cdc-detection"><strong>Workbook detected</strong><div>${e(parsed.layout)} · ${e(parsed.sheetName)} · ${parsed.itemCount} items</div><div>Company in file: <b>${e(shown(parsed.detectedCompany))}</b></div><div>QIP/CIB in file: <b>${e(shown(parsed.qip))}</b></div>${parsed.warnings.map(warning => `<div class="cdc-warning">${e(warning)}</div>`).join("")}</div>` : ""}
      <div class="form-grid">${cdcField("QIP / CIB reference", "qip", draft.qip)}${cdcField("Approval reference", "approvalReference", draft.approvalReference)}</div>
      <label class="checkline cdc-ack"><input type="checkbox" data-cdc-ack ${draft.acknowledged ? "checked" : ""}/> I checked the company, QIP, dates and approval document.</label>
      ${issues.length && parsed ? `<div class="alert"><strong>Before verification</strong>${issues.map(issue => `<div>• ${e(issue)}</div>`).join("")}</div>` : ""}${draft.error ? `<div class="alert">${e(draft.error)}</div>` : ""}
      <button class="btn primary" type="button" data-action="verify-cdc" ${issues.length ? "disabled" : ""}>Mark internally verified</button><p class="viewer-note">Internal verification in this demo is not CDC approval.</p></section>` : ""}`;
}

function renderRegister() {
  setBreadcrumb(["Workspace", "Imports"]);
  const term = state.search.trim().toLowerCase();
  const filtered = state.records.filter(r =>
    (state.statusFilter === "All stages" || r.status === state.statusFilter) &&
    (state.quickFilter === "all" || state.quickFilter === "review" && pendingReviewCount(r) > 0 || state.quickFilter === "port" && r.status === "At port") &&
    (!term || [r.company, r.supplier, r.invoice, r.hbl, r.container].join(" ").toLowerCase().includes(term))
  );
  const openReviews = state.records.filter(r => pendingReviewCount(r) > 0).length;
  const atPort = state.records.filter(r => r.status === "At port").length;
  const inTransit = state.records.filter(r => r.status === "In transit").length;
  const missingCdc = state.records.filter(r => r.type === "CDC" && !linkedCdcList(r)).length;
  view.innerHTML = `
    <div class="page-heading">
      <div><div class="eyebrow">Import register</div><h1>Imports</h1><p>Track each shipment from supplier documents through item review, permit preparation and arrival.</p></div>
      <div class="heading-actions">${button("Import supplier Excel", "import-excel")}${button("+ New import", "new-import", "primary")}</div>
    </div>
    <div class="stat-grid">
      <div class="card stat"><div class="stat-label">Import records</div><div class="stat-value">${state.records.length}</div><div class="stat-note">In this browser demo</div></div>
      <div class="card stat"><div class="stat-label">Need item review</div><div class="stat-value">${openReviews}</div><div class="stat-note">At least one line pending</div></div>
      <div class="card stat"><div class="stat-label">At port</div><div class="stat-value">${atPort}</div><div class="stat-note">Stage recorded on imports</div></div>
      <div class="card stat"><div class="stat-label">In transit</div><div class="stat-value">${inTransit}</div><div class="stat-note">Awaiting later documents</div></div>
    </div>
    ${missingCdc ? `<div class="alert register-alert"><strong>${missingCdc} CDC import${missingCdc === 1 ? "" : "s"} awaiting a verified master list</strong>Supplier documents can be recorded, but CDC matching and permit preparation need a linked list. <button class="link-btn" type="button" data-action="open-cdc-library">Open master lists →</button></div>` : ""}
    <section class="card">
      <div class="register-toolbar"><div class="view-tabs"><button type="button" data-register-filter="all" class="${state.quickFilter === "all" ? "active" : ""}">All imports</button><button type="button" data-register-filter="review" class="${state.quickFilter === "review" ? "active" : ""}">Needs item review</button><button type="button" data-register-filter="port" class="${state.quickFilter === "port" ? "active" : ""}">At port</button></div><span class="muted-note">Sample records are marked in each import</span></div>
      <div class="filter-row"><input class="search" id="register-search" value="${e(state.search)}" placeholder="Search company, supplier, invoice, HBL…" aria-label="Search imports" /><select class="filter" id="stage-filter" aria-label="Filter by stage"><option>All stages</option><option>At port</option><option>Needs review</option><option>In transit</option><option>Draft</option></select></div>
      <div class="table-scroll"><table><thead><tr><th>Company / supplier</th><th>Invoice</th><th>Type</th><th>Invoice amount</th><th>Packages</th><th>Route</th><th>Item review</th><th>CDC list</th><th>Stage</th><th></th></tr></thead><tbody>
      ${filtered.map(r => `<tr data-open="${e(r.id)}"><td><strong>${e(r.company)}</strong><small>${e(r.supplier)}</small></td><td class="ref">${e(r.invoice)}</td><td>${badge(r.type, r.type === "General" ? "gray" : "")}</td><td>${e(money(r.amount, r.currency))}</td><td>${e(shown(r.packages))}</td><td>${e(r.origin || "—")} → ${e(r.destination || "—")}</td><td>${pendingReviewCount(r) ? badge(`${pendingReviewCount(r)} pending`, "amber") : badge("Clear")}</td><td>${r.type === "CDC" ? linkedCdcList(r) ? badge(linkedCdcList(r).cycleYear) : badge("Missing","amber") : "—"}</td><td>${badge(r.status, r.status === "Needs review" ? "amber" : r.status === "In transit" ? "blue" : "")}</td><td style="color:#0c7d71;font-size:16px">›</td></tr>`).join("") || '<tr><td colspan="10" class="empty-state">No imports match these filters.</td></tr>'}
      </tbody></table></div>
      <div class="table-footer"><span>Showing ${filtered.length} demo records</span><span>Click a row to open its import detail</span></div>
    </section>`;
  document.getElementById("stage-filter").value = state.statusFilter;
}

function resetWizard() {
  Object.values(state.wizardAttachments).forEach(releaseAttachment);
  Object.assign(state, {
    screen: "wizard", wizardStep: 0, method: "upload", importType: "CDC", importYear: "2026",
    company: "Tonle Garment Co.", supplier: "", invoice: "", invoiceFile: "",
    packingFile: "", invoiceDate: "", total: "", packages: "", weight: "", origin: "", destination: "", currency: "USD",
    manualChecked: false, extracted: false, extractedData: null, sampleFlow: false, wizardAttachments: {},
    reviewIndex: null, reviewDraft: null, reviewError: "",
    decisions: { term: "pending", quantity: "pending", cdc: "pending" }, error: ""
  });
  render();
}
function steps() {
  const labels = ["Setup", "Invoice & packing list", "Review & create"];
  return `<div class="card wizard-steps">${labels.map((label, i) => `<div class="step ${i === state.wizardStep ? "current" : i < state.wizardStep ? "done" : ""}"><span class="step-number">${i < state.wizardStep ? "✓" : i + 1}</span><span>${label}</span></div>`).join("")}</div>`;
}
function wizardHeading() {
  const subs = [
    "Choose how to enter the shipment and which import process applies.",
    state.method === "upload" ? "Attach supplier documents and check the details found in them." : "Enter the invoice and packing information yourself.",
    "Confirm register details, create the draft, then review item lines in the import record."
  ];
  return `<div class="page-heading"><div><div class="eyebrow">New import · Step ${state.wizardStep + 1} of 3</div><h1>Create import</h1><p>${e(subs[state.wizardStep])}</p></div><div class="heading-actions">${button("Back to imports", "back-register")}</div></div>`;
}
function summaryAside() {
  const list = state.importType === "CDC" ? activeCdcList(state.company,state.importYear) : null;
  return `<aside class="card aside-card"><h3>Record preview</h3>
    <div class="summary-row"><span>Company</span><strong>${e(state.company)}</strong></div>
    <div class="summary-row"><span>Entry method</span><strong>${state.method === "upload" ? "Upload documents" : "Manual entry"}</strong></div>
    <div class="summary-row"><span>Import type</span><strong>${e(state.importType)}</strong></div>
    <div class="summary-row"><span>Invoice</span><strong>${e(state.invoice || "Not entered")}</strong></div>
    <div class="summary-row"><span>Item lines</span><strong>${state.extractedData?.invoiceLines?.length ?? "Not added"}</strong></div>
    <div class="summary-row"><span>Source files</span><strong>${Object.keys(state.wizardAttachments).length ? "Attached" : "None"}</strong></div>
    ${state.importType === "CDC" ? `<div class="summary-row"><span>CDC list</span><strong>${list ? e(`${list.demo ? "Demo · " : ""}${list.cycleYear} · ${list.qip}`) : "Missing · intake draft"}</strong></div>` : ""}
    <p>Save the draft, then confirm item descriptions and quantities inside the import record.</p>
  </aside>`;
}
function renderWizard() {
  setBreadcrumb(["Workspace", "Imports", "Create import"]);
  let body = "";
  if (state.wizardStep === 0) body = setupStep();
  if (state.wizardStep === 1) body = documentsStep();
  if (state.wizardStep === 2) body = reviewStep();
  view.innerHTML = wizardHeading() + steps() + `<div class="wizard-layout"><div class="wizard-main">${body}</div>${summaryAside()}</div>`;
}
function setupStep() {
  const list = activeCdcList(state.company,state.importYear);
  return `
    <section class="card card-pad"><h2 class="section-title">1. How do you want to enter this import?</h2><p class="section-help">Both paths create the same import record.</p>
      <div class="choice-grid">
        <button class="choice ${state.method === "upload" ? "selected" : ""}" type="button" data-choice="method:upload"><span class="radio"></span><span class="choice-icon">⇧</span><strong>Upload invoice & packing list</strong><small>Start with supplier files and review extracted information.</small></button>
        <button class="choice ${state.method === "manual" ? "selected" : ""}" type="button" data-choice="method:manual"><span class="radio"></span><span class="choice-icon">✎</span><strong>Enter manually</strong><small>Type the shipment information without uploading files first.</small></button>
      </div>
    </section>
    <section class="card card-pad"><h2 class="section-title">2. Which import process?</h2>
      <div class="choice-grid">
        <button class="choice ${state.importType === "CDC" ? "selected" : ""}" type="button" data-choice="type:CDC"><span class="radio"></span><span class="choice-icon">▦</span><strong>CDC related</strong><small>Review item matches against this company's CDC master list.</small></button>
        <button class="choice ${state.importType === "General" ? "selected" : ""}" type="button" data-choice="type:General"><span class="radio"></span><span class="choice-icon">▤</span><strong>General import</strong><small>Record the shipment without a CDC matching step.</small></button>
      </div>
    </section>
    <section class="card card-pad"><h2 class="section-title">3. Importing company</h2><div class="form-grid"><div class="field"><label for="company">Company</label><select id="company" data-field="company">${[...new Set([state.company,...companyOptions])].map(name => `<option ${name === state.company ? "selected" : ""}>${e(name)}</option>`).join("")}</select></div><div class="field"><label for="field-importYear">Import cycle year</label><select id="field-importYear" data-field="importYear">${["2025","2026","2027"].map(year => `<option ${year === state.importYear ? "selected" : ""}>${year}</option>`).join("")}</select></div></div></section>
    ${state.importType === "CDC" ? `<section class="card card-pad cdc-prerequisite"><div><div class="eyebrow">4. CDC prerequisite</div><h2 class="section-title">${list ? list.demo ? "Fictional demo list available" : "Verified list available" : "No verified list for this company and cycle"}</h2><p class="section-help">${list ? `${e(list.company)} · ${e(list.qip)} · ${e(list.validFrom)} to ${e(list.validTo)}. ${list.demo ? "This preset demonstrates matching but cannot enable permit preparation." : "This version will be linked to the import draft."}` : "You can record supplier documents as an intake draft. CDC matching and permit preparation will wait until an admin verifies a list."}</p></div>${button(list ? "View master list" : "Set up master list", "open-cdc-library")}</section>` : `<div class="sample-callout">General imports do not require a CDC master list.</div>`}
    <div class="footer-actions"><span class="muted-note">You can save this record as a draft later.</span>${button("Continue →", "next", "primary")}</div>`;
}
function uploadBox(kind, title, filename) {
  return `<label class="upload-box"><span class="upload-icon">⇧</span><strong>${e(filename || title)}</strong><small>${filename ? "Click to change file" : "Choose an XLS or XLSX workbook"}</small><input type="file" data-upload="${kind}" accept=".xls,.xlsx" /></label>`;
}
function importPreview(data) {
  if (!data) return `<div class="empty-state">Upload the supplier workbook. If it has both invoice and packing-list sheets, one file is enough.</div>`;
  const facts = [
    ["Invoice", data.invoiceNo], ["Date", data.invoiceDate], ["Supplier", data.supplier],
    ["Consignee", data.company], ["Origin", data.origin], ["Destination", data.destination],
    ["Amount", money(data.amount, data.currency)], ["Item lines", data.invoiceLines.length],
    ["Packages", data.packages], ["Gross / net", `${shown(data.grossWeight)} / ${shown(data.netWeight)} kg`]
  ];
  return `<div class="import-preview">
    <div class="preview-status">${state.sampleFlow ? `${badge("Sample invoice values", "blue")}${badge("Sample packing values", "blue")}` : `${badge(data.invoiceSheet ? `Invoice · ${data.invoiceSheet}` : "Invoice missing", data.invoiceSheet ? "" : "amber")}${badge(data.packingSheet ? `Packing · ${data.packingSheet}` : "Packing list missing", data.packingSheet ? "" : "amber")}`}</div>
    <div class="kv-grid">${facts.map(([label,value]) => `<div class="kv"><span>${e(label)}</span><strong>${e(shown(value))}</strong></div>`).join("")}</div>
    <div class="preview-footer">${data.invoiceLines.length} invoice lines · ${data.packingLines.length} packing lines · ${data.issues.length} review item${data.issues.length === 1 ? "" : "s"}</div>
    ${data.issues.length ? `<div class="alert"><strong>Needs review</strong>${data.issues.map(issue => `<div>• ${e(issue)}</div>`).join("")}</div>` : `<div class="sample-callout">Invoice and packing quantities align. Review descriptions and company details before use.</div>`}
  </div>`;
}
function documentsStep() {
  if (state.method === "manual") return `
    <section class="card card-pad"><h2 class="section-title">Invoice details</h2><p class="section-help">Only the main fields for this UX demo.</p><div class="form-grid">
      ${field("Supplier", "supplier", state.supplier, "Supplier name")}
      ${field("Invoice number", "invoice", state.invoice, "e.g. DEMO-IM-026")}
      ${field("Invoice date", "invoiceDate", state.invoiceDate || "", "YYYY-MM-DD")}
      ${field("Invoice total", "total", state.total || "", "e.g. 32,500 USD")}
    </div></section>
    <section class="card card-pad"><h2 class="section-title">Packing list details</h2><div class="form-grid">
      ${field("Packages", "packages", state.packages || "", "e.g. 10 crates")}
      ${field("Gross weight", "weight", state.weight || "", "e.g. 8,200 kg")}
    </div></section>
    <div class="sample-callout">You can attach the original invoice, packing list and HBL after creating the draft.</div>
    ${state.error ? `<div class="alert">${e(state.error)}</div>` : ""}
    <div class="footer-actions">${button("← Back", "previous")}${button("Continue to review →", "next", "primary")}</div>`;

  return `
    <section class="card card-pad"><h2 class="section-title">Supplier Excel documents</h2><p class="section-help">Upload one workbook with Invoice and PackingList sheets, or upload separate files. Values below come from the files you choose.</p>
      <div class="upload-grid">${uploadBox("invoice", "Invoice or combined workbook", state.invoiceFile)}${uploadBox("packing", "Separate packing list (optional)", state.wizardAttachments.packing ? state.packingFile : "")}</div>
      ${state.extractedData?.packingSheet && !state.wizardAttachments.packing ? `<div class="inline-status">✓ Packing list found inside the invoice workbook.</div>` : ""}
      <div class="inline-status"><span class="status-dot"></span>HBL, arrival notice and customs files can be attached to the saved import later.</div>
    </section>
    <section class="card card-pad"><h2 class="section-title">What the system found</h2>
      ${state.extractedData ? `${state.sampleFlow ? `<div class="sample-callout sample-data-note">Fictional sample values. No supplier document is attached.</div>` : ""}${importPreview(state.extractedData)}` : importPreview(null)}
      <div class="button-row" style="margin-top:15px">${button("Use sample review flow", "sample-docs")}</div>
    </section>
    ${state.error ? `<div class="alert">${e(state.error)}</div>` : ""}
    <div class="footer-actions">${button("← Back", "previous")}<button class="btn primary" type="button" data-action="next" ${state.extracted ? "" : "disabled"}>Continue to review →</button></div>`;
}
function reviewStep() {
  const upload = state.method === "upload";
  const data = state.extractedData;
  const cdcList = state.importType === "CDC" ? activeCdcList(state.company,state.importYear) : null;
  return `
    ${state.sampleFlow ? `<div class="sample-callout">Sample data only. No supplier invoice or packing list has been attached.</div>` : ""}
    <section class="card card-pad"><h2 class="section-title">Register details</h2><p class="section-help">These are the shipment summary fields saved in the Imports register. Correct anything the workbook did not provide.</p>
      <div class="form-grid">${field("Importing company", "company", state.company)}${field("Supplier / shipper", "supplier", state.supplier)}${field("Invoice number", "invoice", state.invoice)}${field("Invoice date", "invoiceDate", state.invoiceDate || "")}${field("Origin", "origin", state.origin || "")}${field("Destination", "destination", state.destination || "")}${field("Invoice amount", "total", state.total || "")}${field("Packages", "packages", state.packages || "")}</div>
    </section>
    ${upload && data ? `<section class="card card-pad"><h2 class="section-title">Items ready for review</h2><p class="section-help">${data.invoiceLines.length} invoice lines and ${data.packingLines.length} packing lines will be saved with this draft. Review each line in ${state.importType === "CDC" ? "Items & CDC" : "Items"} after creating the record.</p><div class="inline-status">The source file stays attached for comparison.</div></section>
      <section class="card card-pad"><h2 class="section-title">Review findings</h2>${data.issues.length ? `<div class="alert"><strong>Check before permit use</strong>${data.issues.map(issue => `<div>• ${e(issue)}</div>`).join("")}</div>` : `<div class="sample-callout">No cross-document quantity difference detected. Confirm the translation and item specification yourself.</div>`}</section>` : upload ? `<div class="sample-callout">Sample flow only. No supplier files are attached.</div>` : `<section class="card card-pad"><h2 class="section-title">Manual entry check</h2><label class="checkline"><input type="checkbox" id="manual-check" ${state.manualChecked ? "checked" : ""}/> I checked the entered details against the source documents.</label></section>`}
    ${state.importType === "CDC" ? `<section class="card card-pad cdc-prerequisite"><div><div class="eyebrow">CDC list check</div><h2 class="section-title">${cdcList ? cdcList.demo ? "Demo preset ready to link" : "Master list ready to link" : "Master list needed"}</h2><p class="section-help">${cdcList ? `${e(cdcList.company)} · ${e(cdcList.qip)} · ${e(cdcList.cycleYear)}. ${cdcList.demo ? "This is fictional and cannot enable permit preparation." : "This exact version will stay linked to the import."}` : "This draft can be saved, but CDC matching and the permit application remain unavailable until a verified list is linked."}</p></div>${button("Manage master lists", "open-cdc-library")}</section>` : ""}
    <div class="sample-callout"><strong>Create a draft</strong><br/>Unresolved findings stay visible on the import record. The next step is item review.</div>
    <div class="footer-actions">${button("← Back", "previous")}${button("Create import draft", "create-record", "primary")}</div>`;
}

function selectedRecord() { return state.records.find(r => r.id === state.selectedId) || state.records[0]; }
function overviewReview(record) {
  const total = invoiceItems(record).length;
  const pending = pendingReviewCount(record);
  return `<section class="card card-pad overview-review"><div><div class="eyebrow">Item review</div><h2>${total ? pending ? `${pending} of ${total} lines need review` : `All ${total} lines confirmed` : "No item lines saved"}</h2><p>${total ? "Compare each invoice line with its packing details, then record a decision." : "Add item lines after creating the import record."}${record.extracted?.issues?.length ? ` ${record.extracted.issues.length} source finding${record.extracted.issues.length === 1 ? "" : "s"} recorded for reference.` : ""}</p></div>${button(total ? "Review items →" : "Add items →", "review-items", "primary")}</section>`;
}
function overviewCdc(record) {
  if (record.type !== "CDC") return "";
  const linked = linkedCdcList(record);
  const available = activeCdcList(record.company,record.importYear);
  return `<section class="card card-pad overview-review cdc-overview"><div><div class="eyebrow">CDC master-list prerequisite</div><h2>${linked ? linked.demo ? "Fictional demo list linked" : "Verified version linked" : "Master list not linked"}</h2><p>${linked ? `${e(linked.company)} · ${e(linked.qip)} · ${e(linked.cycleYear)} · ${e(linked.validFrom)} to ${e(linked.validTo)}. ${linked.demo ? "The demo preset cannot enable permit preparation." : "This shipment keeps that version."}` : available ? "A verified version is available for this company and cycle. Link it after checking the shipment." : "No internally verified version is available for this company and cycle. CDC matching and permit preparation are unavailable."}</p></div><div class="button-row">${available && available.id !== linked?.id ? button(linked ? "Link newer version" : "Link verified list", "link-cdc-list", "primary") : ""}${button("Master lists", "open-cdc-library")}</div></section>`;
}
function renderDetail() {
  const r = selectedRecord();
  setBreadcrumb(["Workspace", "Imports", r.id]);
  const tabs = ["Overview", "Invoice", "Packing list", r.type === "CDC" ? "Items & CDC" : "Items", ...(r.type === "CDC" ? ["Permit application"] : []), "Shipping docs", "Customs", "Transport", "Costs"];
  view.innerHTML = `
    <div class="detail-head"><button class="detail-back" type="button" data-action="back-register">← All imports</button>
      <div class="detail-title-row"><h1>${e(r.company)}</h1>${badge("Import", "gray")}${r.sample ? badge("Demo sample", "blue") : ""}${badge(r.status, r.status === "Needs review" ? "amber" : "")}</div>
      <p class="detail-sub">${e(r.invoice)} · ${e(r.supplier)} · Imported record</p>
    </div>
    <div class="detail-tabs" role="tablist">${tabs.map(tab => `<button type="button" role="tab" aria-selected="${tab === state.detailTab}" class="${tab === state.detailTab ? "active" : ""}" data-tab="${e(tab)}">${e(tab)}${tab === itemTab(r) && pendingReviewCount(r) ? ` <span class="tab-count">${pendingReviewCount(r)}</span>` : ""}</button>`).join("")}</div>
    ${state.detailTab === "Overview" ? overviewCdc(r) + overviewReview(r) : ""}
    ${detailContent(r)}
    ${reviewDrawer(r)}
  `;
}
function docRow(name, meta, status, tone = "") {
  return `<div class="doc-row"><div class="doc-name"><span class="doc-icon">▤</span><span><strong>${e(name)}</strong><small>${e(meta)}</small></span></div>${badge(status, tone)}</div>`;
}
function permitContent(r) {
  const checks = state.permitChecks[r.id] || {};
  const cdcList = linkedCdcList(r);
  const items = [
    ["documents", "Invoice and packing list checked"],
    ["cdc", "CDC company, QIP and item matches verified"],
    ["dates", "Shipment dates and totals checked"],
  ];
  const sourcesAttached = Boolean(r.invoiceFile && r.packingFile && !r.sample);
  const draftReady = Boolean(cdcList && !cdcList.demo && sourcesAttached && checks.documents && checks.dates);
  const ready = draftReady && items.every(([key]) => checks[key]) && invoiceItems(r).length > 0 && pendingReviewCount(r) === 0;
  return `<div class="detail-grid"><div class="detail-stack">
    <section class="card card-pad"><h2 class="section-title">Permit application workbook</h2><p class="section-help">Generate a separate application draft from this import record. The supplier originals stay attached here.</p>
      ${docRow("INV sheet", "Reviewed invoice, CDC numbers, values", "Excel")}
      ${docRow("PL sheet", "Packages, quantity and weights", "Excel")}
      <div class="inline-status">The Excel draft follows the two-sheet INV / PL structure of the reference workbook.</div>
    </section>
    <section class="card card-pad"><h2 class="section-title">Before reviewed export</h2>
      ${!cdcList ? `<div class="alert"><strong>CDC master list not linked</strong>Choose an internally verified list for this company and cycle before preparing a permit. <button type="button" class="link-btn" data-action="${activeCdcList(r.company,r.importYear) ? "link-cdc-list" : "open-cdc-library"}">${activeCdcList(r.company,r.importYear) ? "Link verified list" : "Set up master list"} →</button></div>` : cdcList.demo ? `<div class="alert"><strong>Fictional CDC preset</strong>Upload and internally verify the actual approved list before permit preparation. <button type="button" class="link-btn" data-action="open-cdc-library">Open master lists →</button></div>` : `<div class="sample-callout">Linked master list: ${e(cdcList.qip)} · ${e(cdcList.cycleYear)} · ${e(cdcList.fileName)}</div>`}
      ${!sourcesAttached ? `<div class="alert"><strong>Supplier files needed</strong>Attach the original invoice and packing list before preparing the application.</div>` : ""}
      ${pendingReviewCount(r) ? `<div class="alert"><strong>${pendingReviewCount(r)} item lines still need review</strong>Confirm item descriptions and quantities before the reviewed PDF. <button type="button" class="link-btn" data-action="review-items">Review items →</button></div>` : ""}
      <div class="review-list">${items.map(([key, label]) => `<label class="review-item checkline"><input type="checkbox" data-permit-check="${key}" ${checks[key] ? "checked" : ""}/><span>${label}</span></label>`).join("")}</div>
    </section>
  </div><aside class="detail-stack">
    <section class="card card-pad"><h2 class="section-title">Export</h2><p class="section-help">Excel is the editable application draft. PDF is a fixed copy for review or printing.</p>
      <div class="button-row"><button class="btn primary" type="button" data-action="demo-permit-export" ${draftReady ? "" : "disabled"}>Generate draft XLSX</button><button class="btn" type="button" data-action="demo-permit-pdf" ${ready ? "" : "disabled"}>Reviewed PDF</button></div>
      <div class="inline-status">${ready ? "Checks complete · ready for reviewed copy" : draftReady ? "Draft available · unresolved reviews stay flagged" : "Check source documents and dates before generating the draft."}</div>
    </section>
    <div class="alert"><strong>Template check</strong>Confirm dates and references from the current shipment. Do not carry old values forward from a previous workbook.</div>
  </aside></div>`;
}
function spreadsheetView(sheet) {
  const cols = sheet.cols || 8;
  const colName = index => window.XLSX?.utils?.encode_col(index) || String.fromCharCode(65 + index);
  return `<div class="spreadsheet-scroll"><table class="sheet-grid"><thead><tr><th class="row-number"></th>${Array.from({length:cols}, (_,i) => `<th>${colName(i)}</th>`).join("")}</tr></thead><tbody>${sheet.rows.map((row, ri) => `<tr><th class="row-number">${ri + 1}</th>${Array.from({length:cols}, (_,ci) => `<td class="${row[ci] !== "" && row[ci] != null ? "filled" : ""}">${e(row[ci] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
async function prepareAttachment(file) {
  const ext = file.name.split(".").pop().toLowerCase();
  if (["xlsx", "xls", "csv"].includes(ext)) {
    if (!window.XLSX) throw new Error("Excel reader is unavailable.");
    const workbook = window.XLSX.read(await file.arrayBuffer());
    const sheets = workbook.SheetNames.map(name => {
      const ws = workbook.Sheets[name];
      const range = window.XLSX.utils.decode_range(ws["!ref"] || "A1");
      const cols = Math.min(Math.max(range.e.c + 1, 8), 18);
      const rowCount = Math.min(Math.max(range.e.r + 1, 12), 80);
      const rows = Array.from({length:rowCount}, (_,ri) =>
        Array.from({length:cols}, (_,ci) => {
          const cell = ws[window.XLSX.utils.encode_cell({r:ri,c:ci})];
          return cell ? String(cell.w ?? cell.v ?? (cell.f ? "=" + cell.f : "")) : "";
        })
      );
      return {name, cols, rows};
    });
    return {name:file.name, type:"sheet", sheets, sheetIndex:0};
  }
  if (ext === "pdf") return {name:file.name, type:"pdf", url:URL.createObjectURL(file)};
  if (["png", "jpg", "jpeg", "webp"].includes(ext)) return {name:file.name, type:"image", url:URL.createObjectURL(file)};
  throw new Error("Choose an Excel, PDF, or image file.");
}
function originalPreview(attachment) {
  if (!attachment) return `<div class="source-empty"><div class="doc-icon-large">▤</div><strong>No original file attached</strong><span>Attach the supplier invoice or packing list to compare it with the saved details.</span></div>`;
  if (attachment.type === "pdf") return `<iframe class="file-preview" src="${e(attachment.url)}" title="${e(attachment.name)}"></iframe>`;
  if (attachment.type === "image") return `<img class="image-preview" src="${e(attachment.url)}" alt="${e(attachment.name)}" />`;
  return spreadsheetView(attachment.sheets[attachment.sheetIndex] || attachment.sheets[0]);
}
function releaseAttachment(attachment) {
  if (attachment?.url) URL.revokeObjectURL(attachment.url);
}
function syncExtractedDraft() {
  const data = window.importExtractor.extract(state.wizardAttachments);
  state.sampleFlow = false;
  state.extractedData = data;
  state.extracted = !!(data.invoiceSheet || data.packingSheet);
  if (!state.extracted) return;
  state.invoice = data.invoiceNo || "";
  state.invoiceDate = data.invoiceDate || "";
  state.supplier = data.supplier || "";
  state.company = data.company || state.company;
  state.origin = data.origin || "";
  state.destination = data.destination || "";
  state.total = data.amount == null ? "" : String(data.amount);
  state.packages = data.packages == null ? "" : String(data.packages);
  state.weight = data.grossWeight == null ? "" : String(data.grossWeight);
  state.currency = data.currency;
  if (state.wizardAttachments.invoice?.type === "sheet") {
    const index = state.wizardAttachments.invoice.sheets.findIndex(sheet => sheet.name === data.invoiceSheet);
    if (index >= 0) state.wizardAttachments.invoice.sheetIndex = index;
  }
  if (state.wizardAttachments.packing?.type === "sheet") {
    const index = state.wizardAttachments.packing.sheets.findIndex(sheet => sheet.name === data.packingSheet);
    if (index >= 0) state.wizardAttachments.packing.sheetIndex = index;
  }
  if (data.packingSheet && !state.wizardAttachments.packing) state.packingFile = state.invoiceFile;
  if (!data.packingSheet && !state.wizardAttachments.packing) state.packingFile = "";
}
function documentWorkspace(r, kind) {
  const invoice = kind === "invoice";
  const title = invoice ? "Supplier invoice" : "Packing list";
  const attachment = state.attachments[r.id]?.[kind];
  const original = state.documentMode === "original";
  const data = r.extracted;
  const fields = invoice
    ? [["Invoice number", r.invoice], ["Invoice date", r.invoiceDate], ["Supplier", r.supplier], ["Consignee", r.company], ["Origin", r.origin], ["Destination", r.destination], ["Invoice amount", money(r.amount, r.currency)]]
    : [["Packages", r.packages], ["Item lines", data?.packingLines?.length], ["Gross weight", shown(r.grossWeight, " kg")], ["Net weight", shown(r.netWeight, " kg")], ["Volume", shown(r.volume, " m³")], ["Supplier", r.supplier]];
  const lines = invoice ? data?.invoiceLines : data?.packingLines;
  const lineTable = lines?.length ? `<div class="table-scroll"><table class="mini-table"><thead><tr><th>HS code</th><th>Supplier description</th><th>Quantity</th>${invoice ? "<th>Unit price</th><th>Subtotal</th>" : "<th>Packages</th><th>Gross kg</th><th>Net kg</th><th>m³</th>"}</tr></thead><tbody>${lines.map(line => `<tr><td>${e(line.hsCode)}</td><td><strong>${e(line.chinese || "—")}</strong><small>${e(line.english || "—")}</small></td><td>${e(shown(line.quantity))} ${e(line.unit)}</td>${invoice ? `<td>${e(money(line.unitPrice, r.currency))}</td><td>${e(money(line.amount, r.currency))}</td>` : `<td>${e(shown(line.packages))}</td><td>${e(shown(line.grossWeight))}</td><td>${e(shown(line.netWeight))}</td><td>${e(shown(line.volume))}</td>`}</tr>`).join("")}</tbody></table></div>` : `<div class="empty-state">No item lines saved yet. Upload the supplier workbook or add details manually.</div>`;
  return `<div class="detail-grid document-workspace">
    <section class="card card-pad source-pane">
      <div class="pane-heading"><div><h2 class="section-title">${title}</h2><div class="muted-note">Supplier values recorded for this import · reviewed corrections are in ${e(itemTab(r))}</div></div>${badge(attachment ? "Source attached" : "No source", attachment ? "" : "gray")}</div>
      <div class="source-controls">
        <div class="view-tabs"><button class="${original ? "" : "active"}" type="button" data-document-mode="details">Details</button><button class="${original ? "active" : ""}" type="button" data-document-mode="original">View original</button></div>
        <label class="btn small file-upload-control">Attach source<input type="file" data-detail-upload="${kind}" accept=".xls,.xlsx,.csv,.pdf,.png,.jpg,.jpeg,.webp" /></label>
      </div>
      ${state.uploadError ? `<div class="alert" style="margin-bottom:12px">${e(state.uploadError)}</div>` : ""}
      ${original ? `<div class="source-canvas ${attachment ? "sheet-host" : ""}">${originalPreview(attachment)}</div>` : `<div class="record-content">${r.sample ? `<div class="sample-callout sample-data-note">Sample values for this fictional import.${attachment ? " The attached file has not replaced these values." : " No supplier file is attached."}</div>` : ""}<div class="kv-grid">${fields.map(([label,value]) => `<div class="kv"><span>${e(label)}</span><strong>${e(shown(value))}</strong></div>`).join("")}</div><h3>Item lines</h3>${lineTable}</div>`}
      ${original && attachment?.type === "sheet" && attachment.sheets.length > 1 ? `<div class="workbook-tabs">${attachment.sheets.map((sheet,i) => `<button type="button" class="${i === attachment.sheetIndex ? "active" : ""}" data-sheet-index="${i}">${e(sheet.name)}</button>`).join("")}</div>` : ""}
      <div class="viewer-note">${original ? "Source preview stays in this browser session." : "The original supplier file is available through View original when attached."}</div>
    </section>
    <aside class="card card-pad review-pane">
      <div><div class="eyebrow">Document review</div><h2 class="section-title">Checks & source</h2><p class="section-help">Review the saved values against the supplier file before permit use.</p></div>
      <div class="kv-grid"><div class="kv"><span>Source file</span><strong>${e(attachment?.name || "Not attached")}</strong></div><div class="kv"><span>Item lines</span><strong>${e(shown(lines?.length))}</strong></div></div>
      ${data?.issues.length ? `<div class="alert"><strong>Source findings</strong>${data.issues.map(issue => `<div>• ${e(issue)}</div>`).join("")}</div>` : r.sample ? `<div class="sample-callout">Sample lines align between invoice and packing list. They have not been checked against a supplier document.</div>` : `<div class="sample-callout">No automated cross-document differences recorded. Confirm item descriptions and specifications.</div>`}
      <div class="review-bottom">${pendingReviewCount(r) ? badge(`${pendingReviewCount(r)} items pending`, "amber") : badge("Items confirmed")}
        <div class="button-row" style="margin-top:14px">${button("Review items →", "review-items", "primary")}</div>
      </div>
    </aside>
  </div>`;
}
function itemReviewContent(record) {
  const lines = invoiceItems(record);
  const pending = pendingReviewCount(record);
  const confirmed = lines.length - pending;
  const list = record.type === "CDC" ? linkedCdcList(record) : null;
  return `<div class="item-review-page">
    <section class="card card-pad item-review-head">
      <div><div class="eyebrow">Item reconciliation</div><h2 class="section-title">Review invoice and packing lines</h2><p class="section-help">Confirm each item after checking its description, quantity and unit. Supplier values remain visible as evidence.</p></div>
      ${button("+ Add item", "review-add", "small")}
    </section>
    <div class="review-metrics"><div class="card"><strong>${lines.length}</strong><span>Invoice lines</span></div><div class="card"><strong>${confirmed}</strong><span>Confirmed</span></div><div class="card"><strong>${pending}</strong><span>Still to review</span></div></div>
    ${record.sample ? `<div class="sample-callout">These are fictional sample lines. Review decisions in this demo do not approve a supplier document.</div>` : ""}
    ${record.extracted?.issues?.length ? `<div class="alert"><strong>Document findings</strong>${record.extracted.issues.map(issue => `<div>• ${e(issue)}</div>`).join("")}</div>` : ""}
    <section class="card item-table-card"><div class="item-table-title"><strong>Shipping items</strong><span>Click a line to compare invoice and packing values</span></div>
      ${lines.length ? `<div class="table-scroll"><table class="item-review-table"><thead><tr><th>#</th><th>Supplier item</th><th>Invoice qty</th><th>Packing qty / packages</th><th>Reviewed value</th><th>Check</th><th>Review</th></tr></thead><tbody>
      ${lines.map((item,index) => { const pack = record.extracted?.packingLines?.[index]; const review = reviewAt(record,index); const differences = lineDifferences(record,index); return `<tr data-review-row="${index}" tabindex="0" role="button" aria-label="Review item ${index + 1}"><td>${index + 1}</td><td><strong>${e(item.english || item.chinese || "Unnamed item")}</strong><small>${e(item.chinese || "No Chinese name")} · ${e(item.hsCode || "No HS code")}</small></td><td>${e(shown(item.quantity))} ${e(item.unit)}</td><td>${pack ? `${e(shown(pack.quantity))} ${e(pack.unit)}<small>${e(shown(pack.packages))} packages</small>` : "—"}</td><td>${record.reviews?.[index] ? `<strong>${e(review.description)}</strong><small>${e(shown(review.quantity))} ${e(review.unit)} · ${e(shown(review.hsCode))}</small>` : "—"}</td><td>${differences.length ? badge(`${differences.length} to check`,"amber") : badge("Aligned")}</td><td>${reviewBadge(review.status)}</td></tr>`; }).join("")}</tbody></table></div>` : `<div class="empty-state">No items yet. Add the first item or attach a supplier workbook in Invoice.</div>`}
    </section>
    ${record.type === "CDC" ? `<section class="card card-pad cdc-prerequisite"><div><h2 class="section-title">CDC master-list matching</h2><p class="section-help">${list ? `Linked to ${e(list.company)} · ${e(list.qip)} · ${e(list.cycleYear)}. ${lines.filter(item => cdcCandidate(list,item)).length} of ${lines.length} supplier descriptions have exact text candidates.` : "A verified company list must be linked before CDC candidates can be shown."}</p><div class="inline-status">Candidates require human checks of company, specification, unit and balance. No stock is deducted.</div></div>${!list ? button(activeCdcList(record.company,record.importYear) ? "Link verified list" : "Set up master list", activeCdcList(record.company,record.importYear) ? "link-cdc-list" : "open-cdc-library") : badge("List linked")}</section>` : ""}
  </div>`;
}
function openItemReview(record, index) {
  const item = invoiceItems(record)[index] || {};
  const pack = record.extracted?.packingLines?.[index] || {};
  const saved = reviewAt(record,index);
  state.reviewIndex = index;
  state.reviewError = "";
  state.reviewDraft = {
    status: saved.status || "pending", description: saved.description || item.english || "",
    quantity: String(saved.quantity || item.quantity || ""), unit: saved.unit || item.unit || "",
    hsCode: saved.hsCode || item.hsCode || "", chinese: item.chinese || "",
    packingQuantity: String(pack.quantity ?? ""), packages: String(pack.packages ?? ""),
    unitPrice: String(item.unitPrice ?? ""), note: saved.note || ""
  };
  render();
}
function reviewField(label, key, value, type = "text") {
  return `<label class="review-field"><span>${e(label)}</span><input type="${type}" data-review-field="${key}" value="${e(value)}" /></label>`;
}
function reviewDrawer(record) {
  if (state.reviewIndex === null || state.detailTab !== itemTab(record)) return "";
  const index = state.reviewIndex;
  const isNew = index >= invoiceItems(record).length;
  const invoice = invoiceItems(record)[index] || {};
  const packing = record.extracted?.packingLines?.[index] || {};
  const list = record.type === "CDC" ? linkedCdcList(record) : null;
  const candidate = cdcCandidate(list,invoice);
  const draft = state.reviewDraft || {};
  const checks = isNew ? [] : lineDifferences(record,index);
  return `<div class="drawer-backdrop" data-action="review-close"></div><aside class="review-drawer" role="dialog" aria-modal="true" aria-label="Review item ${index + 1}">
    <div class="drawer-head"><div><div class="eyebrow">${isNew ? "New item" : `Item ${index + 1} of ${invoiceItems(record).length}`}</div><h2>${isNew ? "Add shipping item" : e(invoice.english || invoice.chinese || "Review item")}</h2></div><button type="button" class="drawer-close" data-action="review-close" aria-label="Close review">×</button></div>
    <div class="drawer-scroll">
      ${record.sample ? `<div class="sample-callout">Fictional sample values for the UX demo.</div>` : ""}
      ${!isNew ? `<div class="compare-grid"><div class="compare-card"><h3>Supplier invoice</h3><dl><dt>Chinese</dt><dd>${e(shown(invoice.chinese))}</dd><dt>English</dt><dd>${e(shown(invoice.english))}</dd><dt>HS code</dt><dd>${e(shown(invoice.hsCode))}</dd><dt>Quantity</dt><dd>${e(shown(invoice.quantity))} ${e(invoice.unit || "")}</dd><dt>Unit price</dt><dd>${e(money(invoice.unitPrice,record.currency))}</dd></dl></div><div class="compare-card"><h3>Supplier packing list</h3><dl><dt>Chinese</dt><dd>${e(shown(packing.chinese))}</dd><dt>Quantity</dt><dd>${e(shown(packing.quantity))} ${e(packing.unit || "")}</dd><dt>Packages</dt><dd>${e(shown(packing.packages))}</dd><dt>Gross / net</dt><dd>${e(shown(packing.grossWeight))} / ${e(shown(packing.netWeight))} kg</dd></dl></div></div>` : ""}
      ${record.type === "CDC" ? `<div class="cdc-candidate"><strong>${list?.demo ? "Fictional CDC candidate" : "CDC master-list candidate"}</strong>${!list ? `<p>No verified list linked to this shipment.</p>` : candidate ? `<p>${e(candidate.description)} · ${e(candidate.unit)} · approved ${e(shown(candidate.approved))} · source remaining ${e(shown(candidate.remaining))}</p><small>Exact text candidate only. Confirm specification, unit and eligibility separately.</small>` : `<p>No exact text candidate found in the linked list.</p>`}</div>` : ""}
      ${checks.length ? `<div class="alert"><strong>Check this line</strong>${checks.map(check => `<div>• ${e(check)}</div>`).join("")}</div>` : !isNew ? `<div class="sample-callout">Invoice and packing identifiers and quantities align for this line.</div>` : ""}
      <h3 class="drawer-section-title">${isNew ? "Enter item details" : "Reviewed values"}</h3>
      <div class="review-form">${isNew ? reviewField("Chinese description", "chinese", draft.chinese) : ""}${reviewField("English description", "description", draft.description)}${reviewField("HS code", "hsCode", draft.hsCode)}${reviewField("Quantity", "quantity", draft.quantity, "number")}${reviewField("Unit", "unit", draft.unit)}${isNew ? `${reviewField("Packing quantity", "packingQuantity", draft.packingQuantity,"number")}${reviewField("Packages", "packages", draft.packages,"number")}${reviewField("Unit price", "unitPrice", draft.unitPrice,"number")}` : ""}
        <label class="review-field"><span>Review result</span><select data-review-field="status"><option value="pending" ${draft.status === "pending" ? "selected" : ""}>Pending</option><option value="confirmed" ${draft.status === "confirmed" ? "selected" : ""}>Confirmed</option><option value="followup" ${draft.status === "followup" ? "selected" : ""}>Ask supplier / follow up</option></select></label>
        <label class="review-field wide"><span>Reviewer note</span><textarea data-review-field="note" rows="3" placeholder="What did you verify or ask the supplier?">${e(draft.note)}</textarea></label>
      </div>
      ${state.reviewError ? `<div class="alert">${e(state.reviewError)}</div>` : ""}
      <p class="drawer-help">Saving a reviewed value does not change the supplier invoice or packing list.</p>
    </div>
    <div class="drawer-actions">${button("Cancel", "review-close")}${button(isNew ? "Add item" : "Save review", "review-save", "primary")}</div>
  </aside>`;
}
function detailContent(r) {
  switch (state.detailTab) {
    case "Overview": return `<div class="detail-grid"><div class="detail-stack">
      <section class="card card-pad"><h2 class="section-title">Shipment overview</h2><div class="kv-grid"><div class="kv"><span>Company</span><strong>${e(r.company)}</strong></div><div class="kv"><span>Supplier</span><strong>${e(r.supplier)}</strong></div><div class="kv"><span>Invoice</span><strong>${e(shown(r.invoice))}</strong></div><div class="kv"><span>Invoice date</span><strong>${e(shown(r.invoiceDate))}</strong></div><div class="kv"><span>Origin → destination</span><strong>${e(shown(r.origin))} → ${e(shown(r.destination))}</strong></div><div class="kv"><span>Invoice amount</span><strong>${e(money(r.amount,r.currency))}</strong></div><div class="kv"><span>Packages</span><strong>${e(shown(r.packages))}</strong></div><div class="kv"><span>Gross / net</span><strong>${e(shown(r.grossWeight))} / ${e(shown(r.netWeight))} kg</strong></div><div class="kv"><span>HBL</span><strong>${e(r.hbl || "Not added")}</strong></div><div class="kv"><span>Port ETA</span><strong>${e(r.eta || "Not added")}</strong></div><div class="kv"><span>Container</span><strong>${e(r.container || "Not added")}</strong></div></div></section>
      <section class="card card-pad"><h2 class="section-title">Documents in this import</h2>${docRow("Supplier invoice",r.invoiceFile || (r.sample ? "Sample values; no file" : r.entryMethod === "manual entry" ? "Entered manually" : "Not attached"),r.invoiceFile ? "Attached" : r.sample ? "Sample" : "Pending",r.invoiceFile ? "" : "gray")}${docRow("Packing list",r.packingFile || (r.sample ? "Sample values; no file" : r.entryMethod === "manual entry" ? "Entered manually" : "Not attached"),r.packingFile ? "Attached" : r.sample ? "Sample" : "Pending",r.packingFile ? "" : "gray")}${docRow("House bill of lading",r.hbl || "Add when received",r.hbl ? "Recorded" : "Pending",r.hbl ? "" : "amber")}${r.type === "CDC" ? docRow("CDC permit","Company master list and permit","Review","amber") : ""}</section>
    </div><div class="detail-stack"><section class="card card-pad"><h2 class="section-title">Record status</h2><p class="section-help">Created from ${e(r.entryMethod || "document upload")}. Review status stays visible on every section.</p>${badge(r.status,r.status === "Needs review" ? "amber" : "")}<div class="inline-status">Open a tab to see each document and its extracted data.</div></section><section class="card card-pad"><h2 class="section-title">Next documents</h2><p class="section-help">Add HBL, arrival notice, delivery order and customs release as they arrive.</p>${button("+ Add document","demo-add-document")}</section></div></div>`;
    case "Invoice": return documentWorkspace(r, "invoice");
    case "Packing list": return documentWorkspace(r, "packing");
    case "Items":
      return itemReviewContent(r);
    case "Items & CDC": return itemReviewContent(r);
    case "Permit application": return permitContent(r);
    case "Shipping docs": return `<div class="detail-grid"><section class="card card-pad"><h2 class="section-title">Shipping documents</h2>${docRow("House bill of lading",r.hbl || "Awaiting forwarder",r.hbl ? "Recorded" : "Pending",r.hbl ? "" : "amber")}${docRow("Arrival notice","Add when received","Pending","amber")}${docRow("Certificate of origin","If required","Pending","gray")}</section><aside class="card card-pad"><h2 class="section-title">Forwarder</h2><p class="section-help">Vessel, HBL and arrival information can be added when confirmed.</p></aside></div>`;
    case "Customs": return `<div class="detail-grid"><section class="card card-pad"><h2 class="section-title">Customs & release</h2>${docRow("Delivery order (D/O)","From shipping agent","Pending","amber")}${docRow("Customs declaration","Broker entry","Pending","amber")}${docRow("Customs release","After clearance","Pending","gray")}</section><aside class="card card-pad"><h2 class="section-title">Important</h2><p class="section-help">Recorded documents and status are for tracking. This demo does not submit to customs.</p></aside></div>`;
    case "Transport": return `<div class="detail-grid"><section class="card card-pad"><h2 class="section-title">Transport & delivery</h2><div class="kv-grid"><div class="kv"><span>Origin</span><strong>Ho Chi Minh City</strong></div><div class="kv"><span>Destination port</span><strong>Sihanoukville</strong></div><div class="kv"><span>Container</span><strong>${e(r.container || "Not added")}</strong></div><div class="kv"><span>Factory receipt</span><strong>Not confirmed</strong></div></div></section><aside class="card card-pad"><h2 class="section-title">Delivery proof</h2><p class="section-help">Record actual truck departure and factory receipt separately from planned dates.</p></aside></div>`;
    case "Costs": return `<div class="detail-grid"><section class="card card-pad"><h2 class="section-title">Costs</h2><div class="empty-state">Add forwarder charges, customs fees and trucking costs as documents arrive.</div></section><aside class="card card-pad"><h2 class="section-title">Estimate vs actual</h2><p class="section-help">Keep estimates separate from confirmed invoices.</p></aside></div>`;
  }
}

function saveItemReview() {
  const record = selectedRecord();
  const index = state.reviewIndex;
  const draft = state.reviewDraft;
  if (index === null || !draft) return;
  const isNew = index >= invoiceItems(record).length;
  const quantity = Number(draft.quantity);
  if (!draft.description.trim() || !draft.unit.trim() || !Number.isFinite(quantity) || quantity <= 0) {
    state.reviewError = "Enter an English description, unit and quantity greater than zero.";
    render(); return;
  }
  const packingQuantity = isNew ? Number(draft.packingQuantity || draft.quantity) : record.extracted?.packingLines?.[index]?.quantity;
  if (isNew && (!Number.isFinite(packingQuantity) || packingQuantity <= 0)) {
    state.reviewError = "Enter a packing quantity greater than zero.";
    render(); return;
  }
  const mismatch = isNew ? packingQuantity !== quantity : lineDifferences(record,index).length > 0;
  if ((draft.status === "confirmed" && mismatch || draft.status === "followup") && !draft.note.trim()) {
    state.reviewError = "Add a reviewer note explaining this difference or follow-up.";
    render(); return;
  }
  if (!record.extracted) record.extracted = { invoiceLines: [], packingLines: [], issues: [] };
  if (isNew) {
    const unitPrice = draft.unitPrice === "" ? null : Number(draft.unitPrice);
    const packages = draft.packages === "" ? null : Number(draft.packages);
    record.extracted.invoiceLines.push({ hsCode: draft.hsCode.trim(), chinese: draft.chinese.trim(), english: draft.description.trim(), quantity, unit: draft.unit.trim(), unitPrice, amount: unitPrice === null || !Number.isFinite(unitPrice) ? null : unitPrice * quantity });
    record.extracted.packingLines.push({ hsCode: draft.hsCode.trim(), chinese: draft.chinese.trim(), english: draft.description.trim(), quantity: packingQuantity, unit: draft.unit.trim(), packages: packages === null || !Number.isFinite(packages) ? null : packages, grossWeight: null, netWeight: null, volume: null });
  }
  if (!record.reviews) record.reviews = [];
  record.reviews[index] = { status: draft.status, description: draft.description.trim(), quantity, unit: draft.unit.trim(), hsCode: draft.hsCode.trim(), note: draft.note.trim() };
  state.reviewIndex = null; state.reviewDraft = null; state.reviewError = "";
  render();
}

document.addEventListener("click", event => {
  const nav = event.target.closest("[data-nav]");
  if (nav) { if (nav.dataset.nav === "cdc") openCdcLibrary("register"); else { state.screen = "register"; state.reviewIndex = null; render(); } return; }
  const cdcYear = event.target.closest("[data-cdc-year]");
  if (cdcYear) { state.cdcYear = cdcYear.dataset.cdcYear; state.cdcSearch = ""; render(); return; }
  const row = event.target.closest("[data-open]");
  if (row) { state.selectedId = row.dataset.open; state.detailTab = "Overview"; state.reviewIndex = null; state.screen = "detail"; render(); return; }
  const registerFilter = event.target.closest("[data-register-filter]");
  if (registerFilter) { state.quickFilter = registerFilter.dataset.registerFilter; render(); return; }
  const reviewRow = event.target.closest("[data-review-row]");
  if (reviewRow) { openItemReview(selectedRecord(), Number(reviewRow.dataset.reviewRow)); return; }
  const tab = event.target.closest("[data-tab]");
  if (tab) {
    state.detailTab = tab.dataset.tab;
    state.reviewIndex = null; state.reviewDraft = null;
    state.documentMode = "details";
    state.uploadError = "";
    render(); return;
  }
  const documentMode = event.target.closest("[data-document-mode]");
  if (documentMode) { state.documentMode = documentMode.dataset.documentMode; state.uploadError = ""; render(); return; }
  const sheetTab = event.target.closest("[data-sheet-index]");
  if (sheetTab) {
    const attachment = state.attachments[state.selectedId]?.[state.detailTab === "Invoice" ? "invoice" : "packing"];
    if (attachment?.type === "sheet") attachment.sheetIndex = Number(sheetTab.dataset.sheetIndex);
    render(); return;
  }
  const choice = event.target.closest("[data-choice]");
  if (choice) { const [group, value] = choice.dataset.choice.split(":"); if (group === "method") state.method = value; else state.importType = value; render(); return; }
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (!action) return;
  if (action === "open-cdc-library") return openCdcLibrary();
  if (action === "return-cdc") { state.screen = state.cdcReturn; render(); return; }
  if (action === "toggle-cdc-upload") { state.cdcUploadOpen = !state.cdcUploadOpen; state.cdcDraft.company = state.workspaceCompany; state.cdcDraft.cycleYear = state.cdcYear; render(); return; }
  if (action === "link-cdc-list") {
    const record = selectedRecord();
    const list = activeCdcList(record.company,record.importYear);
    if (record.type === "CDC" && list) record.cdcListId = list.id;
    render(); return;
  }
  if (action === "verify-cdc") {
    const issues = cdcDraftIssues();
    if (issues.length) { state.cdcDraft.error = issues.join(" "); render(); return; }
    const draft = state.cdcDraft;
    const id = `CDC-${window.cdcMasterReader.companyKey(draft.company)}-${draft.cycleYear}-${state.cdcLists.length + 1}`;
    state.cdcLists.push({ id, company: draft.company, cycleYear: String(draft.cycleYear), validFrom: draft.validFrom, validTo: draft.validTo,
      qip: draft.qip.trim(), approvalReference: draft.approvalReference.trim(), approvalFile: draft.approvalFile,
      fileName: draft.fileName, layout: draft.parsed.layout, itemCount: draft.parsed.itemCount,
      items: draft.parsed.items.map(item => ({...item})), status: "verified", demo: false });
    state.cdcYear = String(draft.cycleYear);
    state.cdcUploadOpen = false;
    state.cdcNotice = "Version marked internally verified in this demo. Existing imports remain on their previous version until linked explicitly.";
    state.cdcDraft = { company: state.workspaceCompany, cycleYear: state.cdcYear, validFrom: "", validTo: "", qip: "", approvalReference: "", approvalFile: "", fileName: "", parsed: null, acknowledged: false, error: "" };
    render(); return;
  }
  if (action === "review-items") { state.detailTab = itemTab(selectedRecord()); state.reviewIndex = null; render(); return; }
  if (action === "review-add") { openItemReview(selectedRecord(), invoiceItems(selectedRecord()).length); return; }
  if (action === "review-close") { state.reviewIndex = null; state.reviewDraft = null; state.reviewError = ""; render(); return; }
  if (action === "review-save") return saveItemReview();
  if (action === "new-import") return resetWizard();
  if (action === "import-excel") { resetWizard(); state.wizardStep = 1; render(); return; }
  if (action === "back-register") { state.screen = "register"; state.reviewIndex = null; render(); return; }
  if (action === "previous") { state.wizardStep = Math.max(0, state.wizardStep - 1); state.error = ""; render(); return; }
  if (action === "sample-docs") {
    Object.values(state.wizardAttachments).forEach(releaseAttachment);
    const sample = sampleDetails["TG-26018"];
    state.wizardAttachments = {}; state.invoiceFile = ""; state.packingFile = "";
    state.sampleFlow = true; state.extracted = true;
    state.invoice = "DEMO-IM-026"; state.invoiceDate = sample.invoiceDate;
    state.company = "Tonle Garment Co."; state.supplier = "Eastline Machines";
    state.origin = sample.origin; state.destination = sample.destination;
    state.total = String(sample.amount); state.packages = String(sample.packages);
    state.weight = String(sample.grossWeight); state.currency = sample.currency;
    state.extractedData = { invoiceNo: state.invoice, invoiceDate: sample.invoiceDate, supplier: state.supplier, company: state.company,
      origin: sample.origin, destination: sample.destination, amount: sample.amount, currency: sample.currency,
      packages: sample.packages, grossWeight: sample.grossWeight, netWeight: sample.netWeight, volume: sample.volume,
      invoiceSheet: "", packingSheet: "", invoiceLines: sample.invoiceLines.map(line => ({...line})), packingLines: sample.packingLines.map(line => ({...line})), issues: [] };
    state.error = ""; render(); return;
  }
  if (action === "next") {
    if (state.wizardStep === 1 && state.method === "upload" && !state.extracted) { state.error = "Upload an Excel invoice or use the sample review flow before continuing."; render(); return; }
    if (state.wizardStep === 1 && state.method === "manual" && (!state.supplier.trim() || !state.invoice.trim())) { state.error = "Enter a supplier and invoice number to continue."; render(); return; }
    state.wizardStep = Math.min(2, state.wizardStep + 1); state.error = ""; render(); return;
  }
  if (action === "create-record") {
    const unresolved = state.method === "manual" ? !state.manualChecked : state.sampleFlow || !state.extractedData || state.extractedData.issues.length > 0 || !state.invoice.trim();
    const invoiceRef = state.invoice.trim() || `DRAFT-${state.records.length + 1}`;
    let id = invoiceRef;
    for (let suffix = 2; state.records.some(r => r.id === id); suffix++) id = `${invoiceRef}-${suffix}`;
    const attachedCount = Number(!!state.extractedData?.invoiceSheet) + Number(!!state.extractedData?.packingSheet);
    const record = { id, invoice: state.invoice, company: state.company, supplier: state.supplier, type: state.importType, importYear: state.importYear, cdcListId: state.importType === "CDC" ? activeCdcList(state.company,state.importYear)?.id || null : null, hbl: "", container: "", eta: "", status: "Draft", reviewWarning: unresolved, reviews: [], docs: `${attachedCount} of 5`, invoiceFile: state.invoiceFile, packingFile: state.packingFile, entryMethod: state.sampleFlow ? "sample data" : state.method === "upload" ? "document upload" : "manual entry", sample: state.sampleFlow, invoiceDate: state.invoiceDate, amount: state.total ? Number(String(state.total).replace(/[^0-9.\-]/g,"")) : null, currency: state.currency || "USD", total: state.total, packages: state.packages, grossWeight: state.weight, netWeight: state.extractedData?.netWeight, volume: state.extractedData?.volume, quantity: state.extractedData?.quantity, origin: state.origin, destination: state.destination, extracted: state.extractedData, weight: state.weight };
    state.records.unshift(record);
    if (Object.keys(state.wizardAttachments).length) {
      state.attachments[id] = { ...state.wizardAttachments };
      if (state.extractedData?.packingSheet && !state.attachments[id].packing && state.wizardAttachments.invoice?.type === "sheet") {
        const sheetIndex = state.wizardAttachments.invoice.sheets.findIndex(sheet => sheet.name === state.extractedData.packingSheet);
        state.attachments[id].packing = { ...state.wizardAttachments.invoice, sheetIndex: Math.max(0,sheetIndex) };
      }
      state.wizardAttachments = {};
    } else delete state.attachments[id];
    state.selectedId = id; state.detailTab = "Overview"; state.screen = "detail"; render(); return;
  }
  if (action.startsWith("demo-")) { window.alert("This control is visual only in the UX demo."); }
});
document.addEventListener("change", async event => {
  const target = event.target;
  if (target.id === "workspace-company") {
    state.workspaceCompany = target.value;
    state.cdcDraft = { company: target.value, cycleYear: "2026", validFrom: "", validTo: "", qip: "", approvalReference: "", approvalFile: "", fileName: "", parsed: null, acknowledged: false, error: "" };
    state.cdcYear = [...state.cdcLists].filter(list => sameCompany(list.company, target.value)).sort((a,b) => b.cycleYear.localeCompare(a.cycleYear))[0]?.cycleYear || "2026";
    state.cdcSearch = "";
    state.cdcUploadOpen = false;
    render(); return;
  }
  if (target.dataset.cdcMasterUpload !== undefined) {
    const file = target.files?.[0]; if (!file) return;
    try { state.cdcDraft.parsed = await window.cdcMasterReader.read(file); state.cdcDraft.fileName = file.name; state.cdcDraft.qip = state.cdcDraft.parsed.qip || ""; state.cdcDraft.error = ""; }
    catch (error) { state.cdcDraft.parsed = null; state.cdcDraft.fileName = ""; state.cdcDraft.error = error.message; }
    render(); return;
  }
  if (target.dataset.cdcApprovalUpload !== undefined) { state.cdcDraft.approvalFile = target.files?.[0]?.name || ""; render(); return; }
  if (target.dataset.cdcField) { state.cdcDraft[target.dataset.cdcField] = target.value; render(); return; }
  if (target.dataset.cdcAck !== undefined) { state.cdcDraft.acknowledged = target.checked; render(); return; }
  if (target.dataset.reviewField) { state.reviewDraft[target.dataset.reviewField] = target.value; return; }
  if (target.dataset.detailUpload) {
    const file = target.files?.[0];
    if (!file) return;
    const kind = target.dataset.detailUpload;
    try {
      const attachment = await prepareAttachment(file);
      const record = selectedRecord();
      const attached = state.attachments[record.id] || {};
      releaseAttachment(attached[kind]);
      attached[kind] = attachment;
      state.attachments[record.id] = attached;
      record[kind === "invoice" ? "invoiceFile" : "packingFile"] = file.name;
      if (attachment.type === "sheet" && window.importExtractor) {
        const data = window.importExtractor.extract(attached);
        const preferredSheet = kind === "invoice" ? data.invoiceSheet : data.packingSheet;
        const preferredIndex = attachment.sheets.findIndex(sheet => sheet.name === preferredSheet);
        if (preferredIndex >= 0) attachment.sheetIndex = preferredIndex;
        if (data.packingSheet && !attached.packing && attachment.type === "sheet") {
          const sheetIndex = attachment.sheets.findIndex(sheet => sheet.name === data.packingSheet);
          attached.packing = { ...attachment, sheetIndex: Math.max(0,sheetIndex) };
        }
        record.extracted = data;
        record.reviews = [];
        record.invoice = data.invoiceNo || record.invoice;
        record.invoiceDate = data.invoiceDate || record.invoiceDate;
        record.supplier = data.supplier || record.supplier;
        record.origin = data.origin || record.origin;
        record.destination = data.destination || record.destination;
        record.amount = data.amount ?? record.amount;
        record.currency = data.currency || record.currency;
        record.quantity = data.quantity ?? record.quantity;
        record.packages = data.packages ?? record.packages;
        record.grossWeight = data.grossWeight ?? record.grossWeight;
        record.netWeight = data.netWeight ?? record.netWeight;
        record.volume = data.volume ?? record.volume;
        record.reviewWarning = data.issues.length > 0;
        record.sample = false;
      }
      state.documentMode = "details";
      state.uploadError = "";
    } catch (error) {
      state.uploadError = `Could not display ${file.name}: ${error.message}`;
    }
    render();
    return;
  }
  if (target.dataset.upload) {
    const file = target.files?.[0];
    if (!file) return;
    const kind = target.dataset.upload;
    try {
      const attachment = await prepareAttachment(file);
      releaseAttachment(state.wizardAttachments[kind]);
      state.wizardAttachments[kind] = attachment;
      state[kind === "invoice" ? "invoiceFile" : "packingFile"] = file.name;
      state.error = "";
      syncExtractedDraft();
    } catch (error) {
      state.error = `Could not display ${file.name}: ${error.message}`;
    }
    render();
    return;
  }
  if (target.dataset.permitCheck) {
    const checks = state.permitChecks[state.selectedId] || {};
    checks[target.dataset.permitCheck] = target.checked;
    state.permitChecks[state.selectedId] = checks;
    render();
    return;
  }
  if (target.dataset.field) { state[target.dataset.field] = target.value; if (["company","importYear"].includes(target.dataset.field)) render(); }
  if (target.dataset.decision) state.decisions[target.dataset.decision] = target.value;
  if (target.id === "manual-check") state.manualChecked = target.checked;
  if (target.id === "stage-filter") { state.statusFilter = target.value; render(); }
});
document.addEventListener("input", event => {
  if (event.target.dataset.reviewField) { state.reviewDraft[event.target.dataset.reviewField] = event.target.value; return; }
  if (event.target.id === "cdc-item-search") { state.cdcSearch = event.target.value; const start = event.target.selectionStart; render(); const input = document.getElementById("cdc-item-search"); input.focus(); input.setSelectionRange(start, start); return; }
  if (event.target.id === "register-search") { state.search = event.target.value; const start = event.target.selectionStart; render(); const input = document.getElementById("register-search"); input.focus(); input.setSelectionRange(start, start); }
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && state.reviewIndex !== null) { state.reviewIndex = null; state.reviewDraft = null; state.reviewError = ""; render(); }
  if (event.key === "Enter" && event.target.closest?.("[data-review-row]")) openItemReview(selectedRecord(), Number(event.target.closest("[data-review-row]").dataset.reviewRow));
});
render();
