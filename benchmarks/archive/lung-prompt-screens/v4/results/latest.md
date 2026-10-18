# HistoPrompt LC25000 600-image lung benchmark

## Short answer

Original MUSK classified 54 of 60 images correctly. Enhanced MUSK classified 45 of 60 images correctly.
The enhanced prompts reduced accuracy by 15.0 percentage points. They fixed 2 original errors and introduced 11 new errors.

| Version | What MUSK received | Correct | Accuracy | Change |
|---|---|---:|---:|---:|
| **Original MUSK** | Image + generic label descriptions | **54/60** | **90.0%** | — |
| **Enhanced MUSK** | Image + descriptions generated from retrieved evidence | **45/60** | **75.0%** | **-15.0 points** |

## What we tested

This run used 60 fixed public pathology images. It covered 2 disease conditions and 1 benign control.

| Clinical group | Images | Correct labels represented | Labels MUSK chose between |
|---|---:|---|---|
| lung histopathology | 60 | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma |

This run deliberately focuses on one clinical group so both prompt versions are compared on the same fixed images.

## Results by clinical group

| Clinical group | Original MUSK | Enhanced MUSK |
|---|---:|---:|
| lung histopathology | 54/60 | 45/60 |

## Results by label

| Correct label | Images | Original MUSK | Enhanced MUSK | Enhanced model's most common error |
|---|---:|---:|---:|---|
| benign lung tissue | 20 | 20/20 | 20/20 | None |
| lung adenocarcinoma | 20 | 15/20 | 6/20 | lung squamous cell carcinoma (10) |
| lung squamous cell carcinoma | 20 | 19/20 | 19/20 | benign lung tissue (1) |

## Main failure pattern

The largest decline was for lung adenocarcinoma: Original MUSK got 15/20 correct, while Enhanced MUSK got 6/20 correct.
Enhanced MUSK labeled 10/20 of these images as lung squamous cell carcinoma.

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
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | benign lung tissue | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | benign lung tissue | lung adenocarcinoma | Better; fixed an original error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | benign lung tissue | Worse; changed a correct result to an error |
| lung histopathology | lung squamous cell carcinoma | lung squamous cell carcinoma | benign lung tissue | Worse; changed a correct result to an error |
| lung histopathology | lung squamous cell carcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Better; fixed an original error |

## Prompt selection without test-set leakage

The first 30 class-stratified images were used to compare prompt candidates. The remaining 30 images were kept hidden from selection.

The development set selected **histology_showing** at 90.0% balanced accuracy.
On the held-out images, that fixed choice scored **29/30 (96.7%)**, compared with **28/30 (93.3%)** for generic MUSK (+3.3 points).

A prompt is considered an improvement only if this held-out result beats generic MUSK. Development accuracy by itself is not evidence of improvement.

## Runtime

- Configured batch size: 8 images
- Completed batches: 32
- Total MUSK inference time: 9.3 seconds
- Mean time per image and prompt strategy: 0.039 seconds

## Reproducibility and sample size

This rapid screen uses the first 20 fixed images per family/label and verifies each SHA-256 checksum before inference.

All images come from the lung portion of LC25000. The dataset contains augmented derivatives of a smaller original collection, so samples are not patient-independent.

## What a broader benchmark should add

- Use patient-independent images with documented train/test separation for each label.
- Add more tissue groups, such as breast, prostate, and lymph node pathology.
- Fix all image selections before running any prompt version.
- Report accuracy for each tissue group, not only one combined number.
- Test report writing separately with a rubric for factual support, missing findings, citations, and unsupported claims.

## Limits

- This is a 60-image engineering benchmark, not a clinical validation study.
- All images come from the lung portion of LC25000. The dataset contains augmented derivatives of a smaller original collection, so samples are not patient-independent.
- Candidate sets differ by organ family, so the task measures within-family discrimination rather than unrestricted diagnosis.
- The hosted hackathon API returns only the winning label and one score. Scores from two-label and three-label families are not directly comparable; calibration, margins, and rank changes cannot be measured.
- Evidence-generated prompts are created once per family without reports, image contents, or ground-truth labels, preventing answer leakage.
- Results may vary when the remote model, preprocessing, or Lumen model changes.

Run ID: `20261017T204011Z`
