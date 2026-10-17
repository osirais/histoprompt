# Validated prompt tuning for MUSK (lung)

## Short answer

On 450 held-out lung images from the fixed LC25000 benchmark, validated tuning classified **423 correctly (94.0%)**.
Original MUSK classified 403 (89.6%) and the plain `histology showing {label}` template 416 (92.4%). Against original
MUSK it fixed 20 images and broke none (sign test p ≈ 1e-6); against the plain template it fixed 7 and broke none
(p = 0.008). Three different prompt-writing LLMs arrived at the same result.

| Prompts | Correct | Errors | Fixed / broken vs original | Fixed / broken vs template |
|---|---:|---:|---:|---:|
| Original MUSK: `a histopathology image showing {label}` | 403 (89.6%) | 47 | — | |
| Template: `histology showing {label}` | 416 (92.4%) | 34 | 13 / 0 | — |
| **Validated tuning** (ornith-1.0-35b, deepseek-v4-flash or gemma-4-31b-it) | **423 (94.0%)** | **27** | **20 / 0** | **7 / 0** |

## Tuned prompts

Only the benign prompt changed; no phrase for the two carcinomas cleared the bars.

```
histology showing benign lung tissue with intact alveolar sacs
histology showing lung adenocarcinoma
histology showing lung squamous cell carcinoma
```

The other two LLMs chose equivalent benign phrases with identical results: `organized pulmonary parenchyma structure`
(ornith) and `alveolar spaces intact` (deepseek). The phrase removed every "tumour called benign" error (8 → 0). The
remaining 27 errors are all adenocarcinoma ↔ squamous cell carcinoma.

## Method

`histoprompt/prompt_tuning.py`, run with `scripts/tune_prompts.py`.

| Set | Images | Use |
|---|---|---|
| Tuning | 900 extra LC25000 lung images (300 per label), not in the 600-image benchmark | choose phrases |
| Confirmation | 900 more extra images | confirm a chosen phrase |
| Test | first 150 per label of the fixed 600-image benchmark (450) | scored once at the end |

1. The LLM writes 8 short (2–6 word) candidate phrases per label: H&E-visible, characteristic of that label, no stain
   markers, no features common to all carcinomas. Phrases sharing a content word with another label's phrases are
   removed. One shared phrase ("alveolar walls") once made MUSK call every benign image adenocarcinoma.
2. Each phrase is tried as `histology showing {label} with {phrase}`. The best phrase for a label is kept only if it
   clears **all** of:
   - **accuracy bar:** at least +1.0 percentage point on the tuning set;
   - **significance bar:** paired exact sign test (images fixed vs broken), one-sided p < 0.05;
   - **confirmation:** at least +0.5 points on the confirmation set.
3. One feedback round: the LLM is told MUSK's most common remaining confusion and writes new phrases for that label,
   under the same bars.
4. Accuracy (right or wrong) is the only measure.

The two bars complement each other. In these runs, deepseek's `basaloid nests` for squamous cell carcinoma was +1.2
points, so it passed the accuracy bar, but it fixed 41 images while breaking 30 (p = 0.12) and was rejected. With
larger tuning sets, the accuracy bar in turn stops tiny but "significant" gains.

An earlier version without these safeguards (150 tuning images, any improvement accepted, no confirmation set) picked
phrases that won by 2–3 images. On the same 450 test images they tied with or were worse than the template (one was
12 images worse).

## Reproduce

```bash
# 1. LC25000 Parquet shards at the benchmark's pinned commit, then the tuning and confirmation sets
#    (images go to the ignored .benchmark-cache/; this manifest pins them by SHA-256)
uv run --with pyarrow python scripts/build_lc25000_tuning_sets.py --source-dir <dir with the 4 LC25000 shards>

# 2. Tune (MUSK reachable, e.g. through scripts/start_delta_tunnel.sh); reasoning LLMs need a larger output budget
LUMEN_MODEL=gemma-4-31b-it LUMEN_MAX_TOKENS=16000 uv run python scripts/tune_prompts.py \
    --output benchmarks/lc25000-tuning/results/gemma-4-31b-it.json
```

The LLM's suggestions vary between runs, so a rerun can choose different wording. Running the committed script
once more with gemma-4-31b-it (`results/gemma-4-31b-it.json`) chose `clear air spaces` for benign and gave the same result:
423/450, 7 fixed and 0 broken against the template (p = 0.008). Freeze the chosen prompts rather
than re-tuning per use. `results/experiment-run/` holds the three runs reported above, with every phrase tried and its
gain, fixed/broken counts and p-value.

## Limitations

- **Lung only.** The phrases are specific to these three labels; other disease groups need their own labelled images
  and tuning run (LC25000 also has colon).
- **LC25000 is augmented** (rotations and flips of about 750 original lung images), so tuning and test images share
  originals. Only label-level wording is chosen, so answers don't leak, but this isn't an independent clinical dataset.
- **Adenocarcinoma vs squamous cell carcinoma** isn't improved by wording. Prompt ensembles or learned prompts need
  MUSK's per-label scores (local MUSK); the hosted service returns only the top label.
- Research benchmark only, not clinical validation.
