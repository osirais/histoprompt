#!/usr/bin/env bash
# Shared template (step 0) then per-task phrases (step 1) for each model, all models in parallel.
# Usage: benchmarks/multitask-general-template/run_all_models.sh [models...]   (default: conch quiltnet plip; MUSK results are committed)
# Set SKIP_LOTO=1 to skip the leave-one-task-out transfer test and run only the two-part method (faster).
set -euo pipefail
cd "$(dirname "$0")/../.."
dir=benchmarks/multitask-general-template
models=("$@")
[ $# -eq 0 ] && models=(conch quiltnet plip)
extra=()
[ "${SKIP_LOTO:-0}" = 1 ] && extra=(--skip-loto)
mkdir -p "$dir/logs"
for m in "${models[@]}"; do
  (
    uv run python "$dir/run_general.py" --model "$m" "${extra[@]}" > "$dir/logs/general_$m.log" 2>&1 &&
    LUMEN_MODEL="${LUMEN_MODEL:-gemma-4-31b-it}" LUMEN_MAX_TOKENS="${LUMEN_MAX_TOKENS:-16000}" \
      uv run python "$dir/run_phrases.py" --model "$m" > "$dir/logs/phrases_$m.log" 2>&1 &&
    echo "[$m] done" || echo "[$m] FAILED, see $dir/logs/"
  ) &
done
wait
tail -n 6 "$dir"/logs/phrases_*.log
