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
