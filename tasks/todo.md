# Benchmark plan

- [x] Define a small, source-traceable pathology benchmark spanning multiple disease families and candidate sets.
- [x] Add deterministic prompt strategies: label-only, generic histology, curated morphology, and evidence-generated features.
- [x] Build a standard-library benchmark runner that caches source images, calls the live MUSK endpoint, and saves raw JSON plus a Markdown summary.
- [x] Add unit tests for strategy construction, accuracy aggregation, failure handling, and answer-leakage prevention.
- [x] Run the benchmark through the Delta tunnel, document dataset and hosted-API limitations, and add the exact reproduction command to the README.
- [x] Run the full checks, self-review the diff and results, commit, push, and verify CI.

Risks: the hackathon API returns only one label and score per image; the benchmark will be small and heterogeneous; source images must be public and attributable; no result will be described as clinical validation.

Observed pilot result: label-only and generic prompts were 8/8; curated and evidence-generated prompts were 7/8 because both flipped the lung adenocarcinoma example to squamous cell carcinoma. The higher returned top score did not correspond to higher accuracy.

## Report readability follow-up

- [x] State the tested organs, conditions, benign controls, and candidate sets before showing scores.
- [x] Put original MUSK and enhanced MUSK in one clear side-by-side table.
- [x] Replace the raw strategy dump with clinical-group results and only the cases where predictions changed.
- [x] Expand the benchmark from 8 to 34 fixed images across lung, colon, infectious esophagitis, and skin cancer.
- [x] Store the exact image bytes, SHA-256 checksums, source links, selection method, and license notes in the repository.
- [x] Explain why sample counts remain small and specify the next credible benchmark.
- [x] Run final checks, self-review, commit, push, and verify CI.

## 1,000-image benchmark

- [x] Add an additive batched remote-inference interface and tests for response ordering and failures.
- [x] Generate a fixed, balanced 1,000-image LC25000 manifest with local image bytes and checksums.
- [x] Update the benchmark runner to process same-family images in configurable batches and record latency.
- [x] At the user's direction, run Original and Enhanced MUSK on the fixed 600-image lung subset and save a readable report.
- [x] Verify image checksums, tests, results, repository size, and credentials; then commit, push, and verify CI.

Risks: the hosted endpoint may limit request size or GPU batch size; LC25000 contains augmented derivatives and is not a patient-independent clinical dataset; batching must preserve image/result order; a failed batch must remain auditable rather than silently dropping cases.

## Benchmark-informed enhancement redesign

- [x] Add and test safer prompt variants that preserve MUSK's generic pretraining template.
- [ ] Benchmark the variants on the same fixed 600 images and select behavior from measured accuracy. The NCSA endpoint timed out during the exploratory appended pass; the completed generic/evidence comparison remains the trusted result.
- [x] Keep harmful morphology enrichment out of the primary classifier unless a variant beats the generic baseline.
- [ ] Use retrieval and Lumen for evidence review and structured report drafting after MUSK inference.
- [x] Update the interface and documentation so the primary result and experimental evidence layer are unambiguous.
- [ ] Run full verification, self-review, commit, push, and verify CI.

Risks: repeated runs can drift if the remote MUSK service changes; LC25000 augmentation prevents patient-independent conclusions; report drafting must stay explicitly research-only and must not invent findings absent from the supplied report or model output.

## NCSA CONCH integration

- [x] Add an opt-in remote CONCH adapter using the NCSA `/classify` contract.
- [x] Add a second SSH tunnel/configuration path without changing the MUSK default.
- [ ] Show CONCH's result alongside MUSK and cover the adapter with offline tests.

Risk: the CONCH host, port, and bearer key are supplied by the hackathon organizers and must remain local-only.

## Organized cross-pathology benchmark

- [x] Make one benchmark index the clear entry point, separating active suites from archived exploratory runs.
- [x] Preserve the 34-image diagnosis suite with its images, checksums, sources, and frozen prompts in one directory.
- [x] Generalize the benchmark runner and report wording from MUSK-only to any hosted model without exposing credentials.
- [x] Reject PanNuke as the broad benchmark because its tissue-origin task does not match the system.
- [x] Select PathMMU as the broad diagnosis/reasoning benchmark target.
- [ ] Obtain PathMMU dataset approval and build its fixed validation/test manifest.
- [ ] Run MUSK, CONCH, QuiltNet, and PLIP with original and retrieval-enhanced answer-option prompts.
- [x] Generate one readable cross-model summary for the currently valid results.
- [x] Add a one-command suite runner and generated aggregate report.
- [x] Run final checks and self-review.

Risks: 34 images across 11 labels are useful for broad smoke coverage but not clinical validation; several families have only one or two images per label; within-family candidate sets do not measure unrestricted diagnosis; model-specific tuning remains independently validated only for the LC25000 lung task.

## Full available NCSA PathGen benchmark

- [x] Pull `main`, fetch every remote branch, and audit the new validated prompt-tuning version before testing it.
- [x] Inventory the PathGen assets that are actually materialized on NCSA.
- [x] Port per-model base-template selection from `validated-prompt-tuning` into the current four-model runner.
- [x] Add a frozen, auditable manifest for all 2,141 available PathGen PNGs and their 8 TCGA project labels.
- [x] Select and freeze one base template independently for MUSK, CONCH, QuiltNet, and PLIP using only the separate LC25000 tuning and confirmation sets.
- [x] Evaluate the original and selected-template prompts on every available PathGen PNG exactly once per model.
- [x] Produce overall, per-project, per-slide, confusion, timing, completeness, and provenance reports.
- [x] Run final tests, self-review, commit, push, and verify CI.

Risks: the materialized NCSA pixel set is 2,141 tiles from only 10 slides, so tile counts must not be mistaken for patient-level sample size; PathGen captions are generated and are not used as ground-truth labels; the larger 1,620,876-region inventory currently has precomputed CONCH features but not raw pixels for a fair four-model image benchmark.

## Correct full per-model tuning run

- [x] Re-read `validated-prompt-tuning`'s `HOW_TO_RUN.md` and identify why the previous run skipped phrase tuning.
- [x] Pull and fetch all branches; confirm the four model services, Lumen, and 1,800 LC25000 tuning/confirmation images are available.
- [ ] Run both documented stages independently for MUSK, CONCH, QuiltNet, and PLIP: base-template selection followed by Lumen phrase tuning.
- [ ] Keep PathGen evaluation-only and clearly distinguish lung-tuned prompts from broad multi-organ evaluation.
- [ ] Update the PathGen runner to apply accepted tuned phrases when a benchmark label matches, and label untuned labels honestly.
- [ ] Run focused and full tests, rerun the affected benchmark conditions, replace the misleading report, commit, push, and verify CI.

Risks: the documented tuning corpus contains only three lung labels, so it cannot honestly claim to tune breast, colon, kidney, brain, prostate, or rectal prompts. PathGen must not be reused as tuning data if it remains the held-out benchmark.

Status: stopped at the user's direction. The target benchmark is the live clinician-style workflow, not offline prompt selection.

## Full PathGen clinician-workflow benchmark

- [x] Stop the unfinished offline prompt-tuning and selected-prompt PathGen processes.
- [x] Prove one PathGen case through the current live pipeline using its image, simulated report, eight candidates, retrieval, Lumen prompt generation, image-model inference, and Lumen review.
- [ ] Extract the clinician workflow into reusable, tested steps shared by the live app and benchmark runner.
- [ ] Include MUSK, CONCH, QuiltNet, and PLIP in the same per-case comparison without model-specific offline tuning.
- [ ] Add a resumable runner that verifies all image and report checksums and processes all 2,141 cases.
- [ ] Record image-only baseline, case-specific prompt result, and final Lumen-review classification separately for every case and model.
- [ ] Run a small balanced smoke set, inspect the saved prompts and reviews, then run every materialized PathGen case.
- [ ] Generate a readable overall, per-project, per-slide, latency, and failure report.
- [x] Add a reproducible organ-by-model table with baseline accuracy, case-specific accuracy, percentage-point change, and paired fixed/broken counts.
- [ ] Run the full checks and self-review. Do not commit or push unless the user explicitly asks.

Risks: PathGen supplies generated image captions rather than authentic clinician reports, and some captions name the organ or likely diagnosis. They are acceptable as simulated workflow inputs but can make final-review accuracy much easier than image-only classification. The report must therefore keep the three stages separate and preserve the exact supplied text for auditability.

## Clinician-workflow UI and recorded demo

- [x] Preserve a pre-change end-to-end smoke run using a public LC25000 image and the built-in de-identified report.
- [ ] Align the live app with the benchmarked clinician workflow: eight candidate-aware prompts, four available vision models, baseline versus case-specific output, and a separate Lumen evidence review.
- [ ] Replace diagnosis/confidence framing with explicit research-only ranking scores, agreement/disagreement, limitations, and human-review guidance.
- [ ] Rework the responsive interface for a practical single-case review and a polished full-window demonstration.
- [ ] Add focused behavior tests, run the full suite, and execute a post-change browser smoke test.
- [ ] Produce a scripted, cursor-free demo video from the verified live workflow and keep all artifacts local.

Constraints: use only de-identified or public research data; do not commit or push; do not imply clinical validation; preserve the current benchmark process and its saved outputs.

## Local saved-demo replay

- [x] Add an explicit environment-gated replay mode that never calls expired NCSA or Lumen services.
- [x] Reuse one exact public benchmark image and its saved four-model outputs.
- [x] Let “Load demo case” populate the image, findings, and differential in one click.
- [x] Mark the interface as a saved replay rather than claiming the remote models are live.
- [x] Add focused tests, document the one-command launch, and run the full suite.

Constraints: replay mode must stay off by default; it must reject arbitrary cases rather than attach saved outputs to a different image; do not commit or push unless explicitly requested again.
