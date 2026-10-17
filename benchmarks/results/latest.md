# HistoPrompt multi-disease benchmark

## Short answer

Original MUSK classified 33 of 34 images correctly. Enhanced MUSK classified 31 of 34 images correctly.
The enhanced prompts reduced accuracy by 5.9 percentage points. They fixed 0 original errors and introduced 2 new errors.

| Version | What MUSK received | Correct | Accuracy | Change |
|---|---|---:|---:|---:|
| **Original MUSK** | Image + generic label descriptions | **33/34** | **97.1%** | — |
| **Enhanced MUSK** | Image + descriptions generated from retrieved evidence | **31/34** | **91.2%** | **-5.9 points** |

## What we tested

This run used 34 fixed public pathology images. It covered 9 disease conditions and 2 benign controls.

| Clinical group | Images | Correct labels represented | Labels MUSK chose between |
|---|---:|---|---|
| lung histopathology | 15 | lung adenocarcinoma, benign lung tissue, lung squamous cell carcinoma | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma |
| colon histopathology | 10 | colorectal adenocarcinoma, benign colonic tissue | benign colonic tissue, colorectal adenocarcinoma |
| infectious esophagitis | 6 | Candida esophagitis, herpes simplex virus esophagitis, cytomegalovirus esophagitis | Candida esophagitis, herpes simplex virus esophagitis, cytomegalovirus esophagitis |
| skin cancer histopathology | 3 | basal cell carcinoma, cutaneous squamous cell carcinoma, melanoma | basal cell carcinoma, cutaneous squamous cell carcinoma, melanoma |

The table shows the number of images in each clinical group. Sample counts still differ by source, so the combined accuracy must be interpreted carefully.

## Results by clinical group

| Clinical group | Original MUSK | Enhanced MUSK |
|---|---:|---:|
| lung histopathology | 14/15 | 12/15 |
| colon histopathology | 10/10 | 10/10 |
| infectious esophagitis | 6/6 | 6/6 |
| skin cancer histopathology | 3/3 | 3/3 |

## Results by label

| Correct label | Images | Original MUSK | Enhanced MUSK | Enhanced model's most common error |
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

The largest decline was for lung adenocarcinoma: Original MUSK got 4/5 correct, while Enhanced MUSK got 2/5 correct.
Enhanced MUSK labeled 2/5 of these images as lung squamous cell carcinoma.

## What original and enhanced mean

- **Original MUSK:** The model received the image and a generic prompt such as `a histopathology image showing lung adenocarcinoma`.
- **Enhanced MUSK:** HistoPrompt retrieved local evidence. Lumen converted that evidence into microscopic feature descriptions. MUSK received the same image with those longer descriptions.
- The benchmark did not give Lumen the image, a report, or the correct label. This prevented the enhanced path from receiving the answer through its prompt.

## Cases where the prediction changed

| Clinical group | Correct label | Original MUSK | Enhanced MUSK | Effect of enhancement |
|---|---|---|---|---|
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | benign lung tissue | Worse; changed a correct result to an error |

## Other prompt versions

The runner also tested diagnostic variants. These are secondary results, not the main product comparison.

| Prompt version | Correct | Accuracy |
|---|---:|---:|
| Label text only | 33/34 | 97.1% |
| Hand-written microscopic features | 31/34 | 91.2% |

These extra variants help separate the effect of retrieval from the effect of adding longer microscopic descriptions.

## Reproducibility and sample size

This run vendors the exact image bytes in the repository and verifies a SHA-256 checksum before inference.

LC25000 images use fixed evenly spaced rows from the public dataset. Infectious-esophagitis and skin-cancer images are published educational figures.

## What a broader benchmark should add

- Use patient-independent images with documented train/test separation for each label.
- Add more tissue groups, such as breast, prostate, and lymph node pathology.
- Fix all image selections before running any prompt version.
- Report accuracy for each tissue group, not only one combined number.
- Test report writing separately with a rubric for factual support, missing findings, citations, and unsupported claims.

## Limits

- This is a 34-image engineering benchmark, not a clinical validation study.
- LC25000 images use fixed evenly spaced rows from the public dataset. Infectious-esophagitis and skin-cancer images are published educational figures.
- Candidate sets differ by organ family, so the task measures within-family discrimination rather than unrestricted diagnosis.
- The hosted hackathon API returns only the winning label and one score. Scores from two-label and three-label families are not directly comparable; calibration, margins, and rank changes cannot be measured.
- Evidence-generated prompts are created once per family without reports, image contents, or ground-truth labels, preventing answer leakage.
- Results may vary when the remote model, preprocessing, or Lumen model changes.

Run ID: `20261017T190617Z`
