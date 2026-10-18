# Complete materialized NCSA PathGen benchmark

Model: **QuiltNet-B-32**
Cases: **2,141 tiles from 10 slides and 8 TCGA projects**
Selected template: `a histopathology slide showing {label}`

## Overall comparison

| Prompt set | Correct | Tile accuracy | Macro project accuracy | Inference time |
|---|---:|---:|---:|---:|
| Original | 695/2,141 | 32.5% | 41.8% | 88.8 s |
| Selected Template | 761/2,141 | 35.5% | 40.3% | 88.0 s |

The selected template changed accuracy by **+3.1 percentage points**: 169 tiles fixed and 103 broken.

## Per-project results

| TCGA project | Tiles | Original | Selected template | Change |
|---|---:|---:|---:|---:|
| TCGA-BRCA | 216 | 11.6% | 5.1% | -6.5 points |
| TCGA-COAD | 422 | 3.6% | 27.7% | +24.2 points |
| TCGA-KIRC | 438 | 8.4% | 13.7% | +5.3 points |
| TCGA-LGG | 204 | 93.6% | 92.6% | -1.0 points |
| TCGA-LUAD | 234 | 69.7% | 68.4% | -1.3 points |
| TCGA-LUSC | 263 | 2.3% | 6.8% | +4.6 points |
| TCGA-PRAD | 208 | 60.1% | 72.1% | +12.0 points |
| TCGA-READ | 156 | 85.3% | 35.9% | -49.4 points |

## Interpretation boundary

This run includes every PNG in the materialized NCSA PathGen collection. It is a tile-level engineering benchmark, not a patient-level clinical validation: the 2,141 tiles come from only 10 whole slides, and PathGen captions are generated auxiliary text rather than expert ground truth. Ground truth here is the TCGA cancer-project assignment recorded independently in the frozen full-PathGen manifest.
