# PathGen clinician-workflow benchmark

Completed cases: **2,141**

Each case followed the same path: image plus simulated report and all eight candidate labels, local evidence retrieval, Lumen case-specific prompt generation, all configured pathology image models, and a final Lumen evidence review.

## Accuracy by decision layer

| Model or review layer | Image-only baseline | Case-specific prompts | Change | Fixed / broken |
|---|---:|---:|---:|---:|
| CONCH | 1,091/2,141 (51.0%) | 983/2,141 (45.9%) | -5.0 points | 305 / 413 |
| MUSK | 868/2,141 (40.5%) | 871/2,141 (40.7%) | +0.1 points | 199 / 196 |
| PLIP | 904/2,141 (42.2%) | 558/2,141 (26.1%) | -16.2 points | 76 / 422 |
| QuiltNet-B-32 | 695/2,141 (32.5%) | 729/2,141 (34.0%) | +1.6 points | 288 / 254 |
| Final Lumen review | — | 609/2,141 (28.4%) | — | — |

## Change by organ and model

Positive values mean that case-specific prompts improved accuracy. Negative values mean that they reduced accuracy. Each value is the percentage-point change from the image-only baseline.

| Organ and disease | Cases | CONCH | MUSK | PLIP | QuiltNet-B-32 |
|---|---:|---:|---:|---:|---:|
| Breast invasive carcinoma (TCGA-BRCA) | 216 | +8.8 | -8.8 | +4.2 | +24.1 |
| Colon adenocarcinoma (TCGA-COAD) | 422 | +28.4 | -12.3 | -36.3 | +24.6 |
| Kidney renal clear cell carcinoma (TCGA-KIRC) | 438 | -25.3 | +10.7 | -18.7 | +5.7 |
| Lower-grade glioma (TCGA-LGG) | 204 | -9.8 | -4.4 | -3.4 | -6.9 |
| Lung adenocarcinoma (TCGA-LUAD) | 234 | -11.5 | -1.3 | -0.9 | -41.0 |
| Lung squamous cell carcinoma (TCGA-LUSC) | 263 | -45.2 | +8.0 | -6.1 | +14.1 |
| Prostate adenocarcinoma (TCGA-PRAD) | 208 | +12.0 | -2.9 | -50.0 | -15.9 |
| Rectal adenocarcinoma (TCGA-READ) | 156 | +3.2 | +15.4 | +5.8 | -26.3 |

## Detailed results by model and organ

A fixed case was wrong with the image-only prompt and correct with the case-specific prompt. A broken case changed in the opposite direction.

### CONCH

| Organ and disease | Cases | Image-only baseline | Case-specific prompts | Change | Fixed / broken |
|---|---:|---:|---:|---:|---:|
| Breast invasive carcinoma (TCGA-BRCA) | 216 | 56/216 (25.9%) | 75/216 (34.7%) | +8.8 points | 43 / 24 |
| Colon adenocarcinoma (TCGA-COAD) | 422 | 77/422 (18.2%) | 197/422 (46.7%) | +28.4 points | 141 / 21 |
| Kidney renal clear cell carcinoma (TCGA-KIRC) | 438 | 276/438 (63.0%) | 165/438 (37.7%) | -25.3 points | 19 / 130 |
| Lower-grade glioma (TCGA-LGG) | 204 | 201/204 (98.5%) | 181/204 (88.7%) | -9.8 points | 1 / 21 |
| Lung adenocarcinoma (TCGA-LUAD) | 234 | 181/234 (77.4%) | 154/234 (65.8%) | -11.5 points | 20 / 47 |
| Lung squamous cell carcinoma (TCGA-LUSC) | 263 | 163/263 (62.0%) | 44/263 (16.7%) | -45.2 points | 1 / 120 |
| Prostate adenocarcinoma (TCGA-PRAD) | 208 | 125/208 (60.1%) | 150/208 (72.1%) | +12.0 points | 67 / 42 |
| Rectal adenocarcinoma (TCGA-READ) | 156 | 12/156 (7.7%) | 17/156 (10.9%) | +3.2 points | 13 / 8 |

### MUSK

| Organ and disease | Cases | Image-only baseline | Case-specific prompts | Change | Fixed / broken |
|---|---:|---:|---:|---:|---:|
| Breast invasive carcinoma (TCGA-BRCA) | 216 | 58/216 (26.9%) | 39/216 (18.1%) | -8.8 points | 6 / 25 |
| Colon adenocarcinoma (TCGA-COAD) | 422 | 129/422 (30.6%) | 77/422 (18.2%) | -12.3 points | 30 / 82 |
| Kidney renal clear cell carcinoma (TCGA-KIRC) | 438 | 89/438 (20.3%) | 136/438 (31.1%) | +10.7 points | 60 / 13 |
| Lower-grade glioma (TCGA-LGG) | 204 | 174/204 (85.3%) | 165/204 (80.9%) | -4.4 points | 0 / 9 |
| Lung adenocarcinoma (TCGA-LUAD) | 234 | 127/234 (54.3%) | 124/234 (53.0%) | -1.3 points | 15 / 18 |
| Lung squamous cell carcinoma (TCGA-LUSC) | 263 | 138/263 (52.5%) | 159/263 (60.5%) | +8.0 points | 34 / 13 |
| Prostate adenocarcinoma (TCGA-PRAD) | 208 | 66/208 (31.7%) | 60/208 (28.8%) | -2.9 points | 12 / 18 |
| Rectal adenocarcinoma (TCGA-READ) | 156 | 87/156 (55.8%) | 111/156 (71.2%) | +15.4 points | 42 / 18 |

### PLIP

| Organ and disease | Cases | Image-only baseline | Case-specific prompts | Change | Fixed / broken |
|---|---:|---:|---:|---:|---:|
| Breast invasive carcinoma (TCGA-BRCA) | 216 | 2/216 (0.9%) | 11/216 (5.1%) | +4.2 points | 11 / 2 |
| Colon adenocarcinoma (TCGA-COAD) | 422 | 163/422 (38.6%) | 10/422 (2.4%) | -36.3 points | 6 / 159 |
| Kidney renal clear cell carcinoma (TCGA-KIRC) | 438 | 262/438 (59.8%) | 180/438 (41.1%) | -18.7 points | 18 / 100 |
| Lower-grade glioma (TCGA-LGG) | 204 | 191/204 (93.6%) | 184/204 (90.2%) | -3.4 points | 0 / 7 |
| Lung adenocarcinoma (TCGA-LUAD) | 234 | 9/234 (3.8%) | 7/234 (3.0%) | -0.9 points | 4 / 6 |
| Lung squamous cell carcinoma (TCGA-LUSC) | 263 | 101/263 (38.4%) | 85/263 (32.3%) | -6.1 points | 24 / 40 |
| Prostate adenocarcinoma (TCGA-PRAD) | 208 | 172/208 (82.7%) | 68/208 (32.7%) | -50.0 points | 1 / 105 |
| Rectal adenocarcinoma (TCGA-READ) | 156 | 4/156 (2.6%) | 13/156 (8.3%) | +5.8 points | 12 / 3 |

### QuiltNet-B-32

| Organ and disease | Cases | Image-only baseline | Case-specific prompts | Change | Fixed / broken |
|---|---:|---:|---:|---:|---:|
| Breast invasive carcinoma (TCGA-BRCA) | 216 | 25/216 (11.6%) | 77/216 (35.6%) | +24.1 points | 59 / 7 |
| Colon adenocarcinoma (TCGA-COAD) | 422 | 15/422 (3.6%) | 119/422 (28.2%) | +24.6 points | 109 / 5 |
| Kidney renal clear cell carcinoma (TCGA-KIRC) | 438 | 37/438 (8.4%) | 62/438 (14.2%) | +5.7 points | 38 / 13 |
| Lower-grade glioma (TCGA-LGG) | 204 | 191/204 (93.6%) | 177/204 (86.8%) | -6.9 points | 1 / 15 |
| Lung adenocarcinoma (TCGA-LUAD) | 234 | 163/234 (69.7%) | 67/234 (28.6%) | -41.0 points | 11 / 107 |
| Lung squamous cell carcinoma (TCGA-LUSC) | 263 | 6/263 (2.3%) | 43/263 (16.3%) | +14.1 points | 39 / 2 |
| Prostate adenocarcinoma (TCGA-PRAD) | 208 | 125/208 (60.1%) | 92/208 (44.2%) | -15.9 points | 25 / 58 |
| Rectal adenocarcinoma (TCGA-READ) | 156 | 133/156 (85.3%) | 92/156 (59.0%) | -26.3 points | 6 / 47 |

## Final-review accuracy by organ

| Organ and disease | Correct | Accuracy |
|---|---:|---:|
| Breast invasive carcinoma (TCGA-BRCA) | 147/216 | 68.1% |
| Colon adenocarcinoma (TCGA-COAD) | 98/422 | 23.2% |
| Kidney renal clear cell carcinoma (TCGA-KIRC) | 131/438 | 29.9% |
| Lower-grade glioma (TCGA-LGG) | 68/204 | 33.3% |
| Lung adenocarcinoma (TCGA-LUAD) | 20/234 | 8.5% |
| Lung squamous cell carcinoma (TCGA-LUSC) | 10/263 | 3.8% |
| Prostate adenocarcinoma (TCGA-PRAD) | 92/208 | 44.2% |
| Rectal adenocarcinoma (TCGA-READ) | 43/156 | 27.6% |

Wall time: **119.4 minutes**.

The simulated reports are PathGen-generated captions, not authentic clinician reports. Some explicitly name an organ or suspected diagnosis, so final-review accuracy and image-model accuracy are reported separately.
