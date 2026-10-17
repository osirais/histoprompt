# HistoPrompt multi-disease pilot benchmark

Run: `20261017T184157Z`

Cases: 8 fixed public images across lung, colon, and infectious esophagitis.
Primary metric: top-1 accuracy within each case's candidate family.

| Strategy | Correct | Successful | Accuracy | Mean returned top score |
|---|---:|---:|---:|---:|
| label_only | 8 | 8 | 100.0% | 0.3842 |
| generic | 8 | 8 | 100.0% | 0.3867 |
| curated | 7 | 8 | 87.5% | 0.3943 |
| evidence_generated | 7 | 8 | 87.5% | 0.3942 |

## Observed result

Evidence-generated prompts scored 87.5% versus 100.0% for generic prompts (-12.5%).
Both morphology-rich strategies changed the lung adenocarcinoma example to the wrong squamous-cell label. The returned top score increased slightly even as accuracy fell, so the score should not be read as calibrated confidence.

## Per-case results

| Case | Truth | Strategy | Prediction | Score | Correct |
|---|---|---|---|---:|:---:|
| lc25000-colon-adenocarcinoma-example | colorectal adenocarcinoma | label_only | colorectal adenocarcinoma | 0.5121 | yes |
| lc25000-colon-adenocarcinoma-example | colorectal adenocarcinoma | generic | colorectal adenocarcinoma | 0.5141 | yes |
| lc25000-colon-adenocarcinoma-example | colorectal adenocarcinoma | curated | colorectal adenocarcinoma | 0.5239 | yes |
| lc25000-colon-adenocarcinoma-example | colorectal adenocarcinoma | evidence_generated | colorectal adenocarcinoma | 0.5171 | yes |
| lc25000-benign-colon-example | benign colonic tissue | label_only | benign colonic tissue | 0.5093 | yes |
| lc25000-benign-colon-example | benign colonic tissue | generic | benign colonic tissue | 0.5162 | yes |
| lc25000-benign-colon-example | benign colonic tissue | curated | benign colonic tissue | 0.5286 | yes |
| lc25000-benign-colon-example | benign colonic tissue | evidence_generated | benign colonic tissue | 0.5420 | yes |
| lc25000-lung-adenocarcinoma-example | lung adenocarcinoma | label_only | lung adenocarcinoma | 0.3378 | yes |
| lc25000-lung-adenocarcinoma-example | lung adenocarcinoma | generic | lung adenocarcinoma | 0.3403 | yes |
| lc25000-lung-adenocarcinoma-example | lung adenocarcinoma | curated | lung squamous cell carcinoma | 0.3390 | no |
| lc25000-lung-adenocarcinoma-example | lung adenocarcinoma | evidence_generated | lung squamous cell carcinoma | 0.3468 | no |
| lc25000-lung-squamous-example | lung squamous cell carcinoma | label_only | lung squamous cell carcinoma | 0.3411 | yes |
| lc25000-lung-squamous-example | lung squamous cell carcinoma | generic | lung squamous cell carcinoma | 0.3451 | yes |
| lc25000-lung-squamous-example | lung squamous cell carcinoma | curated | lung squamous cell carcinoma | 0.3535 | yes |
| lc25000-lung-squamous-example | lung squamous cell carcinoma | evidence_generated | lung squamous cell carcinoma | 0.3548 | yes |
| lc25000-benign-lung-example | benign lung tissue | label_only | benign lung tissue | 0.3419 | yes |
| lc25000-benign-lung-example | benign lung tissue | generic | benign lung tissue | 0.3514 | yes |
| lc25000-benign-lung-example | benign lung tissue | curated | benign lung tissue | 0.3627 | yes |
| lc25000-benign-lung-example | benign lung tissue | evidence_generated | benign lung tissue | 0.3521 | yes |
| pmc7005969-candida-he | Candida esophagitis | label_only | Candida esophagitis | 0.3435 | yes |
| pmc7005969-candida-he | Candida esophagitis | generic | Candida esophagitis | 0.3396 | yes |
| pmc7005969-candida-he | Candida esophagitis | curated | Candida esophagitis | 0.3492 | yes |
| pmc7005969-candida-he | Candida esophagitis | evidence_generated | Candida esophagitis | 0.3467 | yes |
| pmc7005969-hsv-he | herpes simplex virus esophagitis | label_only | herpes simplex virus esophagitis | 0.3412 | yes |
| pmc7005969-hsv-he | herpes simplex virus esophagitis | generic | herpes simplex virus esophagitis | 0.3419 | yes |
| pmc7005969-hsv-he | herpes simplex virus esophagitis | curated | herpes simplex virus esophagitis | 0.3438 | yes |
| pmc7005969-hsv-he | herpes simplex virus esophagitis | evidence_generated | herpes simplex virus esophagitis | 0.3460 | yes |
| pmc7005969-cmv-he | cytomegalovirus esophagitis | label_only | cytomegalovirus esophagitis | 0.3465 | yes |
| pmc7005969-cmv-he | cytomegalovirus esophagitis | generic | cytomegalovirus esophagitis | 0.3452 | yes |
| pmc7005969-cmv-he | cytomegalovirus esophagitis | curated | cytomegalovirus esophagitis | 0.3540 | yes |
| pmc7005969-cmv-he | cytomegalovirus esophagitis | evidence_generated | cytomegalovirus esophagitis | 0.3480 | yes |

## Interpretation limits

- This is an eight-image integration pilot, not a clinical validation study.
- The five LC25000 items are catalog example images, not a random sample; the three infectious-esophagitis items are published educational figures.
- Candidate sets differ by organ family, so the task measures within-family discrimination rather than unrestricted diagnosis.
- The hosted hackathon API returns only the winning label and one score. Scores from two-label and three-label families are not directly comparable; calibration, margins, and rank changes cannot be measured.
- Evidence-generated prompts are created once per family without reports, image contents, or ground-truth labels, preventing answer leakage.
- Results may vary when the remote model, preprocessing, or Lumen model changes.
