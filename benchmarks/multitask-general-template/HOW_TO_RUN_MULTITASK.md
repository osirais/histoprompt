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
