# HistoPrompt 11-label diagnosis benchmark

## Short answer

Generic prompt classified 32 of 34 images correctly. Evidence-enriched prompt classified 28 of 34 images correctly.
The candidate prompts reduced accuracy by 11.8 percentage points. They fixed 2 original errors and introduced 6 new errors.

| Version | What CONCH received | Correct | Accuracy | Change |
|---|---|---:|---:|---:|
| **Generic prompt** | Image + generic label descriptions | **32/34** | **94.1%** | — |
| **Evidence-enriched prompt** | Image + frozen descriptions generated from retrieved evidence | **28/34** | **82.4%** | **-11.8 points** |

## What we tested

This run used 34 fixed public pathology images. It evaluated 11 diagnosis labels in four clinical differentials: lung, colon, infectious esophagitis, and skin cancer.

| Clinical group | Images | Correct labels represented | Labels CONCH chose between |
|---|---:|---|---|
| lung histopathology | 15 | lung adenocarcinoma, benign lung tissue, lung squamous cell carcinoma | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma |
| colon histopathology | 10 | colorectal adenocarcinoma, benign colonic tissue | benign colonic tissue, colorectal adenocarcinoma |
| infectious esophagitis | 6 | Candida esophagitis, herpes simplex virus esophagitis, cytomegalovirus esophagitis | Candida esophagitis, herpes simplex virus esophagitis, cytomegalovirus esophagitis |
| skin cancer histopathology | 3 | basal cell carcinoma, cutaneous squamous cell carcinoma, melanoma | basal cell carcinoma, cutaneous squamous cell carcinoma, melanoma |

The table shows the number of images in each clinical group. Sample counts still differ by source, so the combined accuracy must be interpreted carefully.

## Results by clinical group

| Clinical group | Generic prompt | Evidence-enriched prompt |
|---|---:|---:|
| lung histopathology | 15/15 | 10/15 |
| colon histopathology | 8/10 | 10/10 |
| infectious esophagitis | 6/6 | 5/6 |
| skin cancer histopathology | 3/3 | 3/3 |

## Results by label

| Correct label | Images | Generic prompt | Evidence-enriched prompt | Candidate prompt's most common error |
|---|---:|---:|---:|---|
| lung adenocarcinoma | 5 | 5/5 | 2/5 | benign lung tissue (2) |
| benign lung tissue | 5 | 5/5 | 5/5 | None |
| lung squamous cell carcinoma | 5 | 5/5 | 3/5 | benign lung tissue (2) |
| colorectal adenocarcinoma | 5 | 3/5 | 5/5 | None |
| benign colonic tissue | 5 | 5/5 | 5/5 | None |
| Candida esophagitis | 2 | 2/2 | 2/2 | None |
| herpes simplex virus esophagitis | 2 | 2/2 | 1/2 | Candida esophagitis (1) |
| cytomegalovirus esophagitis | 2 | 2/2 | 2/2 | None |
| basal cell carcinoma | 1 | 1/1 | 1/1 | None |
| cutaneous squamous cell carcinoma | 1 | 1/1 | 1/1 | None |
| melanoma | 1 | 1/1 | 1/1 | None |

## Main failure pattern

The largest decline was for lung adenocarcinoma: Generic prompt got 5/5 correct, while Evidence-enriched prompt got 2/5 correct.
Evidence-enriched prompt labeled 2/5 of these images as benign lung tissue.

## What the two versions mean

- **Generic prompt:** The model received the image and a generic prompt such as `a histopathology image showing lung adenocarcinoma`.
- **Evidence-enriched prompt:** HistoPrompt retrieved local evidence. Lumen converted that evidence into microscopic feature descriptions, which were sent with the same image.
- The benchmark did not give Lumen the image, a report, or the correct label, preventing answer leakage through the generated prompt.

## Cases where the prediction changed

| Clinical group | Correct label | Generic prompt | Evidence-enriched prompt | Effect of candidate prompt |
|---|---|---|---|---|
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | benign lung tissue | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | benign lung tissue | Worse; changed a correct result to an error |
| lung histopathology | lung squamous cell carcinoma | lung squamous cell carcinoma | benign lung tissue | Worse; changed a correct result to an error |
| lung histopathology | lung squamous cell carcinoma | lung squamous cell carcinoma | benign lung tissue | Worse; changed a correct result to an error |
| colon histopathology | colorectal adenocarcinoma | benign colonic tissue | colorectal adenocarcinoma | Better; fixed an original error |
| colon histopathology | colorectal adenocarcinoma | benign colonic tissue | colorectal adenocarcinoma | Better; fixed an original error |
| infectious esophagitis | herpes simplex virus esophagitis | herpes simplex virus esophagitis | Candida esophagitis | Worse; changed a correct result to an error |

## Prompt selection

Not run because at least one family/label group has fewer than two cases.
The full-set comparison is descriptive only; it does not select or validate a winning prompt.

## Runtime

- Configured batch size: 64 images
- Completed batches: 8
- Total CONCH inference time: 2.8 seconds
- Mean time per image and prompt strategy: 0.041 seconds

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

Run ID: `20261018T155741Z`
