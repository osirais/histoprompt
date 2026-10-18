# Benchmark guide

Start with [`RESULTS.md`](RESULTS.md) for the readable comparison. The benchmark directory is organized by purpose rather than by run date.

## Active suites

| Suite | Question it answers | Scope | Status |
|---|---|---|---|
| [`diagnosis-11/`](diagnosis-11/) | Does evidence-enriched wording improve disease discrimination? | 34 fixed images; 11 labels; 4 clinical differentials; all four hosted models | Small smoke test |
| [`lc25000-tuning/`](lc25000-tuning/) | Does model-specific prompt search improve held-out lung accuracy? | Separate tuning, confirmation, and 450-image test sets per model | Prompt-selection experiment |
| [`lc25000-1000/`](lc25000-1000/) | Can a larger balanced run be reproduced? | 1,000 stored lung and colon tiles | Stress-test dataset |
| [`lc25000-600/`](lc25000-600/) | What happened in the original MUSK RAG comparison? | 600 stored lung tiles | Preserved baseline |
| [`pathgen-ncsa/`](pathgen-ncsa/) | Does each model's independently selected template transfer across organs? | Every one of 2,141 materialized NCSA PathGen tiles; 8 TCGA projects | Full available-pixel benchmark |

The `archive/` directory contains exploratory runs that should not be treated as current evidence:

- `archive/lung-prompt-screens/` contains the successive rapid prompt prototypes.
- `archive/shared-prompt-comparisons/` contains the old experiment that applied one MUSK-selected phrase to every model. It was superseded by independent per-model tuning.

## Broad-organ benchmark target

[PathMMU](https://huggingface.co/datasets/jamessyx/PathMMU) is the replacement broad benchmark. It was designed for pathology image understanding and reasoning and covers multiple organ systems and pathology specialties. Its 33,428 multiple-choice questions are paired with 24,067 images, answer choices, correct answers, and explanations.

PathMMU requires separate approval. MUSK model approval does not grant dataset access. The Hugging Face account email must match the email submitted through PathMMU's access form. The maintainers state that requests are processed in one to two days.

After access is available, the suite will use the official validation/test split and report:

- original image-and-option scoring for each hosted model;
- retrieval/Lumen-enhanced option scoring without exposing the correct answer;
- overall, organ-system, question-type, and source-subset accuracy;
- answer/explanation quality for the Lumen reasoning layer;
- fixed sample IDs, dataset revision, configuration, and checksums.

The removed PanNuke experiment is not an active benchmark because PanNuke is intended for nucleus segmentation and tissue-origin labels, not diagnosis, retrieval, or report reasoning.

## Reproduce the current diagnosis smoke test

With the Delta tunnel open, run and report all four models with one command:

```bash
uv run python scripts/run_benchmark_suite.py
```

To rerun one model only:

```bash
uv run python scripts/run_benchmark.py \
  --manifest benchmarks/diagnosis-11/manifest.json \
  --model musk \
  --batch-size 64 \
  --strategies generic evidence_generated
```

Replace `musk` with `conch`, `quiltnet`, or `plip`. The evidence-generated prompts are frozen in `diagnosis-11/prompts/evidence-generated.json`, so Lumen is not called during reruns.

To regenerate all readable Markdown from saved raw JSON without calling a hosted model:

```bash
uv run python scripts/run_benchmark_suite.py --report-only
```
