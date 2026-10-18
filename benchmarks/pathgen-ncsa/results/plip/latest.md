# Complete materialized NCSA PathGen benchmark

Model: **PLIP**
Cases: **2,141 tiles from 10 slides and 8 TCGA projects**
Selected template: `pathology tissue showing {label}`

## Overall comparison

| Prompt set | Correct | Tile accuracy | Macro project accuracy | Inference time |
|---|---:|---:|---:|---:|
| Original | 904/2,141 | 42.2% | 40.1% | 90.0 s |
| Selected Template | 827/2,141 | 38.6% | 37.2% | 89.1 s |

The selected template changed accuracy by **-3.6 percentage points**: 43 tiles fixed and 120 broken.

## Per-project results

| TCGA project | Tiles | Original | Selected template | Change |
|---|---:|---:|---:|---:|
| TCGA-BRCA | 216 | 0.9% | 2.3% | +1.4 points |
| TCGA-COAD | 422 | 38.6% | 38.4% | -0.2 points |
| TCGA-KIRC | 438 | 59.8% | 48.9% | -11.0 points |
| TCGA-LGG | 204 | 93.6% | 97.5% | +3.9 points |
| TCGA-LUAD | 234 | 3.8% | 6.4% | +2.6 points |
| TCGA-LUSC | 263 | 38.4% | 29.3% | -9.1 points |
| TCGA-PRAD | 208 | 82.7% | 74.5% | -8.2 points |
| TCGA-READ | 156 | 2.6% | 0.0% | -2.6 points |

## Interpretation boundary

This run includes every PNG in the materialized NCSA PathGen collection. It is a tile-level engineering benchmark, not a patient-level clinical validation: the 2,141 tiles come from only 10 whole slides, and PathGen captions are generated auxiliary text rather than expert ground truth. Ground truth here is the TCGA cancer-project assignment recorded independently in the frozen full-PathGen manifest.
