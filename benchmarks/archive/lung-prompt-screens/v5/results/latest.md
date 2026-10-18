# HistoPrompt LC25000 600-image lung benchmark

## Short answer

Original MUSK classified 271 of 300 images correctly. Enhanced MUSK classified 225 of 300 images correctly.
The enhanced prompts reduced accuracy by 15.3 percentage points. They fixed 5 original errors and introduced 51 new errors.

| Version | What MUSK received | Correct | Accuracy | Change |
|---|---|---:|---:|---:|
| **Original MUSK** | Image + generic label descriptions | **271/300** | **90.3%** | — |
| **Enhanced MUSK** | Image + descriptions generated from retrieved evidence | **225/300** | **75.0%** | **-15.3 points** |

## What we tested

This run used 300 fixed public pathology images. It covered 2 disease conditions and 1 benign control.

| Clinical group | Images | Correct labels represented | Labels MUSK chose between |
|---|---:|---|---|
| lung histopathology | 300 | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma |

This run deliberately focuses on one clinical group so both prompt versions are compared on the same fixed images.

## Results by clinical group

| Clinical group | Original MUSK | Enhanced MUSK |
|---|---:|---:|
| lung histopathology | 271/300 | 225/300 |

## Results by label

| Correct label | Images | Original MUSK | Enhanced MUSK | Enhanced model's most common error |
|---|---:|---:|---:|---|
| benign lung tissue | 100 | 100/100 | 100/100 | None |
| lung adenocarcinoma | 100 | 76/100 | 27/100 | lung squamous cell carcinoma (55) |
| lung squamous cell carcinoma | 100 | 95/100 | 98/100 | benign lung tissue (2) |

## Main failure pattern

The largest decline was for lung adenocarcinoma: Original MUSK got 76/100 correct, while Enhanced MUSK got 27/100 correct.
Enhanced MUSK labeled 55/100 of these images as lung squamous cell carcinoma.

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
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | benign lung tissue | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | benign lung tissue | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |

The table shows the first 25 of 57 changed predictions. The raw JSON contains every case.

## Prompt selection without test-set leakage

The first 150 class-stratified images were used to compare prompt candidates. The remaining 150 images were kept hidden from selection.

The development set selected **pathology_slide_showing** at 94.0% balanced accuracy.
On the held-out images, that fixed choice scored **136/150 (90.7%)**, compared with **136/150 (90.7%)** for generic MUSK (+0.0 points).

A prompt is considered an improvement only if this held-out result beats generic MUSK. Development accuracy by itself is not evidence of improvement.

## Runtime

- Configured batch size: 8 images
- Completed batches: 152
- Total MUSK inference time: 45.3 seconds
- Mean time per image and prompt strategy: 0.038 seconds

## Reproducibility and sample size

This rapid screen uses the first 100 fixed images per family/label and verifies each SHA-256 checksum before inference.

All images come from the lung portion of LC25000. The dataset contains augmented derivatives of a smaller original collection, so samples are not patient-independent.

## What a broader benchmark should add

- Use patient-independent images with documented train/test separation for each label.
- Add more tissue groups, such as breast, prostate, and lymph node pathology.
- Fix all image selections before running any prompt version.
- Report accuracy for each tissue group, not only one combined number.
- Test report writing separately with a rubric for factual support, missing findings, citations, and unsupported claims.

## Limits

- This is a 300-image engineering benchmark, not a clinical validation study.
- All images come from the lung portion of LC25000. The dataset contains augmented derivatives of a smaller original collection, so samples are not patient-independent.
- Candidate sets differ by organ family, so the task measures within-family discrimination rather than unrestricted diagnosis.
- The hosted hackathon API returns only the winning label and one score. Scores from two-label and three-label families are not directly comparable; calibration, margins, and rank changes cannot be measured.
- Evidence-generated prompts are created once per family without reports, image contents, or ground-truth labels, preventing answer leakage.
- Results may vary when the remote model, preprocessing, or Lumen model changes.

Run ID: `20261017T204107Z`
