# How to run validated prompt tuning

The script is `scripts/tune_prompts.py`, on the `validated-prompt-tuning` branch. The method and results are in
[`README.md`](README.md).

## One-time setup

1. **Install:** `uv sync` in the repository root.
2. **Credentials** in `.env.local` (ignored by Git):
   - `LUMEN_API_KEY`: the LLM that suggests phrases.
   - MUSK access, either:
     - **Hosted MUSK** on Delta: `MUSK_BACKEND=remote`, `MUSK_API_KEY`, `DELTA_USERNAME` (your own NCSA username),
       then start the tunnel in a separate terminal and leave it open:
       `./scripts/start_delta_tunnel.sh` (asks for your NCSA password and Duo), or
     - **Local MUSK**: `MUSK_BACKEND=local`, `MUSK_DEVICE=auto` and an `HF_TOKEN` with the MUSK terms accepted.
3. **Data** (about 1.9 GB):
   ```bash
   uv run --with huggingface-hub python -c "from huggingface_hub import snapshot_download; snapshot_download('1aurent/LC25000', repo_type='dataset', revision='2387ffed63932faa8fd05c679ffec85fc3153f61', local_dir='.benchmark-cache/lc25000-parquet', allow_patterns=['data/*.parquet'])"
   uv run --with pyarrow python scripts/build_lc25000_tuning_sets.py
   ```
   The second command builds the 900 tuning and 900 confirmation images in `.benchmark-cache/lc25000-tuning/` and
   checks them against `manifest.json`. The 450 test images are already in the repository.

## Run

```bash
LUMEN_MODEL=gemma-4-31b-it LUMEN_MAX_TOKENS=16000 uv run python scripts/tune_prompts.py \
    --output benchmarks/lc25000-tuning/results/my-run.json
```

It takes about 45 minutes with the hosted MUSK: step 0 (the template) is about 22 minutes, step 1 (the phrases) about
20. The output JSON contains the chosen template and phrases, every candidate tried with its gain, fixed/broken
counts and p-value, and the test scores against original MUSK and the plain template.

| Option | Effect |
|---|---|
| `LUMEN_MODEL=...` | LLM that suggests phrases: `gemma-4-31b-it`, `ornith-1.0-35b`, `deepseek-v4-flash`, … (only step 1 uses it) |
| `LUMEN_MAX_TOKENS=16000` | output budget for the LLM; reasoning models return nothing at the default 1400 |
| `--output PATH` | where the results JSON is written |
| `--no-template-search` | skip step 0 and keep `--default-template`; this is the v1 behaviour (about 20 minutes) |
| `--default-template "..."` | starting template (default `histology showing {label}`); must contain `{label}` |
| `--candidates N` | phrases the LLM writes per label (default 8) |
| `--batch-size N` | images per MUSK request (default 8). 32–64 is about 1.5× faster, but only compare runs made with the same batch size |
| `--test-per-label N` | test images per label from the 600-image benchmark (default 150, i.e. 450) |

## Files

| File | Role |
|---|---|
| `scripts/tune_prompts.py` | runs the tuning against MUSK and scores the test set |
| `histoprompt/prompt_tuning.py` | the method: template list (with sources), the three bars, template selection, phrase tuning |
| `scripts/build_lc25000_tuning_sets.py` | builds and verifies the tuning and confirmation images |
| `benchmarks/lc25000-tuning/manifest.json` | the tuning and confirmation images, pinned by SHA-256 |
| `tests/test_prompt_tuning.py` | tests for the bars, template selection and tuning loop (`uv run --extra dev pytest`) |

## Other models (CONCH, QuiltNet, PLIP)

`scripts/tune_prompts.py` currently classifies with MUSK only. To tune another model, add a backend with the same
interface as the MUSK one (`classify_batch(images, prompts)` returning one prediction with a `.label` per image) and
use it in place of `make_musk_backend`. `histoprompt/prompt_tuning.py` needs no changes. Choosing the template per
model matters: CONCH scored 94.0% with `a histopathology image showing {label}` but 65.1% with
`histology showing {label}`. Prompts tuned for one model must not be reused for another.

## Previous version

The fixed-template version (v1, 423/450 on MUSK) is tagged `tuning-v1-fixed-template`:
`git checkout tuning-v1-fixed-template`, or run the current code with `--no-template-search`.
