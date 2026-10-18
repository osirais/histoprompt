# How to run the multitask template experiment

On the `validated-prompt-tuning` branch. What the experiment tests is in [`README.md`](README.md).

## One-time setup

1. **Install and credentials:** as in [`../lc25000-tuning/HOW_TO_RUN.md`](../lc25000-tuning/HOW_TO_RUN.md):
   `uv sync`, `.env.local` with `LUMEN_API_KEY` and MUSK access (hosted MUSK through
   `./scripts/start_delta_tunnel.sh`, left open in a separate terminal, or local MUSK).
2. **LC25000** (lung and colon tasks), if not already downloaded:
   ```bash
   uv run --with huggingface-hub python -c "from huggingface_hub import snapshot_download; snapshot_download('1aurent/LC25000', repo_type='dataset', revision='2387ffed63932faa8fd05c679ffec85fc3153f61', local_dir='.benchmark-cache/lc25000-parquet', allow_patterns=['data/*.parquet'])"
   uv run --with pyarrow python scripts/build_lc25000_tuning_sets.py
   ```
   The lung task reuses the tuning images built by the second command.
3. **Build the four task sets** (about 15 minutes; NCT-CRC-HE and PatchCamelyon are read from Hugging Face):
   ```bash
   uv run --with pyarrow --with huggingface-hub python benchmarks/multitask-general-template/build_sets.py
   ```
   Images go to `.benchmark-cache/multitask/` (about 400 MB, ignored by Git) and are checked against
   `manifest.json`. If the LC25000 parquet files are elsewhere, set `LC25000_PARQUET_DIR=/path/to/data`.

## Run

```bash
# step 0 only: leave-one-task-out transfer and the general template (about 20 minutes, no LLM)
uv run python benchmarks/multitask-general-template/run_general.py

# step 1: general template + per-task phrases (about 20 minutes; needs results.json from the run above)
LUMEN_MODEL=gemma-4-31b-it LUMEN_MAX_TOKENS=16000 uv run python benchmarks/multitask-general-template/run_phrases.py
```

| Output | Contents |
|---|---|
| `results.json` | per held-out task: transferred template, the task's own template, test scores vs the baseline with fixed/broken counts and p-values, every template tried; then the general template on all tasks |
| `results_phrases.json` | per task: accepted phrases, test scores for baseline / general template / general template + phrases, the full tuning log |

## Files

| File | Role |
|---|---|
| `build_sets.py` | builds and verifies the tuning, confirmation and test images for the four tasks |
| `manifest.json` | every image with its label, source key and SHA-256 |
| `run_general.py` | template selection across tasks (step 0) |
| `run_phrases.py` | phrase tuning per task on the general template (step 1) |
| `backends.py` | MUSK and the hosted CONCH / QuiltNet / PLIP classifiers |
| `run_all_models.sh` | both steps for several models in parallel |

## Other models: CONCH, QuiltNet-B-32, PLIP

Both scripts take `--model musk|conch|quiltnet|plip` (default `musk`). The method is the same for every model: the
shared template is selected for that model on all four tasks, then the phrases are tuned for that model per task.
Nothing is reused from MUSK, because prompts chosen for one model must not be reused for another.

1. Add the model's key and endpoint to `.env.local` (same names as on `main`):
   `CONCH_API_KEY`, `CONCH_ENDPOINT=http://127.0.0.1:8802`; `QUILTNET_API_KEY`, `QUILTNET_ENDPOINT=http://127.0.0.1:8803`;
   `PLIP_API_KEY`, `PLIP_ENDPOINT=http://127.0.0.1:8804`.
2. Start the tunnel with those ports forwarded. `scripts/start_delta_tunnel.sh` on `main` forwards 8802–8804 when
   `DELTA_CONCH_HOST`, `DELTA_QUILTNET_HOST` and `DELTA_PLIP_HOST` are set.
3. Run one model:
   ```bash
   uv run python benchmarks/multitask-general-template/run_general.py --model conch
   LUMEN_MODEL=gemma-4-31b-it LUMEN_MAX_TOKENS=16000 uv run python benchmarks/multitask-general-template/run_phrases.py --model conch
   ```
   or all three in parallel (logs in `logs/`):
   ```bash
   benchmarks/multitask-general-template/run_all_models.sh            # conch quiltnet plip
   SKIP_LOTO=1 benchmarks/multitask-general-template/run_all_models.sh   # two-part method only, faster
   ```

Results go to `results_<model>.json` and `results_phrases_<model>.json` (MUSK keeps `results.json` and
`results_phrases.json`). For each task, `results_phrases_<model>.json` reports the test score for the model's own
baseline prompt `a histopathology image showing {label}`, the shared template, and the shared template plus phrases.
Expect about 20 minutes per step per model with the hosted services. `--skip-loto` makes step 0 roughly five times
faster.

The hosted-model adapter is `backends.py`. It was checked by pointing it at the hosted MUSK endpoint, which uses the
same `/classify` format: on 18 crc9 images it gave identical predictions to the MUSK backend. It has not been run
against CONCH, QuiltNet or PLIP themselves.
