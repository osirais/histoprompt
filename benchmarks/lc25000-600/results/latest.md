# HistoPrompt LC25000 600-image lung benchmark

## Short answer

Original MUSK classified 538 of 600 images correctly. Enhanced MUSK classified 478 of 600 images correctly.
The enhanced prompts reduced accuracy by 10.0 percentage points. They fixed 26 original errors and introduced 86 new errors.

| Version | What MUSK received | Correct | Accuracy | Change |
|---|---|---:|---:|---:|
| **Original MUSK** | Image + generic label descriptions | **538/600** | **89.7%** | — |
| **Enhanced MUSK** | Image + descriptions generated from retrieved evidence | **478/600** | **79.7%** | **-10.0 points** |

## What we tested

This run used 600 fixed public pathology images. It covered 2 disease conditions and 1 benign control.

| Clinical group | Images | Correct labels represented | Labels MUSK chose between |
|---|---:|---|---|
| lung histopathology | 600 | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma | benign lung tissue, lung adenocarcinoma, lung squamous cell carcinoma |

This run deliberately focuses on one clinical group so both prompt versions are compared on the same fixed images.

## Results by clinical group

| Clinical group | Original MUSK | Enhanced MUSK |
|---|---:|---:|
| lung histopathology | 538/600 | 478/600 |

## Results by label

| Correct label | Images | Original MUSK | Enhanced MUSK | Enhanced model's most common error |
|---|---:|---:|---:|---|
| benign lung tissue | 200 | 200/200 | 199/200 | lung squamous cell carcinoma (1) |
| lung adenocarcinoma | 200 | 149/200 | 79/200 | lung squamous cell carcinoma (120) |
| lung squamous cell carcinoma | 200 | 189/200 | 200/200 | None |

## Main failure pattern

The largest decline was for lung adenocarcinoma: Original MUSK got 149/200 correct, while Enhanced MUSK got 79/200 correct.
Enhanced MUSK labeled 120/200 of these images as lung squamous cell carcinoma.

## What original and enhanced mean

- **Original MUSK:** The model received the image and a generic prompt such as `a histopathology image showing lung adenocarcinoma`.
- **Enhanced MUSK:** HistoPrompt retrieved local evidence. Lumen converted that evidence into microscopic feature descriptions. MUSK received the same image with those longer descriptions.
- The benchmark did not give Lumen the image, a report, or the correct label. This prevented the enhanced path from receiving the answer through its prompt.

## Cases where the prediction changed

| Clinical group | Correct label | Original MUSK | Enhanced MUSK | Effect of enhancement |
|---|---|---|---|---|
| lung histopathology | benign lung tissue | benign lung tissue | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | benign lung tissue | lung adenocarcinoma | Better; fixed an original error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | benign lung tissue | lung adenocarcinoma | Better; fixed an original error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | benign lung tissue | lung adenocarcinoma | Better; fixed an original error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | benign lung tissue | lung adenocarcinoma | Better; fixed an original error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | benign lung tissue | lung adenocarcinoma | Better; fixed an original error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | lung adenocarcinoma | lung squamous cell carcinoma | Worse; changed a correct result to an error |
| lung histopathology | lung adenocarcinoma | benign lung tissue | lung adenocarcinoma | Better; fixed an original error |
| lung histopathology | lung adenocarcinoma | benign lung tissue | lung adenocarcinoma | Better; fixed an original error |

The table shows the first 25 of 122 changed predictions. The raw JSON contains every case.

## Prompt selection without test-set leakage

The first 300 class-stratified images were used to compare prompt candidates. The remaining 300 images were kept hidden from selection.

The development set selected **histology_showing** at 92.7% balanced accuracy.
On the held-out images, that fixed choice scored **278/300 (92.7%)**, compared with **267/300 (89.0%)** for generic MUSK (+3.7 points).

A prompt is considered an improvement only if this held-out result beats generic MUSK. Development accuracy by itself is not evidence of improvement.

## Runtime

- Configured batch size: 8 images
- Completed batches: 75
- Total MUSK inference time: 23.8 seconds
- Mean time per image and prompt strategy: 0.040 seconds

## Reproducibility and sample size

This run uses 600 exact image files and verifies every SHA-256 checksum before inference. It contains 200 deterministic samples from each lung class.

All images come from the lung portion of LC25000. The dataset contains augmented derivatives of a smaller original collection, so samples are not patient-independent.

## What a broader benchmark should add

- Use patient-independent images with documented train/test separation for each label.
- Add more tissue groups, such as breast, prostate, and lymph node pathology.
- Fix all image selections before running any prompt version.
- Report accuracy for each tissue group, not only one combined number.
- Test report writing separately with a rubric for factual support, missing findings, citations, and unsupported claims.

## Limits

- This is a 600-image engineering benchmark, not a clinical validation study.
- All images come from the lung portion of LC25000. The dataset contains augmented derivatives of a smaller original collection, so samples are not patient-independent.
- Candidate sets differ by organ family, so the task measures within-family discrimination rather than unrestricted diagnosis.
- The hosted hackathon API returns only the winning label and one score. Scores from two-label and three-label families are not directly comparable; calibration, margins, and rank changes cannot be measured.
- Evidence-generated prompts are created once per family without reports, image contents, or ground-truth labels, preventing answer leakage.
- Results may vary when the remote model, preprocessing, or Lumen model changes.

Run ID: `20261017T204147Z`
