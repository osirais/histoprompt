# Validated prompt tuning for MUSK (lung)

## Short answer

On 450 held-out lung images from the fixed LC25000 benchmark, validated tuning classified **423 correctly (94.0%)**.
Original MUSK classified 403 (89.6%) and the plain `histology showing {label}` template 416 (92.4%). Against original
MUSK it fixed 20 images and broke none (sign test p ≈ 1e-6); against the plain template it fixed 7 and broke none
(p = 0.008). Three different prompt-writing LLMs arrived at the same result.

| Prompts | Correct | Errors | Fixed / broken vs original | Fixed / broken vs template |
|---|---:|---:|---:|---:|
| Enhanced MUSK, gemma-4-31b-it (descriptions from the team's 600-image run) | 356 (79.1%) | 94 | 21 / 68 | 11 / 71 |
| Enhanced MUSK, gemma-4-31b-it (descriptions from a 99-image rerun) | 375 (83.3%) | 75 | 23 / 51 | 13 / 54 |
| Enhanced MUSK, ornith-1.0-35b | 387 (86.0%) | 63 | 26 / 42 | 14 / 43 |
| Enhanced MUSK, nemotron-3-super-120b-a12b | 395 (87.8%) | 55 | 22 / 30 | 11 / 32 |
| Original MUSK: `a histopathology image showing {label}` | 403 (89.6%) | 47 | — | |
| Template: `histology showing {label}` | 416 (92.4%) | 34 | 13 / 0 | — |
| **Validated tuning** (ornith-1.0-35b, deepseek-v4-flash or gemma-4-31b-it) | **423 (94.0%)** | **27** | **20 / 0** | **7 / 0** |

Enhanced MUSK is the repo's `evidence_generated` strategy: long LLM-written evidence descriptions for every label,
scored here with the exact descriptions each LLM wrote earlier (`results/enhanced_450.json`). On these 450 images it
is below original MUSK whichever LLM writes the descriptions: each version fixes some images but breaks more.
Validated tuning breaks none. (On a 99-image subset, ornith's and nemotron's Enhanced versions had looked better than
original MUSK; that didn't hold on 450 images.)

## Fresh test: 1,500 never-used images

To rule out reuse of the 450 test images (they were looked at while the method was developed), every prompt set was
frozen to a file first (`fresh-test/frozen_prompts.json`). Then 1,500 LC25000 lung images (500 per label) were drawn
with a new seed, excluding the 600-image benchmark and the tuning and confirmation sets, and each set was scored once.
The images used to choose prompts and the images used to score them never overlap.

| Prompts | Correct (1,500) | Fixed / broken vs original | Fixed / broken vs template |
|---|---:|---:|---:|
| Original MUSK | 1318 (87.9%) | — | |
| Template: `histology showing {label}` | 1361 (90.7%) | 44 / 1 | — |
| Tuned (ornith-1.0-35b) | 1383 (92.2%) | 67 / 2 | 23 / 1 (p = 1.5e-6) |
| **Tuned (deepseek-v4-flash)** | **1384 (92.3%)** | **67 / 1** | **23 / 0** (p = 1.2e-7) |
| **Tuned (gemma-4-31b-it)** | **1384 (92.3%)** | **67 / 1** | **23 / 0** (p = 1.2e-7) |
| **Tuned (gemma-4-31b-it, committed-script rerun)** | **1384 (92.3%)** | **67 / 1** | **23 / 0** (p = 1.2e-7) |

The gain over original MUSK matches the 450-image test (+4.4 points in both), so the earlier result wasn't inflated
by reusing those images. These are still LC25000 images (augmented from shared originals); a different lung dataset
would be the next test of generalisation.

## Per-model template selection (step 0)

Models prefer different wording: in a teammate's per-model run, CONCH scored 94.0% with
`a histopathology image showing {label}` but 65.1% with `histology showing {label}`. Step 0 therefore chooses the base
template from 33 candidates before tuning phrases: this repository's 4, the 4 used by MUSK's benchmark code and the
Quilt-1M paper (Table 10), CONCH's 22 (`prompts/nsclc_prompts_all_per_class.json` in mahmoodlab/CONCH), and PLIP's 3
(its reproducibility code). A template replaces the default only if it clears the same three bars. Phrases are then
inserted right after the label (`an H&E image of {label} with {phrase}.`). `--no-template-search` reproduces the
fixed-template version, which is also tagged `tuning-v1-fixed-template`.

For MUSK, step 0 chose CONCH's `an H&E stained image of {label}.` (tuning +2.4 points, 33 fixed / 11 broken,
p = 0.0006; confirmation +1.2 points). No gemma-4-31b-it phrase cleared the bars on top of it.

| MUSK prompts | 450 test | 1,500 fresh | Cancer called benign (fresh) | Adeno → squamous | Squamous → adeno |
|---|---:|---:|---:|---:|---:|
| Original MUSK | 403 | 1318 (87.9%) | 56 | 96 | 30 |
| `histology showing {label}` | 416 | 1361 (90.7%) | 23 | 90 | 26 |
| v1: fixed template + benign phrase | 423 | 1384 (92.3%) | **0** | 90 | 26 |
| v2: template selection | **427** | **1390 (92.7%)** | 7 | **60** | 43 |

v2 matches or slightly exceeds v1 on accuracy (on the fresh images: 32 fixed, 26 broken, not significant), with a
different error profile. It separates the two carcinomas better, but calls 7 cancers benign where v1 called none.
Which to deploy is a clinical choice; missing a cancer is usually the costlier error.

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

You need: this repository (`uv sync`), a Lumen API key (`LUMEN_API_KEY` in `.env.local`), and MUSK access. The hosted
MUSK needs `MUSK_API_KEY` and the Delta tunnel (`scripts/start_delta_tunnel.sh`); local MUSK needs `MUSK_BACKEND=local`
and an `HF_TOKEN` with the MUSK terms accepted. About 1.9 GB of disk for LC25000.

```bash
# 1. Download the four LC25000 Parquet shards at the benchmark's pinned commit (public, about 1.9 GB)
uv run --with huggingface-hub python -c "from huggingface_hub import snapshot_download; snapshot_download('1aurent/LC25000', repo_type='dataset', revision='2387ffed63932faa8fd05c679ffec85fc3153f61', local_dir='.benchmark-cache/lc25000-parquet', allow_patterns=['data/*.parquet'])"

# 2. Build the tuning and confirmation sets (images go to the ignored .benchmark-cache/; the build checks them
#    against benchmarks/lc25000-tuning/manifest.json by SHA-256)
uv run --with pyarrow python scripts/build_lc25000_tuning_sets.py

# 3. Tune and score; reasoning LLMs need a larger output budget. About 15-20 minutes with the hosted MUSK.
LUMEN_MODEL=gemma-4-31b-it LUMEN_MAX_TOKENS=16000 uv run python scripts/tune_prompts.py \
    --output benchmarks/lc25000-tuning/results/my-run.json
```

The 450 test images are already in the repository (`benchmarks/lc25000-1000/images`).

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
