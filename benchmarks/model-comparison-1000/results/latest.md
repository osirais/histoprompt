# Four-model 1,000-image comparison

Live NCSA hosted-service benchmark using all 1,000 stored LC25000 tiles:
200 each of benign colon tissue, benign lung tissue, colorectal
adenocarcinoma, lung adenocarcinoma, and lung squamous cell carcinoma. Images
were sent in batches of 32. This is an engineering benchmark over augmented
tiles, not clinical validation.

The standard prompt was `histology showing {label}`. The tuned prompt changed
the benign-lung label to `histology showing benign lung tissue with intact
alveolar sacs`; the other labels remained unchanged because the validated
prompt branch only selected that additional phrase for the lung task.

This run did **not** rerun the branch's Lumen candidate-generation and
tuning process. It applied the branch's frozen winning prompt set at inference
time, exactly as recorded in
`benchmarks/lc25000-tuning/fresh-test/frozen_prompts.json` on
`origin/validated-prompt-tuning`.

| Model | Standard | Tuned | Change |
| --- | ---: | ---: | ---: |
| CONCH | 674/1,000 (67.4%) | 648/1,000 (64.8%) | -2.6 pp |
| MUSK | 892/1,000 (89.2%) | 901/1,000 (90.1%) | **+0.9 pp** |
| QuiltNet-B-32 | 778/1,000 (77.8%) | 770/1,000 (77.0%) | -0.8 pp |
| PLIP | 766/1,000 (76.6%) | 766/1,000 (76.6%) | 0.0 pp |

## MUSK per class

| Class | Standard | Tuned |
| --- | ---: | ---: |
| Benign colon | 200/200 | 200/200 |
| Benign lung | 200/200 | 200/200 |
| Colorectal adenocarcinoma | 141/200 | 141/200 |
| Lung adenocarcinoma | 162/200 | 170/200 |
| Lung squamous carcinoma | 189/200 | 190/200 |

MUSK improves mainly on lung adenocarcinoma (+8 images) and squamous
carcinoma (+1), while the broader colon classes are unchanged. This supports
keeping the tuned prompt as a MUSK-specific option rather than presenting it as
a universal prompt for every hosted model.
