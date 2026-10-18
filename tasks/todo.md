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
