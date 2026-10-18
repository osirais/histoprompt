# HistoPrompt LC25000 600-image lung benchmark

## Short answer

Original MUSK classified 26 of 30 images correctly. Enhanced MUSK classified 21 of 30 images correctly.
The enhanced prompts reduced accuracy by 16.7 percentage points. They fixed 0 original errors and introduced 5 new errors.

| Version | What MUSK received | Correct | Accuracy | Change |
|---|---|---:|---:|---:|
| **Original MUSK** | Image + generic label descriptions | **26/30** | **86.7%** | — |
| **Enhanced MUSK** | Image + descriptions generated from retrieved evidence | **21/30** | **70.0%** | **-16.7 points** |

## What we tested

This run used 30 fixed public pathology images. It covered 2 disease conditions and 1 benign control.

| Clinical group | Images | Correct labels represented | Labels MUSK chose between |
|---|---:|---|---|
| lung histopathology | 30 | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma |

This run deliberately focuses on one clinical group so both prompt versions are compared on the same fixed images.

## Results by clinical group

| Clinical group | Original MUSK | Enhanced MUSK |
|---|---:|---:|
| lung histopathology | 26/30 | 21/30 |

## Results by label

| Correct label | Images | Original MUSK | Enhanced MUSK | Enhanced model's most common error |
|---|---:|---:|---:|---|
| benign lung tissue | 10 | 10/10 | 10/10 | None |
| lung adenocarcinoma | 10 | 6/10 | 1/10 | lung squamous cell carcinoma (7) |
| lung squamous cell carcinoma | 10 | 10/10 | 10/10 | None |

## Main failure pattern

The largest decline was for lung adenocarcinoma: Original MUSK got 6/10 correct, while Enhanced MUSK got 1/10 correct.
Enhanced MUSK labeled 7/10 of these images as lung squamous cell carcinoma.

## What original and enhanced mean

- **Original MUSK:** The model received the image and a generic prompt such as `a histopathology image showing lung adenocarcinoma`.
- **Enhanced MUSK:** HistoPrompt retrieved local evidence. Lumen converted that evidence into microscopic feature descriptions. MUSK received the same image with those longer descriptions.
- The benchmark did not give Lumen the image, a report, or the correct label. This prevented the enhanced path from receiving the answer through its prompt.

## Cases where the prediction changed

| Clinical group | Correct label | Original MUSK | Enhanced MUSK | Effect of enhancement |
|---|---|---|---|---|
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |

## Other prompt versions

The runner also tested diagnostic variants. These are secondary results, not the main product comparison.

| Prompt version | Correct | Accuracy |
|---|---:|---:|
| Label text only | 26/30 | 86.7% |
| Hand-written microscopic features | 22/30 | 73.3% |
| Generic template + all generated features | 24/30 | 80.0% |
| Generic template + first generated feature | 26/30 | 86.7% |

These extra variants help separate the effect of retrieval from the effect of adding longer microscopic descriptions.

## Prompt selection without test-set leakage

The first 15 class-stratified images were used to compare prompt candidates. The remaining 15 images were kept hidden from selection.

The development set selected **generic** at 86.7% balanced accuracy.
On the held-out images, that fixed choice scored **13/15 (86.7%)**, compared with **13/15 (86.7%)** for generic MUSK (+0.0 points).

A prompt is considered an improvement only if this held-out result beats generic MUSK. Development accuracy by itself is not evidence of improvement.

## Runtime

- Configured batch size: 8 images
- Completed batches: 32
- Total MUSK inference time: 9.5 seconds
- Mean time per image and prompt strategy: 0.039 seconds

## Reproducibility and sample size

This rapid screen uses the first 10 fixed images per family/label and verifies each SHA-256 checksum before inference.

All images come from the lung portion of LC25000. The dataset contains augmented derivatives of a smaller original collection, so samples are not patient-independent.

## What a broader benchmark should add

- Use patient-independent images with documented train/test separation for each label.
- Add more tissue groups, such as breast, prostate, and lymph node pathology.
- Fix all image selections before running any prompt version.
- Report accuracy for each tissue group, not only one combined number.
- Test report writing separately with a rubric for factual support, missing findings, citations, and unsupported claims.

## Limits

- This is a 30-image engineering benchmark, not a clinical validation study.
- All images come from the lung portion of LC25000. The dataset contains augmented derivatives of a smaller original collection, so samples are not patient-independent.
- Candidate sets differ by organ family, so the task measures within-family discrimination rather than unrestricted diagnosis.
- The hosted hackathon API returns only the winning label and one score. Scores from two-label and three-label families are not directly comparable; calibration, margins, and rank changes cannot be measured.
- Evidence-generated prompts are created once per family without reports, image contents, or ground-truth labels, preventing answer leakage.
- Results may vary when the remote model, preprocessing, or Lumen model changes.

Run ID: `20261017T203939Z`
