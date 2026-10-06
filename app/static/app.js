const DEMO_DOMAINS = [
  "stripe.com",
  "notion.so",
  "figma.com",
  "linear.app",
  "airtable.com",
  "vercel.com",
];

const BUCKET_STYLES = {
  hot: "bg-red-100 text-red-700",
  warm: "bg-amber-100 text-amber-700",
  cold: "bg-slate-100 text-slate-600",
};

const domainsInput = document.getElementById("domains");
const analyzeBtn = document.getElementById("analyzeBtn");
const demoBtn = document.getElementById("demoBtn");
const statusEl = document.getElementById("status");
const resultsBody = document.getElementById("results");
const emptyState = document.getElementById("emptyState");

demoBtn.addEventListener("click", () => {
  domainsInput.value = DEMO_DOMAINS.join("\n");
});

analyzeBtn.addEventListener("click", analyze);

loadExistingLeads();

async function analyze() {
  const domains = domainsInput.value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (domains.length === 0) return;

  setStatus(`Scraping and scoring ${domains.length} lead(s)...`);
  analyzeBtn.disabled = true;

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domains }),
    });
    if (!response.ok) throw new Error("Request failed");
    const leads = await response.json();
    renderLeads(mergeWithExisting(leads));
    setStatus(`Done. ${leads.length} lead(s) scored.`);
  } catch (error) {
    setStatus("Something went wrong. Check the server is running.");
  } finally {
    analyzeBtn.disabled = false;
  }
}

async function loadExistingLeads() {
  try {
    const response = await fetch("/api/leads");
    const leads = await response.json();
    if (leads.length > 0) renderLeads(leads);
  } catch (error) {
    // nothing saved yet, that's fine
  }
}

function mergeWithExisting(newLeads) {
  const existingRows = Array.from(resultsBody.querySelectorAll("tr[data-domain]"));
  const existing = existingRows.map((row) => JSON.parse(row.dataset.lead));
  const byDomain = new Map(existing.map((lead) => [lead.domain, lead]));
  newLeads.forEach((lead) => byDomain.set(lead.domain, lead));
  return Array.from(byDomain.values()).sort((a, b) => b.score - a.score);
}

function renderLeads(leads) {
  resultsBody.innerHTML = "";
  emptyState.classList.toggle("hidden", leads.length > 0);

  for (const lead of leads) {
    const row = document.createElement("tr");
    row.className = "border-t border-slate-100";
    row.dataset.domain = lead.domain;
    row.dataset.lead = JSON.stringify(lead);

    const bucketClass = BUCKET_STYLES[lead.bucket] || BUCKET_STYLES.cold;
    const reasons = lead.reasons.slice(0, 2).join(". ") || "No strong signals found";

    row.innerHTML = `
      <td class="px-4 py-3">
        <div class="font-medium">${escapeHtml(lead.company_name)}</div>
        <div class="text-slate-400 text-xs">${escapeHtml(lead.domain)}${lead.cached ? " · cached" : ""}</div>
      </td>
      <td class="px-4 py-3">
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${bucketClass}">
          ${lead.score} ${lead.bucket}
        </span>
      </td>
      <td class="px-4 py-3 text-slate-600 text-sm">${escapeHtml(reasons)}</td>
    `;
    resultsBody.appendChild(row);
  }
}

function setStatus(message) {
  statusEl.textContent = message;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}
