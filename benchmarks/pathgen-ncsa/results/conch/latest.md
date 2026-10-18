# Complete materialized NCSA PathGen benchmark

Model: **CONCH**
Cases: **2,141 tiles from 10 slides and 8 TCGA projects**
Selected template: `a histopathological photograph showing {label}.`

## Overall comparison

| Prompt set | Correct | Tile accuracy | Macro project accuracy | Inference time |
|---|---:|---:|---:|---:|
| Original | 1,091/2,141 | 51.0% | 51.6% | 118.2 s |
| Selected Template | 1,164/2,141 | 54.4% | 54.8% | 118.0 s |

The selected template changed accuracy by **+3.4 percentage points**: 277 tiles fixed and 204 broken.

## Per-project results

| TCGA project | Tiles | Original | Selected template | Change |
|---|---:|---:|---:|---:|
| TCGA-BRCA | 216 | 25.9% | 15.3% | -10.6 points |
| TCGA-COAD | 422 | 18.2% | 51.2% | +32.9 points |
| TCGA-KIRC | 438 | 63.0% | 39.7% | -23.3 points |
| TCGA-LGG | 204 | 98.5% | 96.6% | -2.0 points |
| TCGA-LUAD | 234 | 77.4% | 92.3% | +15.0 points |
| TCGA-LUSC | 263 | 62.0% | 56.3% | -5.7 points |
| TCGA-PRAD | 208 | 60.1% | 84.1% | +24.0 points |
| TCGA-READ | 156 | 7.7% | 3.2% | -4.5 points |

## Interpretation boundary

This run includes every PNG in the materialized NCSA PathGen collection. It is a tile-level engineering benchmark, not a patient-level clinical validation: the 2,141 tiles come from only 10 whole slides, and PathGen captions are generated auxiliary text rather than expert ground truth. Ground truth here is the TCGA cancer-project assignment recorded independently in the frozen full-PathGen manifest.
