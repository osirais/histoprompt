# Complete materialized NCSA PathGen benchmark

Every model was evaluated on all 2,141 materialized PathGen PNGs from 10 slides and 8 TCGA projects. The selected base template for each model was frozen using separate LC25000 tuning and confirmation sets.

| Model | Original | Selected template | Change | Fixed / broken | Macro-project selected | Time |
|---|---:|---:|---:|---:|---:|---:|
| MUSK | 868/2,141 (40.5%) | 838/2,141 (39.1%) | -1.4 points | 64 / 94 | 43.6% | 4.2 min |
| CONCH | 1,091/2,141 (51.0%) | 1,164/2,141 (54.4%) | +3.4 points | 277 / 204 | 54.8% | 3.9 min |
| QuiltNet-B-32 | 695/2,141 (32.5%) | 761/2,141 (35.5%) | +3.1 points | 169 / 103 | 40.3% | 2.9 min |
| PLIP | 904/2,141 (42.2%) | 827/2,141 (38.6%) | -3.6 points | 43 / 120 | 37.2% | 3.0 min |

## Frozen prompt selected for each model

| Model | Selected template |
|---|---|
| MUSK | `an H&E stained image of {label}.` |
| CONCH | `a histopathological photograph showing {label}.` |
| QuiltNet-B-32 | `a histopathology slide showing {label}` |
| PLIP | `pathology tissue showing {label}` |

## Results by TCGA project

Each cell is original accuracy → selected-template accuracy (percentage-point change).

| Project | Tiles | MUSK | CONCH | QuiltNet-B-32 | PLIP |
|---|---:|---:|---:|---:|---:|
| TCGA-BRCA | 216 | 26.9% → 29.2% (+2.3) | 25.9% → 15.3% (-10.6) | 11.6% → 5.1% (-6.5) | 0.9% → 2.3% (+1.4) |
| TCGA-COAD | 422 | 30.6% → 26.8% (-3.8) | 18.2% → 51.2% (+32.9) | 3.6% → 27.7% (+24.2) | 38.6% → 38.4% (-0.2) |
| TCGA-KIRC | 438 | 20.1% → 18.0% (-2.1) | 63.0% → 39.7% (-23.3) | 8.4% → 13.7% (+5.3) | 59.8% → 48.9% (-11.0) |
| TCGA-LGG | 204 | 85.3% → 83.8% (-1.5) | 98.5% → 96.6% (-2.0) | 93.6% → 92.6% (-1.0) | 93.6% → 97.5% (+3.9) |
| TCGA-LUAD | 234 | 54.3% → 44.9% (-9.4) | 77.4% → 92.3% (+15.0) | 69.7% → 68.4% (-1.3) | 3.8% → 6.4% (+2.6) |
| TCGA-LUSC | 263 | 52.9% → 62.0% (+9.1) | 62.0% → 56.3% (-5.7) | 2.3% → 6.8% (+4.6) | 38.4% → 29.3% (-9.1) |
| TCGA-PRAD | 208 | 31.7% → 25.0% (-6.7) | 60.1% → 84.1% (+24.0) | 60.1% → 72.1% (+12.0) | 82.7% → 74.5% (-8.2) |
| TCGA-READ | 156 | 55.8% → 59.0% (+3.2) | 7.7% → 3.2% (-4.5) | 85.3% → 35.9% (-49.4) | 2.6% → 0.0% (-2.6) |

## What this measures

This is an eight-way TCGA cancer-project classification stress test over every PathGen tile that was physically available in the shared NCSA PathGen collection. It compares each model's original generic prompt with that model's independently selected base template.

## Limitations

- The 2,141 tiles come from only 10 whole slides, so tile-level confidence intervals would overstate the effective sample size.
- PathGen captions are generated auxiliary text and are not used as labels or model inputs here.
- Ground truth is TCGA project membership. Some distinctions, especially colon versus rectal adenocarcinoma, are not reliably identifiable from an isolated tile.
- The separate 1,620,876-region PathGen inventory is not a four-model image benchmark because NCSA currently supplies its raw pixels only for this 2,141-tile collection; the larger shared store contains precomputed CONCH embeddings.
