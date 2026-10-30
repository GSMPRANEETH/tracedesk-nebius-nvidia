"use strict";
const $ = id => document.getElementById(id);
let context, sources = [], corrections = [], active = false;
const scope = () => ({product: "RelayGate", version: $("version").value});
const scoped = () => sources.filter(x => x.product === scope().product && x.version === scope().version);
function el(tag, text, cls) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; }
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:"POST", headers:{"Content-Type":"application/json", "X-TraceDesk-Token":context.csrf_token}, body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The request failed. Try again.");
  return result;
}
function resetAnswer() {
  $("answer-state").textContent = "Awaiting question"; $("answer-state").className = "badge neutral";
  $("answer-body").className = "empty-answer"; $("answer-body").replaceChildren(el("div", "↳", "evidence-glyph"), el("h3", "A source, not a guess."), el("p", "Your answer, citations, and runtime trace will appear here. Missing evidence stays visible."));
  $("citations").replaceChildren(); $("runtime").hidden = true;
}
function selectSource(id, focus = true) {
  $("review-source").value = id;
  const source = scoped().find(x => x.id === id);
  $("review-text").value = source?.text || "";
  $("review-question").value = $("question").value;
  $("approved").checked = false; $("review-status").textContent = "";
  if (focus) $("review-question").focus();
}
function renderSources() {
  const passages = scoped();
  $("source-summary").textContent = `${passages.length} passages · version-scoped`;
  $("evidence-count").textContent = String(passages.length).padStart(2, "0");
  $("sources").replaceChildren(); $("review-source").replaceChildren();
  for (const [i, s] of passages.entries()) {
    const detail = el("details", undefined, "source"); detail.id = `source-${s.id}`; detail.open = i === 0;
    const summary = el("summary"); summary.append(el("code", s.id), el("span", s.title));
    const review = el("button", "Review this passage ↗"); review.type = "button"; review.addEventListener("click", () => selectSource(s.id));
    detail.append(summary, el("p", s.text), review); $("sources").append(detail);
    const option = el("option", `${s.id} — ${s.title}`); option.value = s.id; $("review-source").append(option);
  }
  if (passages.length) selectSource(passages[0].id, false);
}
function renderMemory() {
  $("memory-count").textContent = corrections.length;
  $("memory-list").replaceChildren();
  if (!corrections.length) $("memory-list").append(el("p", "No reviewed memory yet. Save a source excerpt in the workbench to begin.", "empty-memory"));
  for (const c of corrections) {
    const item = el("article", undefined, "memory-item");
    item.append(el("code", `${c.product} / ${c.version}`), el("h3", c.question), el("p", c.text), el("small", `Evidence: ${(c.evidence_ids || []).join(", ")} · Human reviewed`));
    $("memory-list").append(item);
  }
  $("clear-memory").disabled = corrections.length === 0;
}
async function refreshMemory() { corrections = (await api("/api/corrections")).corrections; renderMemory(); }
function view(memory) {
  $("workbench").hidden = memory; $("memory-view").hidden = !memory;
  for (const [id, selected] of [["nav-workbench", !memory], ["nav-memory", memory]]) {
    $(id).classList.toggle("active", selected); selected ? $(id).setAttribute("aria-current", "page") : $(id).removeAttribute("aria-current");
  }
  $("breadcrumb").textContent = memory ? "Reviewed memory" : "Answer workbench";
}
$("nav-workbench").addEventListener("click", () => view(false)); $("nav-memory").addEventListener("click", () => view(true));
$("version").addEventListener("change", () => { renderSources(); resetAnswer(); });
$("use-memory").addEventListener("change", resetAnswer);
$("review-source").addEventListener("change", () => selectSource($("review-source").value, false));
$("example-supported").addEventListener("click", () => { $("question").value = "How should I retry a downstream request after a timeout?"; $("question").focus(); });
$("example-unknown").addEventListener("click", () => { $("question").value = "What is the refund policy and subscription price?"; $("question").focus(); });
$("ask-form").addEventListener("submit", async event => {
  event.preventDefault(); if (active) return; active = true;
  const question = $("question").value.trim(); if (!question) { active = false; return; }
  $("ask").disabled = true; $("version").disabled = true; $("use-memory").disabled = true;
  $("answer-section").setAttribute("aria-busy", "true"); $("answer-state").textContent = "Checking evidence…"; $("answer-state").className = "badge neutral";
  $("answer-body").className = "answer-copy"; $("answer-body").textContent = "Waiting for NVIDIA inference on Nebius Token Factory…"; $("citations").replaceChildren(); $("runtime").hidden = true;
  try {
    const result = await api("/api/answer", {...scope(), question, use_memory:$("use-memory").checked});
    if (result.status === "provider_error") throw new Error(result.error || result.answer || "Nebius inference failed. No substitute answer was generated.");
    const labels = {answer:"Evidence-linked answer", insufficient_evidence:"Insufficient evidence", review_needed:"Review needed"};
    $("answer-state").textContent = labels[result.status] || "Review needed";
    $("answer-state").className = `badge ${result.status === "answer" ? "" : "warning"}`;
    $("answer-body").textContent = result.answer;
    for (const id of result.citations || []) {
      const button = el("button", `↗ ${id}`, "citation"); button.addEventListener("click", () => {
        const source = document.getElementById(`source-${id}`); if (source) { source.open = true; source.scrollIntoView({block:"nearest",behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"instant":"smooth"}); source.querySelector("summary").focus(); }
      }); $("citations").append(button);
    }
    const usage = result.usage || {}; $("runtime").hidden = false;
    $("runtime").textContent = `${result.provider || "Nebius Token Factory"} / ${result.model} · ${result.latency_ms} ms · ${usage.total_tokens ?? "unreported"} tokens · ${(result.used_correction_ids || []).length} memories cited`;
    $("review-question").value = question;
  } catch (error) {
    $("answer-state").textContent = "Inference unavailable"; $("answer-state").className = "badge error";
    $("answer-body").className = "answer-copy error-copy"; $("answer-body").textContent = error.message;
  } finally { active = false; $("ask").disabled = false; $("version").disabled = false; $("use-memory").disabled = false; $("answer-section").setAttribute("aria-busy", "false"); }
});
$("review-form").addEventListener("submit", async event => {
  event.preventDefault(); $("save-correction").disabled = true; $("review-status").textContent = "Saving reviewed excerpt…";
  try {
    await api("/api/corrections", {...scope(), question:$("review-question").value.trim(), text:$("review-text").value.trim(), evidence_ids:[$("review-source").value], approved:$("approved").checked});
    await refreshMemory(); $("review-status").textContent = "Saved. This version can now retrieve the reviewed excerpt."; $("approved").checked = false;
  } catch(error) { $("review-status").textContent = error.message; }
  finally { $("save-correction").disabled = false; }
});
$("clear-memory").addEventListener("click", async () => {
  if (!confirm("Delete all reviewed memory in this local workspace? The runbook will remain.")) return;
  try { await api("/api/clear", {}); await refreshMemory(); $("memory-status").textContent = "All local reviewed memory cleared."; }
  catch(error) { $("memory-status").textContent = error.message; }
});
(async () => {
  try {
    context = await api("/api/context"); sources = context.sources;
    for (const version of [...new Set(sources.filter(s=>s.product === "RelayGate").map(s=>s.version))].sort()) { const option = el("option", `RelayGate ${version}`); option.value = version; $("version").append(option); }
    $("connection").classList.toggle("warning", !context.configured);
    $("connection").textContent = context.configured ? `Runtime configured · ${context.model} · Actual connectivity is verified when you ask a question.` : "Live inference needs NEBIUS_API_KEY on the local server. Source browsing and reviewed memory work now; no AI answers are simulated.";
    renderSources(); await refreshMemory();
  } catch(error) { $("connection").classList.add("warning"); $("connection").textContent = `Workspace could not load: ${error.message}. Reload to retry.`; $("ask").disabled = true; $("save-correction").disabled = true; }
})();
