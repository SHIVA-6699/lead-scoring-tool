const DEMO_DOMAINS = ["stripe.com", "notion.so", "figma.com", "linear.app", "airtable.com", "vercel.com"];

const SIGNAL_LABELS = [
  ["has_careers_page", "Hiring (careers page)"],
  ["has_pricing_page", "Has a pricing page"],
  ["contact_email", "Contact email found"],
  ["has_linkedin", "LinkedIn company page"],
  ["has_blog", "Publishes a blog"],
  ["uses_https", "Uses HTTPS"],
  ["mobile_friendly", "Mobile friendly"],
];

const domainsInput = document.getElementById("domains");
const analyzeBtn = document.getElementById("analyzeBtn");
const demoBtn = document.getElementById("demoBtn");
const exportBtn = document.getElementById("exportBtn");
const statusEl = document.getElementById("status");
const statStack = document.getElementById("statStack");
const ledgerSection = document.getElementById("ledger");
const ledgerCountLabel = document.getElementById("ledgerCountLabel");
const sortSelect = document.getElementById("sortSelect");
const emptyState = document.getElementById("emptyState");
const toastEl = document.getElementById("toast");

let leads = [];
let activeBucket = "all";
let toastTimer = null;

demoBtn.addEventListener("click", () => {
  domainsInput.value = DEMO_DOMAINS.join("\n");
  domainsInput.focus();
});

analyzeBtn.addEventListener("click", analyze);
sortSelect.addEventListener("change", render);

statStack.addEventListener("click", (event) => {
  const row = event.target.closest(".stat-row");
  if (!row) return;
  activeBucket = row.dataset.bucket;
  render();
});

loadExistingLeads();

async function analyze() {
  const domains = domainsInput.value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (domains.length === 0) {
    showToast("Paste at least one website first.", true);
    return;
  }

  analyzeBtn.disabled = true;
  setStatus(`Scanning ${domains.length} website${domains.length > 1 ? "s" : ""}...`);
  showSkeleton(domains.length);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domains }),
    });
    if (!response.ok) throw new Error(await response.text());

    const scored = await response.json();
    mergeLeads(scored);
    setStatus("");
    showToast(`Scored ${scored.length} lead${scored.length > 1 ? "s" : ""}.`);
    render();
  } catch (error) {
    setStatus("");
    showToast("Could not reach the server. Check it is running.", true);
    render();
  } finally {
    analyzeBtn.disabled = false;
  }
}

async function loadExistingLeads() {
  try {
    const response = await fetch("/api/leads");
    const saved = await response.json();
    if (saved.length > 0) {
      leads = saved;
      render();
    }
  } catch (error) {
    // no leads saved yet, nothing to show
  }
}

function mergeLeads(newLeads) {
  const byDomain = new Map(leads.map((lead) => [lead.domain, lead]));
  newLeads.forEach((lead) => byDomain.set(lead.domain, lead));
  leads = Array.from(byDomain.values());
}

function render() {
  const counts = { hot: 0, warm: 0, cold: 0 };
  leads.forEach((lead) => counts[lead.bucket]++);

  document.getElementById("countAll").textContent = leads.length;
  document.getElementById("countHot").textContent = counts.hot;
  document.getElementById("countWarm").textContent = counts.warm;
  document.getElementById("countCold").textContent = counts.cold;

  statStack.querySelectorAll(".stat-row").forEach((row) => {
    row.classList.toggle("is-active", row.dataset.bucket === activeBucket);
  });

  const visible = leads
    .filter((lead) => activeBucket === "all" || lead.bucket === activeBucket)
    .sort((a, b) => (sortSelect.value === "name" ? a.company_name.localeCompare(b.company_name) : b.score - a.score));

  exportBtn.setAttribute("aria-disabled", leads.length === 0 ? "true" : "false");
  if (leads.length === 0) {
    exportBtn.removeAttribute("href");
  } else {
    exportBtn.href = "/api/export";
  }

  if (leads.length === 0) {
    ledgerSection.hidden = true;
    emptyState.hidden = false;
    ledgerCountLabel.textContent = "";
    return;
  }

  emptyState.hidden = true;
  ledgerSection.hidden = false;
  ledgerCountLabel.textContent = `${visible.length} of ${leads.length} shown`;
  ledgerSection.innerHTML = visible.map(renderRow).join("");
}

function renderRow(lead) {
  if (!lead.reachable) {
    return `
      <details class="lead-row" data-bucket="cold">
        <summary>
          <span class="bar"></span>
          <img class="favicon" src="${faviconUrl(lead.domain)}" alt="" />
          <span class="lead-name">
            <span class="company">${escapeHtml(lead.company_name)}</span>
            <span class="domain mono">${escapeHtml(lead.domain)}</span>
          </span>
          <span class="magnitude"><span style="width: 0%"></span></span>
          <span class="score mono">0</span>
          <span class="chevron">&#8250;</span>
        </summary>
        <p class="unreachable-note">Could not reach this website. It may be down, blocking automated requests, or the domain may be incorrect.</p>
      </details>
    `;
  }

  const detailItems = SIGNAL_LABELS.map(([key, label]) => signalItem(Boolean(lead.signals[key]), label));

  const tools = lead.signals.tools_detected || [];
  detailItems.push(signalItem(tools.length > 0, tools.length > 0 ? `Uses ${tools.join(", ")}` : "No sales/marketing tools detected"));

  const employeeCount = lead.signals.employee_count_hint;
  detailItems.push(signalItem(Boolean(employeeCount), employeeCount ? `About ${employeeCount} employees` : "No employee count found"));

  return `
    <details class="lead-row" data-bucket="${lead.bucket}">
      <summary>
        <span class="bar"></span>
        <img class="favicon" src="${faviconUrl(lead.domain)}" alt="" />
        <span class="lead-name">
          <span class="company">${escapeHtml(lead.company_name)}</span>
          <span class="domain mono">${escapeHtml(lead.domain)}${lead.cached ? " (cached)" : ""}</span>
        </span>
        <span class="magnitude"><span style="width: ${lead.score}%"></span></span>
        <span class="score mono">${lead.score}</span>
        <span class="chevron">&#8250;</span>
      </summary>
      <div class="lead-detail">${detailItems.join("")}</div>
    </details>
  `;
}

function signalItem(hit, label) {
  return `
    <span class="signal-item ${hit ? "hit" : ""}">
      <span class="mark">${hit ? "+" : "-"}</span>
      <span>${escapeHtml(label)}</span>
    </span>
  `;
}

function showSkeleton(count) {
  ledgerSection.hidden = false;
  emptyState.hidden = true;
  const rows = Array.from({ length: Math.min(count, 6) })
    .map(
      () => `
      <div class="skeleton-row">
        <span class="skeleton-bar"></span>
        <span></span>
        <span class="skeleton-pill" style="width: 45%"></span>
        <span class="skeleton-pill" style="width: 100%"></span>
        <span></span>
      </div>
    `
    )
    .join("");
  ledgerSection.innerHTML = rows;
}

function faviconUrl(domain) {
  return `https://www.google.com/s2/favicons?sz=64&domain=${encodeURIComponent(domain)}`;
}

function setStatus(message) {
  statusEl.textContent = message;
}

function showToast(message, isError = false) {
  toastEl.textContent = message;
  toastEl.classList.toggle("is-error", isError);
  toastEl.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("is-visible"), 3200);
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}
