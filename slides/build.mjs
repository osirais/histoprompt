import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const slidesDir = path.dirname(fileURLToPath(import.meta.url));
const workspaceDir = path.resolve(slidesDir, "..");
const buildDir = path.join(slidesDir, ".build");
const previewDir = path.join(buildDir, "render");
const canonicalPptx = path.join(workspaceDir, "output/slides/HistoPrompt_Hackathon_Deck.pptx");
const finalPptx = path.join(buildDir, `.codex-finalizer/HistoPrompt_Hackathon_Deck-${process.pid}.pptx`);
const skillDir = "/Users/orlan/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations";
const runtimePython = "/Users/orlan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const runtimeNodeModules = "/Users/orlan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules";
process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES = runtimeNodeModules;
const artifactToolPath = path.join(runtimeNodeModules, "@oai/artifact-tool/dist/artifact_tool.mjs");
const { Presentation, PresentationFile } = await import(pathToFileURL(artifactToolPath).href);
const { finalizePresentation, applyPresentationChartFont, makeNativeBulletParagraphs } = await import(
  pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href
);

const W = 1280;
const H = 720;
const TITLE_FONT = "Rubik";
const BODY_FONT = "Noto Sans";
const C = {
  ink: "#12211D",
  muted: "#5D6B66",
  paper: "#F8F5F0",
  white: "#FFFFFF",
  green: "#103D35",
  green2: "#007D68",
  mint: "#DDEDE6",
  pink: "#D13D77",
  rose: "#F0D5DE",
  orange: "#E9873C",
  gold: "#F2C96B",
  plum: "#6A3F78",
  line: "#D7DDD8",
};

const assets = {
  uiInput: path.join(slidesDir, "assets/ui-input-crop.png"),
  uiResults: path.join(slidesDir, "assets/ui-results-crop.png"),
  lungAdeno: path.join(workspaceDir, "benchmarks/diagnosis-11/images/lc25000/lung-adenocarcinoma/lungaca11.jpeg"),
  routingMap: path.join(slidesDir, "assets/routing-map.png"),
  gainTrajectories: path.join(slidesDir, "assets/gain-trajectories.png"),
  workflowPulse: path.join(slidesDir, "assets/workflow-pulse.png"),
  scaleJourney: path.join(slidesDir, "assets/scale-journey.png"),
};

const assetBytes = Object.fromEntries(
  await Promise.all(Object.values(assets).map(async (assetPath) => [assetPath, await fs.readFile(assetPath)])),
);

function addShape(slide, geometry, x, y, w, h, fill = "none", line = "none", radius = undefined) {
  return slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function addText(slide, text, x, y, w, h, opts = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    name: opts.name,
    position: { left: x, top: y, width: w, height: h },
    fill: opts.fill ?? "none",
    line: { style: "solid", fill: opts.line ?? "none", width: opts.line && opts.line !== "none" ? 1 : 0 },
  });
  box.text = text;
  box.text.style = {
    typeface: opts.font ?? BODY_FONT,
    fontSize: opts.size ?? 20,
    bold: opts.bold ?? false,
    italic: opts.italic ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    autoFit: "none",
  };
  return box;
}

function addSpeechBubble(slide, text, x, y, w, h, color, targetX, targetY) {
  const tipX = Math.round(((targetX - (x + w / 2)) / w) * 100000);
  const tipY = Math.round(((targetY - (y + h / 2)) / h) * 100000);
  const bubble = slide.shapes.add({
    geometry: "wedgeRoundRectCallout",
    position: { left: x, top: y, width: w, height: h },
    fill: C.white,
    line: { style: "solid", fill: color, width: 1.5 },
    adjustmentList: [
      { name: "adj1", formula: `val ${tipX}` },
      { name: "adj2", formula: `val ${tipY}` },
      { name: "adj3", formula: "val 16667" },
    ],
  });
  addText(slide, text, x + 18, y + 13, w - 36, h - 26, {
    size: 15,
    bold: true,
    color: C.ink,
  });
  return bubble;
}

function addBullets(slide, items, x, y, w, h, opts = {}) {
  const box = addText(slide, "", x, y, w, h, { size: opts.size ?? 20, color: opts.color ?? C.ink });
  box.text = makeNativeBulletParagraphs(items, {
    marginLeftPoints: opts.marginLeft ?? 16,
    hangingPoints: opts.hanging ?? 8,
    spaceAfterPoints: opts.spaceAfter ?? 7,
  });
  box.text.style = {
    typeface: BODY_FONT,
    fontSize: opts.size ?? 20,
    color: opts.color ?? C.ink,
    autoFit: "none",
  };
  return box;
}

function addImage(slide, assetPath, x, y, w, h, fit = "cover", alt = "") {
  return slide.images.add({
    blob: assetBytes[assetPath],
    contentType: assetPath.toLowerCase().endsWith(".png") ? "image/png" : "image/jpeg",
    alt,
    fit,
    position: { left: x, top: y, width: w, height: h },
    geometry: "roundRect",
    borderRadius: 16,
  });
}

function addFullBleedImage(slide, assetPath, alt = "") {
  return slide.images.add({
    blob: assetBytes[assetPath],
    contentType: "image/png",
    alt,
    fit: "cover",
    position: { left: 0, top: 0, width: W, height: H },
    geometry: "rect",
  });
}

function addFooter(slide, number, source = "") {
  addShape(slide, "line", 64, 682, 1152, 1, "none", C.line);
  addText(slide, source, 72, 687, 1040, 20, { size: 9, color: C.muted });
  addText(slide, String(number).padStart(2, "0"), 1148, 684, 60, 24, { size: 11, color: C.muted, align: "right", bold: true });
}

function addTitle(slide, title, number, subtitle = "", source = "") {
  slide.background.fill = C.paper;
  addText(slide, title, 72, 42, 1100, 56, { size: 34, bold: true, color: C.ink, font: TITLE_FONT });
  if (subtitle) addText(slide, subtitle, 72, 101, 1100, 42, { size: 19, color: C.muted });
  addFooter(slide, number, source);
}

function addMetric(slide, value, label, x, y, w, accent = C.green) {
  addText(slide, value, x, y, w, 62, { size: 42, bold: true, color: accent });
  addText(slide, label, x, y + 62, w, 48, { size: 18, color: C.muted });
}

function addNote(slide, lines) {
  slide.speakerNotes.text = Array.isArray(lines) ? lines : [lines];
  slide.speakerNotes.setVisible(true);
}

function addChart(slide, type, config) {
  const chart = slide.charts.add(type, config);
  applyPresentationChartFont(chart, { fontFamily: BODY_FONT });
  return chart;
}

const deck = Presentation.create({ slideSize: { width: W, height: H } });

// 1. Cover
{
  const s = deck.slides.add();
  s.background.fill = C.paper;
  addShape(s, "rect", 0, 0, 710, H, C.green, "none");
  addImage(s, assets.lungAdeno, 710, 0, 570, H, "cover", "LC25000 lung adenocarcinoma histology image");
  addText(s, "HistoPrompt", 72, 124, 560, 86, { size: 58, bold: true, color: C.white, font: TITLE_FONT });
  addText(s, "Model-aware prompting for pathology review", 72, 224, 555, 132, { size: 31, color: "#E9F4EF", font: TITLE_FONT });
  addText(s, "2026 Ashby Prize Hackathon", 72, 520, 420, 34, { size: 18, bold: true, color: C.gold });
  addText(s, "Built on PathGen, four NCSA pathology models, Delta, and Lumen", 72, 568, 550, 64, { size: 18, color: "#D3E7DF" });
  addText(s, "Research prototype", 1022, 666, 190, 24, { size: 11, bold: true, color: C.white, align: "right" });
  addNote(s, [
    "Project repository: https://github.com/osirais/histoprompt",
    "Hackathon challenge and criteria: https://cancer.illinois.edu/2026-ashby-prize-in-computational-science-hackathon/",
    "Cover image: public LC25000 sample stored in benchmarks/diagnosis-11/images with source and checksum metadata.",
  ]);
}


// 2. Team introduction
{
  const s = deck.slides.add();
  addTitle(s, "Five disciplines, one pathology workflow", 2, "Our team combines quantitative science, software, biomedical engineering, and domain-oriented evaluation.", "University of Illinois Urbana-Champaign");
  addText(s, "ASTRONOMY  ·  BIOENGINEERING  ·  COMPUTING  ·  PHYSICS  ·  MATHEMATICS", 86, 148, 1108, 34, { size: 17, bold: true, color: C.pink, align: "center", font: TITLE_FONT });
  const members = [
    ["Aditya Arunachalam", "Astronomy Department", "ASTRONOMY", C.plum, 15],
    ["David Wang", "Department of Bioengineering", "BIOENGINEERING", C.green2, 15],
    ["Orlando Sirais", "Siebel School of Computing and Data Science\nDepartment of Bioengineering", "COMPUTING + BIOENGINEERING", C.pink, 13],
    ["Jaidev Balaji", "Department of Physics", "PHYSICS", C.orange, 15],
    ["Karthik Sista", "Department of Mathematics", "MATHEMATICS", C.green, 15],
  ];
  members.forEach(([name, dept, field, color, deptSize], i) => {
    const topRow = i < 3;
    const x = topRow ? 66 + i * 396 : 264 + (i - 3) * 396;
    const y = topRow ? 214 : 424;
    addShape(s, "roundRect", x, y, 356, 166, C.white, C.line, 20);
    addShape(s, "rect", x, y, 10, 166, color, "none");
    addText(s, name, x + 30, y + 22, 300, 34, { size: 21, bold: true, color: C.ink, font: TITLE_FONT });
    addText(s, dept, x + 30, y + 66, 300, 54, { size: deptSize, color: C.muted });
    addText(s, field, x + 30, y + 128, 300, 24, { size: 13, bold: true, color, font: TITLE_FONT });
  });
  addText(s, "Together, we built and evaluated a single clinician-facing system.", 150, 618, 980, 36, { size: 19, bold: true, color: C.green, align: "center" });
  addNote(s, ["Team affiliations supplied by the user on 2026-10-19."]);
}


// 3. Concrete prompt transformation
{
  const s = deck.slides.add();
  addTitle(s, "What Lumen changes for each candidate", 3, "The baseline names the diagnosis. The enhanced version adds a short, visually discriminative morphology phrase.", "Source: saved case record 4cff975b-adbe-4ecf-9be5-365c715e2305_53792_26368.json");
  addText(s, "BASELINE PROMPT", 86, 164, 300, 30, { size: 16, bold: true, color: C.muted, font: TITLE_FONT });
  addShape(s, "roundRect", 76, 208, 500, 140, C.white, C.line, 20);
  addText(s, "a histopathology image showing\ncolon adenocarcinoma", 108, 244, 436, 76, { size: 24, bold: true, color: C.green, align: "center" });
  addText(s, "LUMEN + RETRIEVED EVIDENCE", 750, 164, 360, 30, { size: 16, bold: true, color: C.pink, font: TITLE_FONT });
  addShape(s, "roundRect", 704, 208, 500, 140, C.rose, C.pink, 20);
  addText(s, "colon adenocarcinoma with irregular glandular structures, cribriform patterns, desmoplastic response", 736, 232, 436, 92, { size: 21, bold: true, color: C.ink, align: "center" });
  addText(s, "→", 604, 248, 70, 54, { size: 36, bold: true, color: C.orange, align: "center", font: TITLE_FONT });
  const steps = [
    ["1", "Read case context", "The report and differential define what needs to be distinguished."],
    ["2", "Retrieve local evidence", "The system supplies relevant morphology and diagnostic context."],
    ["3", "Generate eight prompts", "Every candidate keeps its exact label and receives a concise feature phrase."],
  ];
  steps.forEach(([n, head, body], i) => {
    const x = 78 + i * 396;
    addText(s, n, x, 404, 40, 34, { size: 20, bold: true, color: i === 1 ? C.pink : C.green, font: TITLE_FONT });
    addText(s, head, x + 48, 402, 290, 36, { size: 20, bold: true, color: C.ink, font: TITLE_FONT });
    addText(s, body, x + 48, 454, 290, 86, { size: 17, color: C.muted });
  });
  addText(s, "HistoPrompt measures this transformation and learns which model–organ pairings benefit.", 138, 574, 1004, 52, { size: 18, bold: true, color: C.green, align: "center" });
  addNote(s, ["The quoted baseline and enhanced prompts are reproduced from a saved full-workflow case record."]);
}

// 4. Prototype
{
  const s = deck.slides.add();
  addTitle(s, "The prototype is organized around a single review", 4, "Inputs stay visible while model results, evidence, and next actions are reviewed.", "Source: saved replay in data/demo_replay.json; demo video");
  addImage(s, assets.uiResults, 70, 152, 1140, 500, "contain", "HistoPrompt results interface in saved replay mode");
  addShape(s, "roundRect", 83, 164, 220, 42, C.green, "none", 16);
  addText(s, "Public saved demo", 100, 170, 186, 28, { size: 15, bold: true, color: C.white });
  addNote(s, [
    "Screenshot extracted from demo/histoprompt-clinician-workflow-demo.mp4.",
    "The saved replay uses a public LC25000 case and makes no NCSA or Lumen requests.",
  ]);
}


// 5. Hackathon stack
{
  const s = deck.slides.add();
  addTitle(s, "Built on the full hackathon stack", 5, "We combined PathGen, RAG, Lumen, four pathology models, and Delta in one working product.", "Source: repository implementation; CCIL hackathon resources");
  const cards = [
    ["PathGen", "2,141 pathology cases\n8 TCGA cancer projects", C.pink],
    ["NCSA models", "MUSK · CONCH\nQuiltNet · PLIP", C.green2],
    ["Delta", "Hosted inference\nparallel model evaluation", C.orange],
    ["RAG + Lumen", "Retrieved pathology evidence\ncase-specific prompts", C.plum],
  ];
  cards.forEach(([head, body, color], i) => {
    const x = 66 + i * 296;
    addShape(s, "roundRect", x, 170, 260, 282, C.white, C.line, 22);
    addShape(s, "rect", x, 170, 260, 12, color, "none");
    addText(s, String(i + 1).padStart(2, "0"), x + 24, 206, 60, 38, { size: 22, bold: true, color, font: TITLE_FONT });
    addText(s, head, x + 24, 258, 212, 46, { size: 28, bold: true, color: C.ink, font: TITLE_FONT });
    addText(s, body, x + 24, 330, 212, 80, { size: 18, color: C.muted });
  });
  addText(s, "17,128", 128, 512, 210, 56, { size: 42, bold: true, color: C.green, font: TITLE_FONT, align: "center" });
  addText(s, "candidate-specific prompts", 100, 570, 266, 30, { size: 16, color: C.muted, align: "center" });
  addText(s, "17,128", 528, 512, 210, 56, { size: 42, bold: true, color: C.pink, font: TITLE_FONT, align: "center" });
  addText(s, "baseline / enhanced decisions", 492, 570, 282, 30, { size: 16, color: C.muted, align: "center" });
  addText(s, "2 hours", 928, 512, 210, 56, { size: 42, bold: true, color: C.orange, font: TITLE_FONT, align: "center" });
  addText(s, "end-to-end benchmark", 900, 570, 266, 30, { size: 16, color: C.muted, align: "center" });
  addNote(s, ["Every PathGen case produced eight Lumen prompts and eight model decisions: four baseline and four case-specific."]);
}

// 6. Product workflow

// 6. Manim workflow pulse
{
  const s = deck.slides.add();
  addFullBleedImage(s, assets.workflowPulse, "Manim workflow visualization tracing a clinical case through retrieval, Lumen, four-model comparison, and review");
  addText(s, "06", 1174, 678, 42, 20, { size: 10, bold: true, color: C.muted, align: "right" });
  addNote(s, ["Visualization authored in Manim Community v0.22.0 from the implemented clinical workflow."]);
}


// 7. Build inventory
{
  const s = deck.slides.add();
  addTitle(s, "Two days produced a complete, testable system", 7, "The project moved beyond a UI mockup into live model integration, scripted evaluation, and portable delivery.", "Source: repository history through f378abc");
  const stages = [
    ["Prototype", "Clinician case entry and review UI", C.green],
    ["Integration", "MUSK, CONCH, QuiltNet, PLIP, and Lumen", C.pink],
    ["Evaluation", "Small screens, held-out tuning, and full PathGen workflow", C.orange],
    ["Reproduction", "Checksums, resumable runs, saved replay, and reports", C.plum],
  ];
  stages.forEach(([head, body, color], i) => {
    const y = 160 + i * 104;
    addText(s, String(i + 1).padStart(2, "0"), 86, y + 4, 54, 34, { size: 19, bold: true, color, font: TITLE_FONT });
    addText(s, head, 158, y, 240, 40, { size: 23, bold: true, color: C.ink, font: TITLE_FONT });
    addText(s, body, 418, y, 540, 44, { size: 18, color: C.muted });
    if (i < stages.length - 1) addShape(s, "line", 112, y + 42, 1, 60, "none", C.line);
  });
  addShape(s, "roundRect", 990, 160, 206, 388, C.green, "none", 22);
  addText(s, "30", 1018, 184, 150, 54, { size: 40, bold: true, color: C.white, font: TITLE_FONT, align: "center" });
  addText(s, "commits", 1018, 238, 150, 26, { size: 16, color: "#D8E9E3", align: "center" });
  addShape(s, "line", 1022, 282, 142, 1, "none", "#2F665C");
  addText(s, "60", 1018, 308, 150, 54, { size: 40, bold: true, color: C.gold, font: TITLE_FONT, align: "center" });
  addText(s, "automated tests", 1018, 362, 150, 26, { size: 16, color: "#D8E9E3", align: "center" });
  addShape(s, "line", 1022, 406, 142, 1, "none", "#2F665C");
  addText(s, "1", 1018, 432, 150, 54, { size: 40, bold: true, color: C.white, font: TITLE_FONT, align: "center" });
  addText(s, "saved replay", 1018, 486, 150, 26, { size: 16, color: "#D8E9E3", align: "center" });
  addText(s, "Everything shown in this document is backed by saved code, data, or replayable artifacts in the private repository.", 142, 610, 996, 42, { size: 19, bold: true, color: C.green, align: "center" });
  addNote(s, ["Git history: 30 commits on main by two contributors as of 2026-10-19. Test suite: 60 passing tests."]);
}

// 8. Evaluation progression

// 8. Manim benchmark scale journey
{
  const s = deck.slides.add();
  addFullBleedImage(s, assets.scaleJourney, "Manim visualization of benchmark growth from 34 cases to the 2,141-case full workflow");
  addText(s, "08", 1174, 678, 42, 20, { size: 10, bold: true, color: C.muted, align: "right" });
  addNote(s, ["Visualization authored in Manim Community v0.22.0 from repository benchmark records."]);
}


// 9. Manim routing map
{
  const s = deck.slides.add();
  s.background.fill = "#0B201B";
  addFullBleedImage(s, assets.routingMap, "Manim routing diagram linking six cancer contexts to the model with the strongest observed prompt gain");
  addText(s, "09", 1174, 678, 42, 20, { size: 10, bold: true, color: "#A9BBB5", align: "right" });
  addNote(s, ["Visualization authored in Manim Community v0.22.0 from the saved 2,141-case PathGen benchmark."]);
}

// 10. Colon
{
  const s = deck.slides.add();
  addTitle(s, "Colon was the clearest multi-model success", 10, "Two independent pathology models improved substantially on the same 422-case PathGen cohort.", "Source: TCGA-COAD subset, pathgen-clinical-workflow results");
  addChart(s, "bar", {
    position: { left: 68, top: 160, width: 760, height: 414 },
    categories: ["CONCH", "QuiltNet-B-32"],
    series: [
      { name: "Baseline", values: [18.2, 3.6], fill: C.green },
      { name: "Case-specific", values: [46.7, 28.2], fill: C.pink },
    ],
    hasLegend: true,
    legend: { position: "bottom", textStyle: { fontSize: 14, fill: C.ink } },
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 55 },
    yAxis: { min: 0, max: 55, majorUnit: 10, numberFormatCode: "0\"%\"", majorGridlines: { style: "solid", fill: C.line, width: 1 }, textStyle: { fontSize: 14, fill: C.muted } },
    xAxis: { textStyle: { fontSize: 15, fill: C.ink } },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0.0", textStyle: { fontSize: 13, fill: C.ink, bold: true } },
    chartFill: C.paper, plotAreaFill: C.paper,
  });
  addMetric(s, "+28.4", "points · CONCH", 892, 184, 260, C.pink);
  addMetric(s, "+24.6", "points · QuiltNet", 892, 334, 260, C.green2);
  addSpeechBubble(s, "Both models improve on the same 422-case cohort.", 882, 492, 296, 72, C.green2, 802, 426);
  addNote(s, ["CONCH: 77/422 to 197/422. QuiltNet: 15/422 to 119/422."]);
}

// 11. Breast
{
  const s = deck.slides.add();
  addTitle(s, "Breast showed gains across three models", 11, "QuiltNet delivered the largest improvement, with CONCH and PLIP moving in the same direction.", "Source: TCGA-BRCA subset, pathgen-clinical-workflow results");
  addChart(s, "bar", {
    position: { left: 66, top: 160, width: 850, height: 420 },
    categories: ["QuiltNet-B-32", "CONCH", "PLIP"],
    series: [
      { name: "Baseline", values: [11.6, 25.9, 0.9], fill: C.green },
      { name: "Case-specific", values: [35.6, 34.7, 5.1], fill: C.pink },
    ],
    hasLegend: true,
    legend: { position: "bottom", textStyle: { fontSize: 14, fill: C.ink } },
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 50 },
    yAxis: { min: 0, max: 45, majorUnit: 10, numberFormatCode: "0\"%\"", majorGridlines: { style: "solid", fill: C.line, width: 1 }, textStyle: { fontSize: 14, fill: C.muted } },
    xAxis: { textStyle: { fontSize: 14, fill: C.ink } },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0.0", textStyle: { fontSize: 12, fill: C.ink, bold: true } },
    chartFill: C.paper, plotAreaFill: C.paper,
  });
  addText(s, "+24.1", 968, 194, 190, 54, { size: 38, bold: true, color: C.pink, font: TITLE_FONT });
  addText(s, "QuiltNet points", 968, 250, 190, 30, { size: 18, color: C.muted });
  addText(s, "+8.8", 968, 330, 190, 54, { size: 34, bold: true, color: C.green2, font: TITLE_FONT });
  addText(s, "CONCH points", 968, 384, 190, 30, { size: 18, color: C.muted });
  addText(s, "+4.2", 968, 464, 190, 54, { size: 34, bold: true, color: C.orange, font: TITLE_FONT });
  addText(s, "PLIP points", 968, 518, 190, 30, { size: 18, color: C.muted });
  addNote(s, ["QuiltNet: 25/216 to 77/216. CONCH: 56/216 to 75/216. PLIP: 2/216 to 11/216."]);
}

// 12. Rectal
{
  const s = deck.slides.add();
  addTitle(s, "MUSK reached 71.2% on rectal adenocarcinoma", 12, "Case-specific prompting added 24 correct classifications on the 156-case cohort.", "Source: TCGA-READ subset, pathgen-clinical-workflow results");
  addChart(s, "bar", {
    position: { left: 72, top: 178, width: 760, height: 366 },
    categories: ["MUSK"],
    series: [
      { name: "Baseline", values: [55.8], fill: C.green },
      { name: "Case-specific", values: [71.2], fill: C.pink },
    ],
    hasLegend: true,
    legend: { position: "bottom", textStyle: { fontSize: 14, fill: C.ink } },
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 48 },
    yAxis: { min: 0, max: 80, majorUnit: 20, numberFormatCode: "0\"%\"", majorGridlines: { style: "solid", fill: C.line, width: 1 }, textStyle: { fontSize: 14, fill: C.muted } },
    xAxis: { textStyle: { fontSize: 15, fill: C.ink } },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0.0", textStyle: { fontSize: 15, fill: C.ink, bold: true } },
    chartFill: C.paper, plotAreaFill: C.paper,
  });
  addShape(s, "roundRect", 888, 174, 286, 330, C.white, C.line, 22);
  addText(s, "+15.4", 918, 210, 228, 70, { size: 48, bold: true, color: C.pink, font: TITLE_FONT, align: "center" });
  addText(s, "percentage points", 918, 280, 228, 32, { size: 17, color: C.muted, align: "center" });
  addShape(s, "line", 926, 338, 210, 1, "none", C.line);
  addText(s, "87 → 111", 918, 366, 228, 50, { size: 31, bold: true, color: C.green, font: TITLE_FONT, align: "center" });
  addText(s, "correct cases", 918, 418, 228, 30, { size: 18, color: C.muted, align: "center" });
  addNote(s, ["MUSK exact result: 87/156 baseline to 111/156 case-specific."]);
}

// 13. Kidney and lung squamous
{
  const s = deck.slides.add();
  addTitle(s, "The routing pattern repeated in kidney and lung squamous", 13, "Kidney selected MUSK; lung squamous selected QuiltNet.", "Source: TCGA-KIRC and TCGA-LUSC subsets");
  const cards = [
    ["Kidney clear cell", "MUSK", "20.3%", "31.1%", "+10.7", "89 → 136 correct", C.green2],
    ["Lung squamous", "QuiltNet", "2.3%", "16.3%", "+14.1", "6 → 43 correct", C.pink],
  ];
  cards.forEach(([organ, model, before, after, gain, count, color], i) => {
    const x = 74 + i * 574;
    addShape(s, "roundRect", x, 160, 532, 406, C.white, C.line, 24);
    addShape(s, "rect", x, 160, 532, 12, color, "none");
    addText(s, organ, x + 34, 202, 460, 46, { size: 26, bold: true, color: C.ink, font: TITLE_FONT });
    addText(s, model, x + 34, 260, 180, 32, { size: 19, bold: true, color });
    addText(s, before, x + 36, 328, 150, 52, { size: 36, bold: true, color: C.muted, font: TITLE_FONT });
    addText(s, "→", x + 205, 331, 70, 48, { size: 32, bold: true, color: C.line, align: "center" });
    addText(s, after, x + 296, 328, 170, 52, { size: 36, bold: true, color, font: TITLE_FONT });
    addText(s, gain, x + 34, 414, 220, 54, { size: 38, bold: true, color, font: TITLE_FONT });
    addText(s, "points", x + 220, 431, 90, 28, { size: 17, color: C.muted });
    addText(s, count, x + 34, 496, 300, 30, { size: 17, bold: true, color: C.green });
  });
  addNote(s, ["Kidney MUSK: 89/438 to 136/438. Lung squamous QuiltNet: 6/263 to 43/263."]);
}

// 14. Prostate
{
  const s = deck.slides.add();
  addTitle(s, "CONCH crossed 72% on prostate adenocarcinoma", 14, "The case-specific prompt improved accuracy by 12 points across 208 PathGen cases.", "Source: TCGA-PRAD subset, pathgen-clinical-workflow results");
  addChart(s, "bar", {
    position: { left: 74, top: 176, width: 760, height: 368 },
    categories: ["CONCH"],
    series: [
      { name: "Baseline", values: [60.1], fill: C.green },
      { name: "Case-specific", values: [72.1], fill: C.pink },
    ],
    hasLegend: true,
    legend: { position: "bottom", textStyle: { fontSize: 14, fill: C.ink } },
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 48 },
    yAxis: { min: 0, max: 80, majorUnit: 20, numberFormatCode: "0\"%\"", majorGridlines: { style: "solid", fill: C.line, width: 1 }, textStyle: { fontSize: 14, fill: C.muted } },
    xAxis: { textStyle: { fontSize: 15, fill: C.ink } },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0.0", textStyle: { fontSize: 15, fill: C.ink, bold: true } },
    chartFill: C.paper, plotAreaFill: C.paper,
  });
  addMetric(s, "+12.0", "percentage points", 906, 200, 250, C.pink);
  addText(s, "125 → 150", 906, 370, 250, 58, { size: 34, bold: true, color: C.green, font: TITLE_FONT });
  addText(s, "correct cases", 906, 430, 220, 32, { size: 18, color: C.muted });
  addNote(s, ["CONCH exact result: 125/208 baseline to 150/208 case-specific."]);
}


// 15. Manim gain trajectories
{
  const s = deck.slides.add();
  s.background.fill = "#0B201B";
  addFullBleedImage(s, assets.gainTrajectories, "Manim before-to-after visualization of the three largest model-organ gains");
  addText(s, "15", 1174, 678, 42, 20, { size: 10, bold: true, color: "#A9BBB5", align: "right" });
  addNote(s, ["Visualization authored in Manim Community v0.22.0. Exact values come from the saved PathGen clinician-workflow benchmark."]);
}

// 16. Held-out tuning
{
  const s = deck.slides.add();
  addTitle(s, "Independent tuning added 4.4 points for two models", 16, "The search used a development set, confirmation set, and frozen 450-image held-out lung test for each model.", "Source: benchmarks/lc25000-tuning results");
  addChart(s, "bar", {
    position: { left: 78, top: 166, width: 760, height: 414 },
    categories: ["MUSK", "PLIP"],
    series: [
      { name: "Original", values: [89.6, 82.9], fill: C.green },
      { name: "Individually tuned", values: [94.0, 87.3], fill: C.pink },
    ],
    hasLegend: true,
    legend: { position: "bottom", textStyle: { fontSize: 14, fill: C.ink } },
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 55 },
    yAxis: { min: 70, max: 100, majorUnit: 10, numberFormatCode: "0\"%\"", majorGridlines: { style: "solid", fill: C.line, width: 1 }, textStyle: { fontSize: 14, fill: C.muted } },
    xAxis: { textStyle: { fontSize: 15, fill: C.ink } },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0.0", textStyle: { fontSize: 13, fill: C.ink, bold: true } },
    chartFill: C.paper, plotAreaFill: C.paper,
  });
  addMetric(s, "+20", "MUSK correct cases", 904, 204, 250, C.pink);
  addMetric(s, "+20", "PLIP correct cases", 904, 366, 250, C.green2);
  addSpeechBubble(s, "Each model received its own prompt search.", 902, 500, 274, 68, C.plum, 790, 436);
  addNote(s, ["MUSK: 403/450 to 423/450. PLIP: 373/450 to 393/450. Only the two models with held-out gains are shown on this success slide."]);
}

// 17. Multitask extension
{
  const s = deck.slides.add();
  addTitle(s, "One tuned template added 66 correct MUSK predictions", 17, "Held-out evaluation covered lung, colon, CRC9 tissue classes, and PatchCamelyon metastasis.", "Source: origin/validated-prompt-tuning at 5ae7423");
  addText(s, "Four tasks", 86, 176, 230, 38, { size: 24, bold: true, color: C.green, font: TITLE_FONT });
  addBullets(s, ["LC25000 lung", "LC25000 colon", "CRC9 tissue classes", "PatchCamelyon metastasis"], 86, 232, 296, 220, { size: 20 });
  addShape(s, "roundRect", 420, 164, 744, 386, C.white, C.line, 22);
  addText(s, "MUSK held-out total", 462, 198, 280, 34, { size: 20, bold: true, color: C.muted });
  addText(s, "1,444", 462, 252, 220, 60, { size: 42, bold: true, color: C.green, font: TITLE_FONT });
  addText(s, "baseline correct", 462, 312, 220, 30, { size: 16, color: C.muted });
  addText(s, "→", 704, 262, 70, 44, { size: 30, bold: true, color: C.line, align: "center" });
  addText(s, "1,510", 792, 252, 220, 60, { size: 42, bold: true, color: C.pink, font: TITLE_FONT });
  addText(s, "tuned correct", 792, 312, 220, 30, { size: 16, color: C.muted });
  addShape(s, "line", 462, 372, 650, 1, "none", C.line);
  addText(s, "+66 correct", 462, 404, 260, 50, { size: 34, bold: true, color: C.green2, font: TITLE_FONT });
  addText(s, "CRC9: 319 → 364 correct", 792, 412, 300, 38, { size: 21, bold: true, color: C.plum });
  addText(s, "Shared structure + task-specific language", 500, 490, 570, 32, { size: 18, bold: true, color: C.green, align: "center" });
  addText(s, "Shared structure and task-specific phrases produced the 66-case gain.", 164, 590, 952, 42, { size: 22, bold: true, color: C.pink, align: "center", font: TITLE_FONT });
  addNote(s, ["Separate research branch. Complete results in the branch cover MUSK across four tasks; this slide does not attribute the branch result to the other models."]);
}

// 18. Clinician value
{
  const s = deck.slides.add();
  addTitle(s, "One screen supports a fast clinical review", 18, "Inputs, model rankings, evidence, and next actions stay visible.", "Source: implemented UI and saved demo");
  addImage(s, assets.uiInput, 68, 154, 650, 470, "contain", "HistoPrompt clinician review input interface");
  const items = [
    ["Compare", "Four model perspectives on the same differential", C.green],
    ["Trace", "Prompts, retrieved evidence, and source passages", C.pink],
    ["Act", "A concise rationale and next review step", C.orange],
  ];
  items.forEach(([head, body, color], i) => {
    const y = 170 + i * 138;
    addText(s, String(i + 1).padStart(2, "0"), 770, y, 54, 32, { size: 18, bold: true, color, font: TITLE_FONT });
    addText(s, head, 838, y, 300, 38, { size: 25, bold: true, color: C.ink, font: TITLE_FONT });
    addText(s, body, 838, y + 48, 344, 54, { size: 18, color: C.muted });
  });
  addNote(s, ["The saved replay supports a reliable judge demo even when temporary event model services are unavailable."]);
}

if (true) {
// 19. Reproducibility
{
  const s = deck.slides.add();
  addTitle(s, "The full benchmark is reproducible", 19, "A reusable script preserves the inputs, outputs, checksums, and workflow state.", "Source: scripts, manifests, case records, workflow fingerprints, tests");
  const features = [
    ["2,141", "case records", "Exact report, prompts, model outputs, and review"],
    ["SHA-256", "checksums", "Images, reports, corpus, and workflow inputs"],
    ["1", "fingerprint", "Models, candidates, retrieval settings, and source"],
    ["resume", "safe reruns", "Completed matching cases are skipped"],
    ["report-only", "instant summaries", "No new endpoint calls required"],
    ["60", "automated tests", "Pipeline, tuning, backends, replay, and setup"],
  ];
  features.forEach(([value, head, body], i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 70 + col * 396;
    const y = 158 + row * 220;
    addShape(s, "roundRect", x, y, 350, 176, C.white, C.line, 20);
    const valueSize = value.length > 9 ? 22 : value.length > 6 ? 25 : 30;
    addText(s, value, x + 24, y + 18, 302, 42, { size: valueSize, bold: true, color: col === 1 ? C.pink : C.green, font: TITLE_FONT });
    addText(s, head, x + 24, y + 64, 302, 30, { size: 17, bold: true, color: C.ink });
    addText(s, body, x + 24, y + 106, 302, 48, { size: 15, color: C.muted });
  });
  addText(s, "One command runs the app. One command rebuilds the benchmark report.", 170, 614, 940, 34, { size: 21, bold: true, color: C.green, align: "center", font: TITLE_FONT });
  addNote(s, ["Repository includes setup.sh, run.sh, NCSA tunnel launcher, data manifests, exact benchmark outputs, a saved public replay, and the demo video."]);
}
}


// 20. Close
{
  const s = deck.slides.add();
  s.background.fill = C.green;
  addText(s, "HistoPrompt finds where prompting works", 74, 64, 1090, 66, { size: 38, bold: true, color: C.white, font: TITLE_FONT });
  addText(s, "and puts those gains into a usable workflow.", 74, 126, 1040, 66, { size: 38, bold: true, color: C.gold, font: TITLE_FONT });
  const wins = [
    ["+28.4", "CONCH · colon"],
    ["+24.1", "QuiltNet · breast"],
    ["+15.4", "MUSK · rectal"],
  ];
  wins.forEach(([value, label], i) => {
    const x = 74 + i * 300;
    addShape(s, "roundRect", x, 242, 262, 150, "#174D44", "#2E665C", 22);
    addText(s, value, x + 22, 270, 218, 58, { size: 39, bold: true, color: C.white, font: TITLE_FONT, align: "center" });
    addText(s, label, x + 22, 336, 218, 30, { size: 16, bold: true, color: "#D8E9E3", align: "center" });
  });
  addShape(s, "roundRect", 1000, 242, 206, 294, C.white, "none", 24);
  addText(s, "Built with", 1026, 276, 154, 34, { size: 21, bold: true, color: C.pink, font: TITLE_FONT });
  addText(s, "PathGen\nDelta\nMUSK\nCONCH\nQuiltNet\nPLIP\nLumen", 1026, 328, 154, 184, { size: 18, bold: true, color: C.ink, align: "center" });
  addText(s, "2,141 cases · 8 cancers · 4 models · 1 reproducible workflow", 76, 458, 830, 44, { size: 24, bold: true, color: C.white, font: TITLE_FONT });
  addText(s, "Next: prospective confirmation of the six model-aware routing targets.", 76, 520, 820, 42, { size: 19, color: "#D8E9E3" });
  addText(s, "github.com/osirais/histoprompt", 76, 648, 560, 28, { size: 16, bold: true, color: C.gold });
  addText(s, "Clinician prototype + saved demo + full benchmark", 760, 648, 444, 28, { size: 16, color: "#D8E9E3", align: "right" });
  addNote(s, ["Repository: https://github.com/osirais/histoprompt", "Primary benchmark: benchmarks/pathgen-clinical-workflow/RESULTS.md", "Demo: demo/histoprompt-clinician-workflow-demo.mp4"]);
}

await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
await fs.mkdir(path.dirname(finalPptx), { recursive: true });
await fs.mkdir(path.dirname(canonicalPptx), { recursive: true });

for (const [index, slide] of deck.slides.items.entries()) {
  const png = await deck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(previewDir, `slide-${String(index + 1).padStart(2, "0")}.png`), new Uint8Array(await png.arrayBuffer()));
}

const stagingDir = path.join(buildDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, `candidate-${process.pid}.pptx`);
await (await PresentationFile.exportPptx(deck)).save(candidatePath);

const result = await finalizePresentation({
  explicitTotalSlideCount: 20,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [10, 11, 12, 14, 16],
  materializeLiteralChartWorkbooks: true,
  workspaceDir,
  candidatePath,
  finalPath: finalPptx,
  pythonExecutable: runtimePython,
  integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
  ],
  fontPolicy: { basis: "design", families: [TITLE_FONT, BODY_FONT] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(buildDir, "HistoPrompt_Hackathon_Deck.validation.json"),
});

await fs.copyFile(finalPptx, canonicalPptx);
await Promise.all([fs.rm(finalPptx, { force: true }), fs.rm(candidatePath, { force: true })]);

console.log(JSON.stringify({ finalPptx: canonicalPptx, result }, null, 2));
