# Does a MUSK prompt template carry over to other cancers and tasks?

Experiment, MUSK only. Results will be added after the runs finish.

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
