const $ = (selector) => document.querySelector(selector);

const state = {
  image: "",
  demoCaseId: "",
  lastResult: null,
  loadingInterval: null,
  loadingStartedAt: 0,
};

const sampleReport = `Lung core biopsy demonstrates malignant gland-forming epithelial cells with mucin production. Tumor cells are strongly positive for TTF-1 and Napsin A and negative for p40.`;
const sampleLabels = [
  "benign lung tissue",
  "lung adenocarcinoma",
  "lung squamous cell carcinoma",
];
const loadingPhases = [
  ["Retrieving relevant evidence", "Searching the frozen local corpus against the case findings and differential."],
  ["Building case-specific prompts", "Extracting short, visually discriminative features for every candidate."],
  ["Comparing pathology models", "Running image-only and case-specific prompts across the available vision models."],
  ["Preparing the review brief", "Summarizing model outputs, retrieved evidence, and the next human review step."],
];

async function checkStatus() {
  const holder = $("#pipeline-status");
  try {
    const response = await fetch("/api/status");
    const status = await response.json();
    const models = status.models || { musk: status.musk, conch: status.conch };
    const modelEntries = Object.entries(models).filter(([, value]) => value);
    const readyModels = modelEntries.filter(([, value]) => value.configured);
    const ready = readyModels.length > 0 && status.lumen.configured && status.corpus.configured;
    const partial = readyModels.length > 0 || status.lumen.configured || status.corpus.configured;
    holder.innerHTML = `<span class="status-dot ${ready ? "ready" : partial ? "partial" : "waiting"}"></span>${status.demo_replay ? "Saved demo ready" : ready ? "Workflow ready" : "Setup incomplete"}`;
    $("#model-count").textContent = status.demo_replay
      ? `${readyModels.length}/${modelEntries.length} models · replay mode`
      : `${readyModels.length}/${modelEntries.length} vision models connected`;
    holder.title = [
      ...modelEntries.map(([name, value]) => `${name.toUpperCase()}: ${value.detail}`),
      `Lumen: ${status.lumen.detail}`,
      `Corpus: ${status.corpus.documents} documents`,
    ].join("\n");
    if (status.lumen.configured) loadModels();
  } catch (error) {
    holder.innerHTML = `<span class="status-dot waiting"></span>Server unavailable`;
    $("#model-count").textContent = "Services unavailable";
  }
}

async function loadModels() {
  const select = $("#model");
  if (select.dataset.loaded === "true") return;
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    if (!response.ok) return;
    for (const id of data.models) {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = id;
      option.selected = id === data.default;
      select.append(option);
    }
    select.dataset.loaded = "true";
  } catch (_) {}
}

function readImage(file) {
  if (!file) return;
  if (file.size > 25 * 1024 * 1024) {
    showError("Image must be no larger than 25 MB.");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    setImage(reader.result, file.name);
  };
  reader.readAsDataURL(file);
}

function setImage(image, name, demoCaseId = "") {
  state.image = image;
  state.demoCaseId = demoCaseId;
  $("#preview").src = image;
  $("#dropzone").classList.add("has-image");
  $("#drop-copy strong").textContent = name;
}

function showOnly(id) {
  ["#empty-state", "#loading-state", "#error-card", "#results"].forEach(selector => {
    $(selector).classList.toggle("hidden", selector !== id);
  });
}

function showError(message) {
  stopLoading();
  $("#error-message").textContent = message;
  showOnly("#error-card");
}

function fillList(selector, items, fallback = "None noted in this review.") {
  const list = $(selector);
  list.innerHTML = "";
  const values = Array.isArray(items) && items.length ? items : [fallback];
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = value;
    list.append(item);
  }
}

function setLoadingPhase(index) {
  const phase = loadingPhases[Math.min(index, loadingPhases.length - 1)];
  $("#loading-title").textContent = phase[0];
  $("#loading-copy").textContent = phase[1];
  [...$("#loading-steps").children].forEach((item, itemIndex) => {
    item.classList.toggle("active", itemIndex <= index);
  });
}

function startLoading() {
  stopLoading();
  state.loadingStartedAt = Date.now();
  setLoadingPhase(0);
  $("#elapsed-time").textContent = "0 seconds elapsed";
  state.loadingInterval = window.setInterval(() => {
    const seconds = Math.floor((Date.now() - state.loadingStartedAt) / 1000);
    const phase = Math.min(Math.floor(seconds / 5), loadingPhases.length - 1);
    setLoadingPhase(phase);
    $("#elapsed-time").textContent = `${seconds} second${seconds === 1 ? "" : "s"} elapsed`;
  }, 1000);
}

function stopLoading() {
  if (state.loadingInterval) window.clearInterval(state.loadingInterval);
  state.loadingInterval = null;
}

function legacyModelResults(data) {
  const results = {};
  const baseline = data.baseline_predictions?.[0] || null;
  const enhanced = data.musk_predictions?.[0] || null;
  if (baseline || enhanced) results.musk = { name: "MUSK", baseline, enhanced, error: "" };
  const conch = data.conch_predictions?.[0] || null;
  if (conch) results.conch = { name: "CONCH", baseline: null, enhanced: conch, error: "" };
  return results;
}

function formatScore(result) {
  if (!result || !Number.isFinite(Number(result.probability))) return "—";
  return (Number(result.probability) * 100).toFixed(1);
}

function renderModels(modelResults) {
  const holder = $("#model-results");
  holder.innerHTML = "";
  const table = document.createElement("table");
  table.className = "model-table";
  const head = document.createElement("thead");
  const headingRow = document.createElement("tr");
  for (const label of ["Model", "Image only", "Case specific", "Change"]) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = label;
    headingRow.append(cell);
  }
  head.append(headingRow);
  table.append(head);
  const body = document.createElement("tbody");
  for (const [key, result] of Object.entries(modelResults)) {
    const baseline = result.baseline;
    const enhanced = result.enhanced;
    const changed = baseline && enhanced && baseline.label !== enhanced.label;
    const row = document.createElement("tr");
    if (changed) row.className = "changed";
    const name = document.createElement("strong");
    const nameCell = document.createElement("th");
    nameCell.scope = "row";
    nameCell.textContent = result.name || key.toUpperCase();
    row.append(nameCell);
    for (const prediction of [baseline, enhanced]) {
      const cell = document.createElement("td");
      const label = document.createElement("span");
      label.textContent = result.error ? "Unavailable" : prediction?.label || "Unavailable";
      const score = document.createElement("small");
      score.textContent = prediction ? `score ${formatScore(prediction)}` : "";
      cell.append(label, score);
      row.append(cell);
    }
    const change = document.createElement("td");
    change.textContent = result.error ? "Unavailable" : changed ? "Changed" : "—";
    if (changed) change.className = "change-flag";
    row.append(change);
    body.append(row);
  }
  table.append(body);
  holder.append(table);
}

function agreementText(modelResults) {
  const labels = Object.values(modelResults)
    .map(result => result.enhanced?.label)
    .filter(Boolean);
  if (!labels.length) return "No vision-model result was available.";
  const counts = labels.reduce((all, label) => ({ ...all, [label]: (all[label] || 0) + 1 }), {});
  const [label, count] = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
  return `${count} of ${labels.length} available vision models selected ${label} after case-specific prompting.`;
}

function renderPrompts(prompts) {
  const holder = $("#case-prompts");
  holder.innerHTML = "";
  for (const [label, description] of Object.entries(prompts || {})) {
    const item = document.createElement("article");
    item.className = "prompt-item";
    const title = document.createElement("strong");
    title.textContent = label;
    const text = document.createElement("p");
    text.textContent = description;
    item.append(title, text);
    holder.append(item);
  }
}

function renderEvidence(evidenceItems) {
  const cards = $("#evidence-cards");
  cards.innerHTML = "";
  for (const evidence of evidenceItems || []) {
    const card = document.createElement("article");
    card.className = "evidence-card";
    const title = document.createElement(evidence.url ? "a" : "strong");
    title.textContent = evidence.title;
    if (evidence.url) {
      title.href = evidence.url;
      title.target = "_blank";
      title.rel = "noreferrer";
    }
    const meta = document.createElement("small");
    const relevance = Number.isFinite(Number(evidence.score)) ? Number(evidence.score).toFixed(2) : "—";
    meta.textContent = `${evidence.source_id} · ${evidence.year || "year unknown"} · retrieval score ${relevance}`;
    const text = document.createElement("p");
    text.textContent = evidence.text;
    card.append(title, meta, text);
    cards.append(card);
  }
}

function reviewBrief(data) {
  const review = data.review || data.synthesis || {};
  const lines = [
    "HistoPrompt research review",
    `Evidence-supported candidate: ${data.final_classification || review.classification || "indeterminate"}`,
    `Assessment: ${review.assessment || "No structured assessment returned."}`,
    "",
    "Rationale:",
    ...(review.rationale || []).map(item => `- ${item}`),
    "",
    "Recommended human review:",
    ...(review.recommended_review || []).map(item => `- ${item}`),
    "",
    "Research prototype only; not validated for clinical use or patient care.",
  ];
  return lines.join("\n");
}

function render(data) {
  stopLoading();
  state.lastResult = data;
  const review = data.review || data.synthesis || {
    classification: "indeterminate",
    confidence: 0,
    assessment: data.raw_synthesis || "No structured review was returned.",
  };
  const classification = data.final_classification || review.classification || "indeterminate";
  const modelResults = data.model_results || legacyModelResults(data);

  $("#classification").textContent = classification === "indeterminate" ? "Indeterminate · human review required" : classification;
  $("#assessment").textContent = review.assessment || "No assessment returned.";
  $("#agreement-summary").textContent = agreementText(modelResults);
  renderModels(modelResults);
  fillList("#rationale", review.rationale);
  fillList("#review", review.recommended_review, "Review the slide, supplied differential, and source evidence independently.");
  renderPrompts(data.case_specific_prompts || data.musk_prompts || data.primary_prompts);
  renderEvidence(data.evidence);
  $("#model-used").textContent = data.demo_replay
    ? `Saved demo · ${data.llm_model}`
    : `Reviewed by ${data.llm_model}`;
  $("#prompt-generation-prompt").textContent = data.prompt_generation_prompt || "Unavailable";
  $("#review-prompt").textContent = data.review_prompt || "Unavailable";
  showOnly("#results");
  if (window.matchMedia("(max-width: 1120px)").matches) {
    $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

$("#image-input").addEventListener("change", event => readImage(event.target.files[0]));
for (const eventName of ["dragenter", "dragover"]) {
  $("#dropzone").addEventListener(eventName, event => {
    event.preventDefault();
    $("#dropzone").classList.add("dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  $("#dropzone").addEventListener(eventName, event => {
    event.preventDefault();
    $("#dropzone").classList.remove("dragging");
  });
}
$("#dropzone").addEventListener("drop", event => {
  const file = event.dataTransfer.files[0];
  if (file) readImage(file);
});

$("#load-sample").addEventListener("click", async () => {
  const button = $("#load-sample");
  button.disabled = true;
  button.textContent = "Loading case…";
  try {
    const response = await fetch("/api/demo-case");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Demo case unavailable");
    setImage(data.image, data.image_name, data.case_id);
    $("#report").value = data.report;
    $("#labels").value = data.labels.join("\n");
  } catch (_) {
    state.demoCaseId = "";
    $("#report").value = sampleReport;
    $("#labels").value = sampleLabels.join("\n");
  } finally {
    button.disabled = false;
    button.textContent = "Load demo case";
  }
});

$("#copy-review").addEventListener("click", async () => {
  if (!state.lastResult) return;
  const button = $("#copy-review");
  try {
    await navigator.clipboard.writeText(reviewBrief(state.lastResult));
    button.textContent = "Copied";
  } catch (_) {
    button.textContent = "Copy unavailable";
  }
  window.setTimeout(() => { button.textContent = "Copy review brief"; }, 1800);
});

$("#case-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (!state.image) return showError("Add a pathology image before starting the review.");
  const report = $("#report").value.trim();
  if (!report) return showError("Add case findings before starting the review.");
  const labels = $("#labels").value.split("\n").map(value => value.trim()).filter(Boolean);
  if (labels.length < 2) return showError("Add at least two candidates to the working differential.");

  showOnly("#loading-state");
  startLoading();
  const requestStartedAt = Date.now();
  $("#run-button").disabled = true;
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image: state.image,
        report,
        labels,
        demo_case_id: state.demoCaseId,
        model: $("#model").value,
        top_k: Number($("#top-k").value),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed with HTTP ${response.status}`);
    if (data.demo_replay) {
      const remaining = 2400 - (Date.now() - requestStartedAt);
      if (remaining > 0) await new Promise(resolve => window.setTimeout(resolve, remaining));
    }
    render(data);
  } catch (error) {
    showError(error.message);
  } finally {
    $("#run-button").disabled = false;
  }
});

checkStatus();
