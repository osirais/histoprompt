# HistoPrompt 11-label diagnosis benchmark

## Short answer

Generic prompt classified 33 of 34 images correctly. Evidence-enriched prompt classified 31 of 34 images correctly.
The candidate prompts reduced accuracy by 5.9 percentage points. They fixed 0 original errors and introduced 2 new errors.

| Version | What MUSK received | Correct | Accuracy | Change |
|---|---|---:|---:|---:|
| **Generic prompt** | Image + generic label descriptions | **33/34** | **97.1%** | — |
| **Evidence-enriched prompt** | Image + frozen descriptions generated from retrieved evidence | **31/34** | **91.2%** | **-5.9 points** |

## What we tested

This run used 34 fixed public pathology images. It evaluated 11 diagnosis labels in four clinical differentials: lung, colon, infectious esophagitis, and skin cancer.

| Clinical group | Images | Correct labels represented | Labels MUSK chose between |
|---|---:|---|---|
| lung histopathology | 15 | lung adenocarcinoma, benign lung tissue, lung squamous cell carcinoma | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma |
| colon histopathology | 10 | colorectal adenocarcinoma, benign colonic tissue | benign colonic tissue, colorectal adenocarcinoma |
| infectious esophagitis | 6 | Candida esophagitis, herpes simplex virus esophagitis, cytomegalovirus esophagitis | Candida esophagitis, herpes simplex virus esophagitis, cytomegalovirus esophagitis |
| skin cancer histopathology | 3 | basal cell carcinoma, cutaneous squamous cell carcinoma, melanoma | basal cell carcinoma, cutaneous squamous cell carcinoma, melanoma |

The table shows the number of images in each clinical group. Sample counts still differ by source, so the combined accuracy must be interpreted carefully.

## Results by clinical group

| Clinical group | Generic prompt | Evidence-enriched prompt |
|---|---:|---:|
| lung histopathology | 14/15 | 12/15 |
| colon histopathology | 10/10 | 10/10 |
| infectious esophagitis | 6/6 | 6/6 |
| skin cancer histopathology | 3/3 | 3/3 |

## Results by label

| Correct label | Images | Generic prompt | Evidence-enriched prompt | Candidate prompt's most common error |
|---|---:|---:|---:|---|
| lung adenocarcinoma | 5 | 4/5 | 2/5 | lung squamous cell carcinoma (2) |
| benign lung tissue | 5 | 5/5 | 5/5 | None |
| lung squamous cell carcinoma | 5 | 5/5 | 5/5 | None |
| colorectal adenocarcinoma | 5 | 5/5 | 5/5 | None |
| benign colonic tissue | 5 | 5/5 | 5/5 | None |
| Candida esophagitis | 2 | 2/2 | 2/2 | None |
| herpes simplex virus esophagitis | 2 | 2/2 | 2/2 | None |
| cytomegalovirus esophagitis | 2 | 2/2 | 2/2 | None |
| basal cell carcinoma | 1 | 1/1 | 1/1 | None |
| cutaneous squamous cell carcinoma | 1 | 1/1 | 1/1 | None |
| melanoma | 1 | 1/1 | 1/1 | None |

## Main failure pattern

The largest decline was for lung adenocarcinoma: Generic prompt got 4/5 correct, while Evidence-enriched prompt got 2/5 correct.
Evidence-enriched prompt labeled 2/5 of these images as lung squamous cell carcinoma.

## What the two versions mean

- **Generic prompt:** The model received the image and a generic prompt such as `a histopathology image showing lung adenocarcinoma`.
- **Evidence-enriched prompt:** HistoPrompt retrieved local evidence. Lumen converted that evidence into microscopic feature descriptions, which were sent with the same image.
- The benchmark did not give Lumen the image, a report, or the correct label, preventing answer leakage through the generated prompt.

## Cases where the prediction changed

| Clinical group | Correct label | Generic prompt | Evidence-enriched prompt | Effect of candidate prompt |
|---|---|---|---|---|
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | benign lung tissue | Worse; changed a correct result to an error |

## Prompt selection

Not run because at least one family/label group has fewer than two cases.
The full-set comparison is descriptive only; it does not select or validate a winning prompt.

## Runtime

- Configured batch size: 64 images
- Completed batches: 8
- Total MUSK inference time: 4.6 seconds
- Mean time per image and prompt strategy: 0.068 seconds

## Coverage gaps

- This diagnosis suite has only one or two examples for several non-LC25000 labels.
- It does not yet cover breast, prostate, kidney, liver, brain, bone, gynecologic, or hematolymphoid diagnoses.
- The broad-organ replacement benchmark is pending separate PathMMU dataset approval.

## Reproducibility and sample size

The exact selected image bytes are stored in the repository, and every SHA-256 checksum is verified before inference.

LC25000 images use fixed evenly spaced rows from the public dataset; infectious-esophagitis and skin-cancer images are published educational figures.

## What a broader benchmark should add

- Add an expert-reviewed PathMMU subset after the Hugging Face account is approved for that gated dataset.
- Use patient-independent disease datasets with enough cases for a held-out split in every label.
- Keep report-writing evaluation separate from image classification accuracy.

## Limits

- This is a 34-image engineering benchmark, not a clinical validation study.
- LC25000 images use fixed evenly spaced rows from the public dataset; infectious-esophagitis and skin-cancer images are published educational figures.
- Results measure only the candidate-label task defined by the manifest, not unrestricted diagnosis.
- The hosted hackathon API returns only the winning label and one score. Scores from tasks with different candidate-set sizes are not directly comparable; calibration, margins, and rank changes cannot be measured.
- Prompts are fixed before inference and do not receive the image, report, or ground-truth label.
- Results may vary when the remote model, preprocessing, or Lumen model changes.

Run ID: `20261018T155738Z`
