"use strict";
const $ = id => document.getElementById(id);
let context, sources = [], corrections = [], active = false;
const scope = () => ({product: $("product").value, version: $("version").value});
const scoped = () => sources.filter(x => x.product === scope().product && x.version === scope().version);
const versions = product => [...new Set(sources.filter(s => s.product === product).map(s => s.version))].sort((a,b)=>a.localeCompare(b, undefined, {numeric:true}));
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
  $("citations").replaceChildren(); $("verified-quotes").replaceChildren(); $("runtime").hidden = true;
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
  $("question").placeholder = scope().product === "Python queues" ? "Does join() returning prove all queued work finished?" : "What happens when a downstream request times out?";
  $("review-question").placeholder = scope().product === "Python queues" ? "For example: does immediate shutdown preserve completion accounting?" : "For example: how should timeout retries work?";
  $("source-provenance").textContent = scope().product === "Python queues" ? "Original summaries of official Python documentation. Open the upstream page to verify context; quote validation checks these curated passages." : "A fictional RelayGate runbook authored for this demo. It is separate from the real Python documentation.";
  $("source-summary").textContent = `${passages.length} passages · version-scoped`;
  $("evidence-count").textContent = String(passages.length).padStart(2, "0");
  $("sources").replaceChildren(); $("review-source").replaceChildren();
  for (const [i, s] of passages.entries()) {
    const detail = el("details", undefined, "source"); detail.id = `source-${s.id}`; detail.open = i === 0;
    const summary = el("summary"); summary.append(el("code", s.id), el("span", s.title));
    const review = el("button", "Review this passage ↗"); review.type = "button"; review.addEventListener("click", () => selectSource(s.id));
    detail.append(summary, el("p", s.text));
    if (s.source_url) { const link = el("a", `${s.source_label} ↗`, "provenance-link"); link.href = s.source_url; link.target = "_blank"; link.rel = "noopener noreferrer"; detail.append(link); }
    detail.append(review); $("sources").append(detail);
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
function view(name) {
  $("workbench").hidden = name !== "workbench"; $("memory-view").hidden = name !== "memory"; $("compare-view").hidden = name !== "compare";
  for (const [id, selected] of [["nav-workbench", name === "workbench"], ["nav-memory", name === "memory"], ["nav-compare", name === "compare"]]) {
    $(id).classList.toggle("active", selected); selected ? $(id).setAttribute("aria-current", "page") : $(id).removeAttribute("aria-current");
  }
  $("breadcrumb").textContent = {memory:"Reviewed memory", compare:"Version lens", workbench:"Answer workbench"}[name];
}
function populateVersions() {
  $("version").replaceChildren();
  for (const version of versions(scope().product)) { const option = el("option", version); option.value = version; $("version").append(option); }
  renderSources(); resetAnswer();
}
function comparisonRows() {
  const product = $("compare-product").value, from = $("compare-from").value, to = $("compare-to").value;
  const left = sources.filter(s=>s.product===product && s.version===from), right = sources.filter(s=>s.product===product && s.version===to);
  const keys = [...new Set([...left,...right].map(s=>s.id.substring(s.id.indexOf("-")+1)))];
  return keys.map(key=>({left:left.find(s=>s.id.endsWith(`-${key}`)), right:right.find(s=>s.id.endsWith(`-${key}`))}));
}
function renderComparison() {
  const rows = comparisonRows(); $("comparison-list").replaceChildren();
  const changed = rows.filter(r=>r.left?.text!==r.right?.text).length;
  $("comparison-summary").textContent = `${changed} of ${rows.length} curated topics have different text. This is source comparison, not a claim that every wording change changes behavior.`;
  for (const row of rows) {
    const article = el("article", undefined, "comparison-item"); article.append(el("h3", row.right?.title || row.left?.title));
    const columns = el("div", undefined, "comparison-columns");
    for (const [s, version] of [[row.left,$("compare-from").value],[row.right,$("compare-to").value]]) {
      const column = el("div"); column.append(el("small", `VERSION ${version}`), el("p", s?.text || "No passage supplied for this version."));
      if (s) { column.append(el("code", s.id)); if (s.source_url) { const link = el("a", "Official source ↗", "provenance-link"); link.href = s.source_url; link.target="_blank"; link.rel="noopener noreferrer"; column.append(link); } }
      columns.append(column);
    }
    article.append(columns);
    if (row.right) { const ask = el("button", "Ask about this change ↗", "example"); ask.addEventListener("click",()=>{if(active)return; $("product").value=$("compare-product").value; populateVersions(); $("version").value=$("compare-to").value; renderSources(); resetAnswer(); $("question").value=`Explain ${row.right.title.toLowerCase()} for ${scope().product} ${scope().version}.`; view("workbench"); $("question").focus();}); article.append(ask); }
    $("comparison-list").append(article);
  }
}
function populateComparison() {
  for (const id of ["compare-from","compare-to"]) { $(id).replaceChildren(); for(const v of versions($("compare-product").value)) { const o=el("option",v); o.value=v; $(id).append(o); } }
  $("compare-to").selectedIndex=Math.min(1,$("compare-to").options.length-1); renderComparison();
}
$("nav-workbench").addEventListener("click", () => view("workbench")); $("nav-memory").addEventListener("click", () => view("memory")); $("nav-compare").addEventListener("click", () => view("compare"));
$("product").addEventListener("change",populateVersions);
$("compare-product").addEventListener("change",populateComparison);
$("compare-from").addEventListener("change",renderComparison); $("compare-to").addEventListener("change",renderComparison);
$("export-comparison").addEventListener("click",()=>{
  const rows = comparisonRows(), product = $("compare-product").value;
  const text = [`# ${product}: ${$("compare-from").value} → ${$("compare-to").value}`,"Curated source comparison. No model output or semantic-difference guarantee.",...rows.flatMap(r=>[`\n## ${r.right?.title||r.left?.title}`,...[r.left,r.right].map(s=>s?`\n### ${s.version} — ${s.id}\n${s.text}\n${s.source_url||"Authored synthetic example"}`:"No supplied passage.")])].join("\n");
  const url=URL.createObjectURL(new Blob([text],{type:"text/markdown;charset=utf-8"})); const a=el("a"); a.href=url; a.download="tracedesk-version-comparison.md"; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$("version").addEventListener("change", () => { renderSources(); resetAnswer(); });
$("use-memory").addEventListener("change", resetAnswer);
$("review-source").addEventListener("change", () => selectSource($("review-source").value, false));
$("example-supported").addEventListener("click", () => { $("question").value = scope().product === "Python queues" ? "Does join() returning always mean all queued work finished?" : "How should I retry a downstream request after a timeout?"; $("question").focus(); });
$("example-unknown").addEventListener("click", () => { $("question").value = "What is the refund policy and subscription price?"; $("question").focus(); });
$("ask-form").addEventListener("submit", async event => {
  event.preventDefault(); if (active) return; active = true;
  const question = $("question").value.trim(); if (!question) { active = false; return; }
  $("ask").disabled = true; $("version").disabled = true; $("product").disabled = true; $("use-memory").disabled = true;
  $("answer-section").setAttribute("aria-busy", "true"); $("answer-state").textContent = "Checking evidence…"; $("answer-state").className = "badge neutral";
  $("answer-body").className = "answer-copy"; $("answer-body").textContent = "Waiting for NVIDIA inference on Nebius Token Factory…"; $("citations").replaceChildren(); $("verified-quotes").replaceChildren(); $("runtime").hidden = true;
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
    for (const q of result.evidence_quotes || []) { const quote=el("blockquote"); quote.append(el("p",q.quote),el("cite",`${q.passage_id} · exact excerpt in curated source`)); $("verified-quotes").append(quote); }
    const usage = result.usage || {}; $("runtime").hidden = false;
    $("runtime").textContent = `${result.provider || "Nebius Token Factory"} / ${result.model} · ${result.latency_ms} ms · ${usage.total_tokens ?? "unreported"} tokens · ${(result.used_correction_ids || []).length} memories cited`;
    $("review-question").value = question;
  } catch (error) {
    $("answer-state").textContent = "Inference unavailable"; $("answer-state").className = "badge error";
    $("answer-body").className = "answer-copy error-copy"; $("answer-body").textContent = error.message;
  } finally { active = false; $("ask").disabled = false; $("version").disabled = false; $("product").disabled = false; $("use-memory").disabled = false; $("answer-section").setAttribute("aria-busy", "false"); }
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
    for (const product of [...new Set(sources.map(s=>s.product))].sort()) { for(const id of ["product","compare-product"]) { const option=el("option",product); option.value=product; $(id).append(option); } }
    $("connection").classList.toggle("warning", !context.configured);
    $("connection").textContent = context.configured ? `Runtime configured · ${context.model} · Actual connectivity is verified when you ask a question.` : "Live inference needs NEBIUS_API_KEY on the local server. Source browsing and reviewed memory work now; no AI answers are simulated.";
    populateVersions(); populateComparison(); await refreshMemory();
  } catch(error) { $("connection").classList.add("warning"); $("connection").textContent = `Workspace could not load: ${error.message}. Reload to retry.`; $("ask").disabled = true; $("save-correction").disabled = true; }
})();
