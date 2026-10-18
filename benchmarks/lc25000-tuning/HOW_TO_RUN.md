# How to run full validated prompt tuning

The normal workflow has two stages for every model: select a base template, then ask Lumen for label-specific phrases
and keep a phrase only when it passes the tuning, paired sign-test, and confirmation gates. Do not use
`--template-only` for a full tuning run.

## One-time setup

1. Run `uv sync` in the repository root.
2. Put `LUMEN_API_KEY`, the four hosted-model endpoint URLs, and their bearer keys in the ignored `.env.local` file.
3. Start `./scripts/start_delta_tunnel.sh` and verify `./scripts/check_model_services.sh`.
4. Build the frozen LC25000 tuning and confirmation images if `.benchmark-cache/lc25000-tuning/` is absent:

```bash
uv run --with huggingface-hub python -c "from huggingface_hub import snapshot_download; snapshot_download('1aurent/LC25000', repo_type='dataset', revision='2387ffed63932faa8fd05c679ffec85fc3153f61', local_dir='.benchmark-cache/lc25000-parquet', allow_patterns=['data/*.parquet'])"
uv run --with pyarrow python scripts/build_lc25000_tuning_sets.py
```

## Run all four models

```bash
uv run python scripts/run_full_tuning_suite.py --batch-size 32 --workers 4
```

This runs the full two-stage method independently against MUSK, CONCH, QuiltNet, and PLIP, then writes one complete
audit log per model under `results/full-tuning/`. Batch size 32 changes request grouping only; it does not share model
scores or prompts.

To run one model directly:

```bash
LUMEN_MAX_TOKENS=16000 uv run python scripts/tune_prompts.py \
  --model musk --batch-size 32 \
  --output benchmarks/lc25000-tuning/results/full-tuning/musk.json
```

The output records the selected base template, every generated candidate, tuning and confirmation decisions, accepted
phrases, and the final held-out test comparison.

## Scope boundary

The supplied frozen development data covers benign lung tissue, lung adenocarcinoma, and lung squamous-cell carcinoma.
It can fully tune those labels only. The PathGen benchmark remains evaluation-only; its breast, colon, kidney, brain,
prostate, and rectal labels must not be described as phrase-tuned by this workflow.
