# Complete materialized NCSA PathGen benchmark

Model: **MUSK**
Cases: **2,141 tiles from 10 slides and 8 TCGA projects**
Selected template: `an H&E stained image of {label}.`

## Overall comparison

| Prompt set | Correct | Tile accuracy | Macro project accuracy | Inference time |
|---|---:|---:|---:|---:|
| Original | 868/2,141 | 40.5% | 44.7% | 126.4 s |
| Selected Template | 838/2,141 | 39.1% | 43.6% | 125.2 s |

The selected template changed accuracy by **-1.4 percentage points**: 64 tiles fixed and 94 broken.

## Per-project results

| TCGA project | Tiles | Original | Selected template | Change |
|---|---:|---:|---:|---:|
| TCGA-BRCA | 216 | 26.9% | 29.2% | +2.3 points |
| TCGA-COAD | 422 | 30.6% | 26.8% | -3.8 points |
| TCGA-KIRC | 438 | 20.1% | 18.0% | -2.1 points |
| TCGA-LGG | 204 | 85.3% | 83.8% | -1.5 points |
| TCGA-LUAD | 234 | 54.3% | 44.9% | -9.4 points |
| TCGA-LUSC | 263 | 52.9% | 62.0% | +9.1 points |
| TCGA-PRAD | 208 | 31.7% | 25.0% | -6.7 points |
| TCGA-READ | 156 | 55.8% | 59.0% | +3.2 points |

## Interpretation boundary

This run includes every PNG in the materialized NCSA PathGen collection. It is a tile-level engineering benchmark, not a patient-level clinical validation: the 2,141 tiles come from only 10 whole slides, and PathGen captions are generated auxiliary text rather than expert ground truth. Ground truth here is the TCGA cancer-project assignment recorded independently in the frozen full-PathGen manifest.
