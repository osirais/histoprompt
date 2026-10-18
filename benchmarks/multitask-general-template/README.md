# Does a MUSK prompt template carry over to other cancers and tasks?

Results below are for MUSK. The same two steps run for CONCH, QuiltNet-B-32 and PLIP with `--model` (see
[`HOW_TO_RUN_MULTITASK.md`](HOW_TO_RUN_MULTITASK.md)).

## Tasks

| Task | Labels | Tuning / confirmation | Test |
|---|---|---|---|
| lung | 3 (LC25000) | subsets of `benchmarks/lc25000-tuning` | first 150 per class of `benchmarks/lc25000-600` |
| colon | 2 (LC25000) | LC25000 colon outside the colon benchmark | same pool, disjoint |
| crc9 | 9 tissue classes (NCT-CRC-HE) | NCT-CRC-HE-100K | CRC-VAL-HE-7K (different patients) |
| pcam | metastasis vs normal lymph node (PatchCamelyon) | `valid` split | `test` split |

Instructions: [`HOW_TO_RUN_MULTITASK.md`](HOW_TO_RUN_MULTITASK.md).

## Scripts

- `build_sets.py`: builds the images into `.benchmark-cache/multitask/` and checks them against `manifest.json`.
  Set `LC25000_PARQUET_DIR` if the LC25000 parquet files are not in `.benchmark-cache/lc25000-parquet/data`.
- `run_general.py`: template only (step 0). Leave-one-task-out: select a template on three tasks, test it on the
  fourth; compare with the baseline (MUSK's `a histopathology image showing {label}`) and with the task's own
  template. Then one general template selected on all four tasks.
- `run_phrases.py`: the general template plus label phrases tuned per task with the usual bars (step 1).

Both runs use faster settings than `scripts/tune_prompts.py` (batch 64; `run_general.py` screens all templates on 25%
of each tuning set and tests the top 8 in full), so compare their numbers only with each other.

## Results: template only (`results.json`)

Baseline = MUSK's original prompt `a histopathology image showing {label}`. Test sets, correct out of n; fixed/broken
are images the template gets right/wrong that the baseline did not, with the one-sided sign-test p-value.

**Leave-one-task-out:** the template is selected on the other three tasks and never sees the held-out task.

| Held-out task | Baseline | Transferred template | Fixed / broken, p | Task's own template |
|---|---|---|---|---|
| lung | 403 / 450 | **419** | 26 / 10, p = 0.006 | 423 (`An H&E image patch of {label} tissue.`) |
| colon | 395 / 400 | 397 | 2 / 0, p = 0.25 | 395 (baseline kept) |
| crc9 | 319 / 450 | **311** | 8 / 16, p = 0.08 | 319 (baseline kept) |
| pcam | 327 / 400 | 330 | 12 / 9, p = 0.33 | 337 (`{label}, H&E stain.`) |
| total | 1444 / 1700 | 1457 (+13) | | 1474 (+30) |

All four held-out runs chose the same template, `a histopathological photograph showing {label}.`, and selecting on
all four tasks chose it too (tuning: 46 fixed / 17 broken pooled, p = 0.0002; it passed confirmation).

- The transferred template clearly helps only lung. Colon and pcam gain a little, within noise. It hurts crc9.
- crc9 gained 1.8 points on both its tuning and confirmation sets (NCT-CRC-HE-100K) but lost 1.8 on its test set
  (CRC-VAL-HE-7K, different patients and centre). A gain measured on one cohort did not carry over to another.
- Tailoring the template to each task gives about twice the total gain (+30 vs +13).

**Conclusion:** one shared template carries over in part, mainly where the baseline wording is weak. It is not a
substitute for selecting on labelled images from the target task.

## Caveats

- MUSK only, four tasks, one LLM-free selection run; faster settings than `scripts/tune_prompts.py` (see above).
- The source datasets contain some exact duplicate images: 27 of the 5,100 images share content with another image
  (same label each time). Five test images also appear in the same task's confirmation set (colon 4, lung 1). The
  confirmation set only gates acceptance, and five of 1,700 test images cannot change the conclusions above.
- An earlier build truncated NCT-CRC-HE file names, so 4 crc9 tuning/confirmation images were overwritten by others.
  `build_sets.py` now uses full names, and the results above come from the corrected sets. The fix changed the
  template transferred to lung and pcam (selected on sets that include crc9): before it, `a photomicrograph showing
  {label}.` narrowly won (+1.64 vs +1.59 points on tuning) and scored lung 422 / 450, pcam 330 / 400 (total +16).
  Colon, crc9 and the template selected on all four tasks were unchanged. The two near-tied templates show how
  little separates the top candidates.

## Results: general template + per-task phrases (`results_phrases.json`)

Step 1 of the validated tuning (Gemma `gemma-4-31b-it` phrases; accuracy, significance and confirmation bars) on top of
the general template `a histopathological photograph showing {label}.`, run separately for each task. Test sets:

| Task | Baseline | General template | **General template + phrases** | Task's own template (above) |
|---|---|---|---|---|
| lung | 403 / 450 | 419 | 419 (no phrase passed) | 423 |
| colon | 395 / 400 | 397 | 397 (no phrase passed) | 395 |
| crc9 | 319 / 450 | 311 | **364** (51 fixed / 6 broken vs baseline, p < 1e-9) | 319 |
| pcam | 327 / 400 | 330 | 330 (no phrase passed) | 337 |
| total | 1444 / 1700 | 1457 (+13) | **1510 (+66)** | 1474 (+30) |

Accepted crc9 phrases: background "no tissue present" (confirmation +9.8 points), lymphocytes "small lymphoid cells"
(+1.8), cancer-associated stroma "collagen rich stroma" (+2.4). The crc9 test set is CRC-VAL-HE-7K (other patients
and centre), so this gain held on a different cohort, unlike the template-only gain.

- The two-tier design (shared template, phrases tuned per task) gives the largest total gain and no task ends below
  the baseline.
- Phrases matter most where the baseline is weak and the labels are many and similar (crc9, 70.9% baseline). Where
  no phrase cleared the bars, the template was kept unchanged.
- The phrases are tuned on labelled images of each task: the shared part is the template, not the phrases.

### Check: crc9 phrases on the baseline prompt (`results_phrases_crc9_default_template.json`)

Same crc9 sets, same first-round Gemma candidates (`--reuse-candidates results_phrases.json`), but phrases tuned on
MUSK's default prompt `a histopathology image showing {label}` instead of the general template:

| crc9 test (450) | Correct | vs baseline |
|---|---|---|
| baseline | 319 | |
| baseline prompt + phrases | 362 | 46 fixed / 3 broken, p < 1e-10 |
| general template + phrases (above) | 364 | 51 fixed / 6 broken |

Accepted: background "no tissue present", lymphocytes "small lymphoid cells", cancer-associated stroma "fibrotic
connective tissue". The crc9 gain comes from the phrases; the template makes no real difference there (2 images). The
general template's contribution is lung; the phrases' is crc9.
