const $ = (selector) => document.querySelector(selector);

const state = { image: "" };
const sampleReport = `Lung core biopsy demonstrates malignant gland-forming epithelial cells with mucin production. Tumor cells are strongly positive for TTF-1 and Napsin A and negative for p40. No patient identifiers are included in this demonstration.`;

async function checkStatus() {
  const holder = $("#pipeline-status");
  try {
    const response = await fetch("/api/status");
    const status = await response.json();
    const ready = status.musk.configured && status.lumen.configured && status.corpus.configured;
    const count = [status.musk, status.lumen, status.corpus].filter(item => item.configured).length;
    holder.innerHTML = `<span class="status-dot ${ready ? "ready" : count ? "partial" : "waiting"}"></span>${ready ? "Pipeline ready" : `${count}/3 services configured`}`;
    holder.title = `MUSK: ${status.musk.detail}\nCONCH: ${status.conch.detail}\nLumen: ${status.lumen.detail}\nCorpus: ${status.corpus.documents} documents`;
    if (status.lumen.configured) loadModels();
  } catch (error) {
    holder.innerHTML = `<span class="status-dot waiting"></span>Server unavailable`;
  }
}

async function loadModels() {
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    if (!response.ok) return;
    for (const id of data.models) {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = id;
      option.selected = id === data.default;
      $("#model").append(option);
    }
  } catch (_) {}
}

function readImage(file) {
  if (!file) return;
  if (file.size > 25 * 1024 * 1024) return showError("Image must be no larger than 25 MB.");
  const reader = new FileReader();
  reader.onload = () => {
    state.image = reader.result;
    $("#preview").src = reader.result;
    $("#dropzone").classList.add("has-image");
    $("#drop-copy strong").textContent = file.name;
  };
  reader.readAsDataURL(file);
}

function showOnly(id) {
  ["#empty-state", "#loading-state", "#error-card", "#results"].forEach(selector => {
    $(selector).classList.toggle("hidden", selector !== id);
  });
}

function showError(message) {
  $("#error-message").textContent = message;
  showOnly("#error-card");
}

function fillList(selector, items, fallback = "None noted.") {
  const list = $(selector);
  list.innerHTML = "";
  const values = Array.isArray(items) && items.length ? items : [fallback];
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = value;
    list.append(item);
  }
}

function renderPredictions(selector, predictions) {
  const bars = $(selector);
  bars.innerHTML = "";
  for (const prediction of predictions || []) {
    const row = document.createElement("div");
    row.className = "prediction";
    row.innerHTML = `<span></span><div class="bar"><i></i></div><strong>${Math.round(prediction.probability * 100)}%</strong>`;
    row.querySelector("span").textContent = prediction.label;
    row.querySelector("i").style.width = `${prediction.probability * 100}%`;
    bars.append(row);
  }
}

function render(data) {
  const result = data.synthesis || {
    classification: "Unstructured model response",
    confidence: 0,
    assessment: data.raw_synthesis,
    rationale: [], discrepancies: [], recommended_review: []
  };
  const primary = data.primary_predictions?.[0] || data.baseline_predictions?.[0];
  const confidence = Math.max(0, Math.min(1, Number(result.confidence) || 0));
  $("#classification").textContent = primary?.label || result.classification || "Indeterminate";
  $("#assessment").textContent = result.assessment || "No assessment returned.";
  const modelScore = primary ? Number(primary.probability) : confidence;
  $("#confidence").textContent = `${Math.round(modelScore * 100)}%`;
  $("#confidence-ring").style.setProperty("--confidence", `${modelScore * 100}%`);
  fillList("#rationale", result.rationale);
  fillList("#discrepancies", result.discrepancies);
  fillList("#review", result.recommended_review, "Human pathology review remains required.");

  const promptCards = $("#musk-prompts");
  promptCards.innerHTML = "";
  for (const [label, description] of Object.entries(data.primary_prompts || {})) {
    const card = document.createElement("article");
    card.className = "evidence-card";
    const title = document.createElement("strong");
    title.textContent = label;
    const text = document.createElement("p");
    text.textContent = description;
    card.append(title, text);
    promptCards.append(card);
  }

  renderPredictions("#baseline-prediction-bars", data.baseline_predictions);
  renderPredictions("#prediction-bars", data.musk_predictions);
  const conchSection = $("#conch-section");
  const hasConch = Array.isArray(data.conch_predictions) && data.conch_predictions.length;
  conchSection.classList.toggle("hidden", !hasConch);
  if (hasConch) renderPredictions("#conch-prediction-bars", data.conch_predictions);
  const baseline = data.baseline_predictions?.[0];
  const enhanced = data.musk_predictions?.[0];
  if (baseline && enhanced && baseline.label === enhanced.label) {
    const delta = (enhanced.probability - baseline.probability) * 100;
    $("#prompt-effect").textContent = `Prompt effect: same top label; ${delta >= 0 ? "+" : ""}${delta.toFixed(2)} percentage points.`;
  } else if (baseline && enhanced) {
    $("#prompt-effect").textContent = `Prompt effect: top label changed from ${baseline.label} to ${enhanced.label}.`;
  } else {
    $("#prompt-effect").textContent = "Prompt effect could not be calculated.";
  }

  const cards = $("#evidence-cards");
  cards.innerHTML = "";
  for (const evidence of data.evidence) {
    const card = document.createElement("article");
    card.className = "evidence-card";
    const title = document.createElement(evidence.url ? "a" : "strong");
    title.textContent = evidence.title;
    if (evidence.url) { title.href = evidence.url; title.target = "_blank"; title.rel = "noreferrer"; }
    const meta = document.createElement("small");
    meta.textContent = `${evidence.source_id} · ${evidence.year || "year unknown"} · relevance ${evidence.score.toFixed(2)}`;
    const text = document.createElement("p");
    text.textContent = evidence.text;
    card.append(title, meta, text);
    cards.append(card);
  }
  $("#model-used").textContent = `Synthesized by ${data.llm_model}`;
  $("#prompt-generation-prompt").textContent = data.prompt_generation_prompt;
  $("#review-prompt").textContent = data.review_prompt;
  showOnly("#results");
}

$("#image-input").addEventListener("change", event => readImage(event.target.files[0]));
for (const eventName of ["dragenter", "dragover"]) {
  $("#dropzone").addEventListener(eventName, event => { event.preventDefault(); $("#dropzone").classList.add("dragging"); });
}
for (const eventName of ["dragleave", "drop"]) {
  $("#dropzone").addEventListener(eventName, event => { event.preventDefault(); $("#dropzone").classList.remove("dragging"); });
}
$("#dropzone").addEventListener("drop", event => {
  const file = event.dataTransfer.files[0];
  if (file) readImage(file);
});
$("#load-sample").addEventListener("click", () => { $("#report").value = sampleReport; });

$("#case-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (!state.image) return showError("Choose a pathology image first.");
  const labels = $("#labels").value.split("\n").map(value => value.trim()).filter(Boolean);
  showOnly("#loading-state");
  $("#run-button").disabled = true;
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image: state.image,
        report: $("#report").value,
        labels,
        model: $("#model").value,
        top_k: Number($("#top-k").value),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed with HTTP ${response.status}`);
    render(data);
  } catch (error) {
    showError(error.message);
  } finally {
    $("#run-button").disabled = false;
  }
});

checkStatus();

