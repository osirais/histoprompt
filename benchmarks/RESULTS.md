# Benchmark results

## Current evidence

- **Named-diagnosis smoke test:** 34 images covering 11 labels in four clinical differentials.
- **Prompt tuning:** independent candidate search, confirmation, and a 450-image held-out lung test for each model.
- **Broad-organ diagnosis/reasoning:** pending PathMMU dataset access.

The previous PanNuke tissue-origin experiment was removed because it did not match HistoPrompt's diagnosis and reasoning task. The current numbers are useful but do not yet establish performance across pathology.

## 11-label diagnosis smoke test

The generic prompt beat the frozen evidence-enriched descriptions for all four models.

| Model | Generic prompt | Evidence-enriched prompt | Change |
|---|---:|---:|---:|
| MUSK | 33/34 (97.1%) | 31/34 (91.2%) | -5.9 points |
| CONCH | 32/34 (94.1%) | 28/34 (82.4%) | -11.8 points |
| QuiltNet-B-32 | 29/34 (85.3%) | 28/34 (82.4%) | -2.9 points |
| PLIP | 26/34 (76.5%) | 25/34 (73.5%) | -2.9 points |

### Generic accuracy by clinical group

| Clinical group | Images | MUSK | CONCH | QuiltNet-B-32 | PLIP |
|---|---:|---:|---:|---:|---:|
| lung histopathology | 15 | 14/15 | 15/15 | 15/15 | 14/15 |
| colon histopathology | 10 | 10/10 | 8/10 | 8/10 | 7/10 |
| infectious esophagitis | 6 | 6/6 | 6/6 | 4/6 | 3/6 |
| skin cancer histopathology | 3 | 3/3 | 3/3 | 2/3 | 2/3 |

The per-model reports and every prediction are under [`diagnosis-11/results/`](diagnosis-11/results/). Several labels have only one or two examples, so this suite is only a smoke test.

## Model-specific lung prompt tuning

Each model ran its own candidate search and validation. The table below is the final held-out test; phrases were not shared between models.

| Model | Original generic | Short template | Individually tuned | Tuned vs original | Run time |
|---|---:|---:|---:|---:|---:|
| MUSK | 403/450 (89.6%) | 416/450 (92.4%) | 423/450 (94.0%) | +4.4 points | 20.1 min |
| CONCH | 423/450 (94.0%) | 293/450 (65.1%) | 407/450 (90.4%) | -3.6 points | 20.9 min |
| QuiltNet-B-32 | 387/450 (86.0%) | 359/450 (79.8%) | 376/450 (83.6%) | -2.4 points | 14.6 min |
| PLIP | 373/450 (82.9%) | 374/450 (83.1%) | 393/450 (87.3%) | +4.4 points | 17.0 min |

CONCH, QuiltNet, and PLIP were launched together and took about 21 minutes of wall-clock time. The earlier MUSK run took about 20 minutes. The per-model minutes above are measured model runtimes, not a sequential wall-clock total.

The selected phrases and search logs are in [`lc25000-tuning/results/`](lc25000-tuning/results/). “Tuned” means the search found the best candidate that passed its internal gates; it does not guarantee improvement over the original generic prompt.

## Replacement broad benchmark

PathMMU is the replacement target because it was designed for pathology image understanding and reasoning across multiple organ systems and pathology specialties. It provides answer options, correct answers, and explanations, which support direct baseline-versus-retrieval comparisons without inventing labels.

PathMMU is separately gated. MUSK model approval does not grant dataset access. After access is approved, the benchmark will use the official validation/test split and will report overall, organ-system, question-type, and source-subset accuracy.

## What the current results say

1. Prompt wording is model-specific. A phrase that helps MUSK can hurt CONCH or QuiltNet.
2. Longer evidence-derived descriptions are not automatically better. They reduced accuracy in every model on the small diagnosis screen.
3. The lung results show that prompt tuning can help, but they cannot be generalized across organs or diseases.
4. A broad conclusion must wait for a benchmark designed for diagnosis and visual reasoning, rather than tissue-origin or segmentation data.
