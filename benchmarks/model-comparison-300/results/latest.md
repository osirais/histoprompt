# Four-model prompt comparison

This is a rapid engineering benchmark run against the live NCSA hosted model
services. It uses the first 100 stored images from each of three LC25000 lung
classes (300 images total): lung adenocarcinoma, lung squamous cell carcinoma,
and benign lung tissue. Images were sent in batches of 32. This is not clinical
validation; the sample is a fixed augmented tile collection.

## Prompts

The standard prompt was `histology showing {label}`. The frozen tuned prompt
changed only the benign label to `histology showing benign lung tissue with
intact alveolar sacs`; the two malignant prompts were unchanged.

## Results

| Model | Standard | Frozen tuned | Change | Tuned time/image |
| --- | ---: | ---: | ---: | ---: |
| CONCH | 196/300 (65.3%) | 182/300 (60.7%) | -4.7 pp | 0.027 s |
| MUSK | 278/300 (92.7%) | 283/300 (94.3%) | +1.7 pp | 0.027 s |
| QuiltNet-B-32 | 240/300 (80.0%) | 235/300 (78.3%) | -1.7 pp | 0.013 s |
| PLIP | 249/300 (83.0%) | 247/300 (82.3%) | -0.7 pp | 0.014 s |

MUSK's tuned result was 87/100 adenocarcinoma, 96/100 squamous carcinoma,
and 100/100 benign. The other models did not benefit from the MUSK-tuned
phrase, so prompt tuning should remain model-specific.

The newer validated-prompt branch also contains a separate frozen 1,500-image
MUSK check. It was not merged into `main` because that branch predates and
removes the current four-model CONCH/tunnel integration.
