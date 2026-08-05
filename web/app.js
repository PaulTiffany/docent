const QUESTIONS = [
  "What can this project do now?",
  "What remains incomplete?",
  "Why was the public demo selected?",
  "Which roadmap did the AI prove is optimal?",
  "What would a mediated runtime unlock?",
  "Does Docent use OmegaClaw?",
];

const state = { config: null, apiBase: "", sessionId: crypto.randomUUID(), projectLoaded: false };
const $ = (selector) => document.querySelector(selector);

function normalizedBase(value) { return (value || "").trim().replace(/\/+$/, ""); }
function endpoint(path) { return `${state.apiBase}${path}`; }
function isPages() { return location.hostname.endsWith("github.io"); }

function setConnection(kind, label, detail) {
  $("#connection-dot").className = `dot ${kind}`;
  $("#connection-label").textContent = label;
  $("#provider-label").textContent = detail;
}

async function loadConfig() {
  try {
    const response = await fetch("./config.json", { cache: "no-store" });
    state.config = response.ok ? await response.json() : {};
  } catch { state.config = {}; }
  const override = localStorage.getItem("docent.publicApiBaseUrl") || "";
  state.apiBase = normalizedBase(override || state.config.api_base_url || (isPages() ? "" : location.origin));
  $("#repository-link").href = state.config.repository_url || "https://github.com/PaulTiffany/docent";
  $("#api-url").value = state.apiBase;
  if (!state.apiBase) {
    $("#setup-panel").classList.remove("hidden");
    setConnection("error", "Setup needed", "No public API URL configured");
    return;
  }
  await checkConnection();
}

async function checkConnection() {
  setConnection("", "Connecting", "Checking public API…");
  try {
    const response = await fetch(endpoint("/api/config/public"));
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const config = await response.json();
    const mode = config.provider === "mock" ? "Deterministic mock mode" : `Provider: ${config.provider}`;
    setConnection("ok", "Ready", mode);
    $("#setup-panel").classList.add("hidden");
  } catch (error) {
    setConnection("error", "Unavailable", `Public API could not be reached · ${error.message}`);
  }
}

function showView(name) {
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `${name}-view`));
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    const active = tab.dataset.view === name;
    tab.classList.toggle("active", active); tab.setAttribute("aria-selected", String(active));
  });
  location.hash = name;
  if (name === "state" && !state.projectLoaded) loadProjectState();
}

function addMessage(role, text, response = null) {
  const article = document.createElement("article"); article.className = `message ${role}`;
  const speaker = document.createElement("span"); speaker.className = "speaker"; speaker.textContent = role === "human" ? "You" : "Docent";
  const body = document.createElement("p"); body.textContent = text; article.append(speaker, body);
  if (response) {
    const evidence = document.createElement("div"); evidence.className = "evidence";
    const badge = document.createElement("span"); badge.className = "badge";
    badge.textContent = response.grounded && response.record_ids.length ? "grounded" : response.limitations.length ? "limited" : "ungrounded";
    const sources = response.retrieval.filter((hit) => response.record_ids.includes(hit.record_id)).map((hit) => `${hit.record_id} — ${hit.title}`);
    evidence.append(badge, document.createTextNode(sources.length ? sources.join(" · ") : "No supporting public record ID"));
    if (response.limitations.length) evidence.append(document.createElement("br"), document.createTextNode(response.limitations.join(" ")));
    article.append(evidence);
  }
  $("#messages").append(article); article.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function sendQuestion(question) {
  if (!state.apiBase) { $("#setup-panel").classList.remove("hidden"); $("#api-dialog").showModal(); return; }
  addMessage("human", question); $("#send-chat").disabled = true; setConnection("", "Sending", "Waiting for one bounded response…");
  try {
    const response = await fetch(endpoint("/api/chat"), { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ session_id: state.sessionId, message: question }) });
    const body = await response.json(); if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`);
    addMessage("docent", body.reply, body); await checkConnection();
  } catch (error) { addMessage("docent", `The public docent is unavailable. ${error.message}`); setConnection("error", "Unavailable", "Check the API URL and CORS origin"); }
  finally { $("#send-chat").disabled = false; }
}

function statusRows(capabilities) {
  return capabilities.map((item) => `<div class="capability-row"><span class="status ${item.status}">${item.status}</span><span><strong>${escapeHtml(item.title)}</strong><br><small>${escapeHtml(item.limitations[0] || item.description)}</small></span></div>`).join("");
}
function escapeHtml(value) { const span = document.createElement("span"); span.textContent = value; return span.innerHTML; }
function pressureHtml(profile) { return Object.entries(profile).filter(([key]) => key !== "authors_note").map(([key,value]) => `<span>${escapeHtml(key.replaceAll("_"," "))}</span><span>${escapeHtml(value)}</span>`).join(""); }
function pathwayCard(assessment, blocked = false) {
  const pathway = assessment.pathway;
  const missing = blocked ? `<p><strong>Missing:</strong> ${escapeHtml(assessment.unsatisfied_preconditions.join("; "))}</p>` : "";
  return `<article class="pathway"><span class="status ${pathway.status}">${escapeHtml(pathway.status)}</span><h3>${escapeHtml(pathway.title)}</h3><p>${escapeHtml(pathway.public_explanation)}</p>${missing}<p><strong>Unlocks:</strong> ${escapeHtml(pathway.pathways_unlocked.join(", ") || "No declared pathway")}</p><div class="pressure">${pressureHtml(pathway.pressure_profile)}</div><p>${escapeHtml(pathway.pressure_profile.authors_note)}</p></article>`;
}

async function loadProjectState() {
  if (!state.apiBase) { $("#state-status").textContent = "Set a public API URL to inspect live project state."; return; }
  try {
    const [capabilities, pathways, frontier, experiments] = await Promise.all(["capabilities","pathways","frontier","experiments"].map(async (resource) => { const r = await fetch(endpoint(`/api/development/${resource}`)); if (!r.ok) throw new Error(`${resource}: HTTP ${r.status}`); return r.json(); }));
    $("#capabilities").innerHTML = statusRows(capabilities);
    const selected = pathways.find((item) => frontier.selected_pathway_ids.includes(item.pathway_id));
    $("#selected-pathway").innerHTML = selected ? `<span class="status">${escapeHtml(selected.status)}</span><h3>${escapeHtml(selected.title)}</h3><p>${escapeHtml(selected.public_explanation)}</p><p><strong>Completion evidence:</strong></p><ul>${selected.completion_evidence.map((item) => `<li>${escapeHtml(item.description)} — ${escapeHtml(item.status)} (${escapeHtml(item.evidence_type)})</li>`).join("")}</ul>` : "No selected pathway.";
    const active = experiments.find((item) => item.status === "active");
    $("#active-experiment").innerHTML = active ? `<p><strong>${escapeHtml(active.title)}</strong></p><p>${escapeHtml(active.hypothesis)}</p><p>Result: ${escapeHtml(active.result_status)}</p>` : "No active experiment.";
    $("#available-pathways").innerHTML = frontier.admissible_pathways.map((item) => pathwayCard(item)).join("");
    $("#blocked-pathways").innerHTML = frontier.blocked_pathways.map((item) => pathwayCard(item,true)).join("");
    $("#state-status").classList.add("hidden"); state.projectLoaded = true;
  } catch (error) { $("#state-status").textContent = `Project state unavailable: ${error.message}`; }
}

document.querySelectorAll(".nav-tab").forEach((tab) => tab.addEventListener("click", () => showView(tab.dataset.view)));
QUESTIONS.forEach((question) => { const button = document.createElement("button"); button.className = "chip"; button.type = "button"; button.textContent = question; button.addEventListener("click", () => sendQuestion(question)); $("#example-questions").append(button); });
$("#chat-form").addEventListener("submit", (event) => { event.preventDefault(); const input = $("#chat-input"); const question = input.value.trim(); if (question) { input.value = ""; sendQuestion(question); } });
$("#reset-chat").addEventListener("click", () => { state.sessionId = crypto.randomUUID(); $("#messages").innerHTML = ""; addMessage("docent", "Local conversation reset. The server retains only bounded recent history for the previous anonymous session ID."); });
$("#configure-api").addEventListener("click", () => $("#api-dialog").showModal());
$("#save-api").addEventListener("click", (event) => { event.preventDefault(); const value = normalizedBase($("#api-url").value); if (value) localStorage.setItem("docent.publicApiBaseUrl", value); else localStorage.removeItem("docent.publicApiBaseUrl"); state.apiBase = value || normalizedBase(state.config.api_base_url || (isPages() ? "" : location.origin)); state.projectLoaded = false; $("#api-dialog").close(); checkConnection(); });
showView(location.hash.slice(1) || "chat"); loadConfig();
