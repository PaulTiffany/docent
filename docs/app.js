const QUESTIONS = [
  "What can this project do now?",
  "What remains incomplete?",
  "Why was the public demo selected?",
  "Which roadmap did the AI prove is optimal?",
  "What would a mediated runtime unlock?",
  "Does Docent use OmegaClaw?",
];

const state = { config: null, serverConfig: null, apiBase: "", sessionId: crypto.randomUUID(), projectLoaded: false, mode: null };
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
    const config = await response.json(); state.serverConfig = config;
    if (!state.mode || !config.enabled_inference_modes.includes(state.mode)) state.mode = config.default_inference_mode;
    const live = config.live_inference_enabled;
    const detail = live ? `Live inference via ${config.provider === "openrouter" ? "OpenRouter" : config.provider} · configured route: ${config.configured_model}` : "Deterministic corpus mode · no model inference";
    setConnection("ok", "Ready", detail); updateModeControls();
    $("#setup-panel").classList.add("hidden");
  } catch (error) {
    setConnection("error", "Unavailable", `Public API could not be reached · ${error.message}`);
  }
}

function updateModeControls() {
  const config = state.serverConfig; if (!config) return;
  const live = state.mode === "live";
  $("#mode-label").textContent = live ? `Live inference · configured route: ${config.configured_model}` : "Deterministic corpus mode · no model inference";
  const alternate = live ? "deterministic" : "live";
  const allowed = config.enabled_inference_modes.includes(alternate);
  $("#toggle-mode").classList.toggle("hidden", !allowed);
  $("#toggle-mode").textContent = live ? "Switch to deterministic" : "Switch back to live";
  $("#deterministic-fallback").classList.add("hidden");
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
    if (response.provenance) { const provenance = document.createElement("div"); provenance.className = "provenance"; provenance.textContent = response.provenance.inference_mode === "live" ? `LIVE · configured ${response.provenance.configured_model} · actual ${response.provenance.actual_model || "not reported"}` : "DETERMINISTIC · no model inference"; evidence.append(document.createElement("br"), provenance); }
    if (response.limitations.length) evidence.append(document.createElement("br"), document.createTextNode(response.limitations.join(" ")));
    article.append(evidence);
  }
  $("#messages").append(article); article.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function sendQuestion(question, mode = state.mode) {
  if (!state.apiBase) { $("#setup-panel").classList.remove("hidden"); $("#api-dialog").showModal(); return; }
  addMessage("human", question); $("#send-chat").disabled = true; setConnection("", "Sending", mode === "live" ? "Waiting for live bounded synthesis…" : "Retrieving one deterministic record…");
  try {
    const response = await fetch(endpoint("/api/chat"), { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ session_id: state.sessionId, message: question, mode }) });
    const body = await response.json();
    if (!response.ok) {
      const detail = typeof body.detail === "object" ? body.detail : { code: "live_inference_unavailable", message: String(body.detail || `HTTP ${response.status}`) };
      const retry = detail.retry_after_seconds == null ? "" : ` Retry after about ${detail.retry_after_seconds} seconds.`;
      addMessage("error", `${detail.message || "Live inference failed."}${retry}`);
      if (mode === "live" && state.serverConfig?.deterministic_mode_enabled) $("#deterministic-fallback").classList.remove("hidden");
      setConnection("error", "Live request failed", detail.code || "live_inference_unavailable"); return;
    }
    addMessage("docent", body.reply, body); await checkConnection();
  } catch (error) {
    addMessage("error", `The public Docent API could not be reached. ${error.message}`);
    setConnection("error", "Unavailable", "Check the API URL and CORS origin");
  } finally { $("#send-chat").disabled = false; }
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
$("#toggle-mode").addEventListener("click", () => { state.mode = state.mode === "live" ? "deterministic" : "live"; updateModeControls(); checkConnection(); });
$("#deterministic-fallback").addEventListener("click", () => { state.mode = "deterministic"; updateModeControls(); const last = [...document.querySelectorAll(".message.human p")].at(-1)?.textContent; if (last) sendQuestion(last, "deterministic"); });
$("#reset-chat").addEventListener("click", () => { state.sessionId = crypto.randomUUID(); $("#messages").innerHTML = ""; addMessage("docent", "Local conversation reset. The server retains only bounded recent history for the previous anonymous session ID."); });
$("#configure-api").addEventListener("click", () => $("#api-dialog").showModal());
$("#save-api").addEventListener("click", (event) => { event.preventDefault(); const value = normalizedBase($("#api-url").value); if (value) localStorage.setItem("docent.publicApiBaseUrl", value); else localStorage.removeItem("docent.publicApiBaseUrl"); state.apiBase = value || normalizedBase(state.config.api_base_url || (isPages() ? "" : location.origin)); state.projectLoaded = false; $("#api-dialog").close(); checkConnection(); });
showView(location.hash.slice(1) || "chat"); loadConfig();
