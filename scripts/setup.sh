#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if ! command -v uv >/dev/null 2>&1; then
  echo "HistoPrompt needs uv. Install it from https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

uv sync --extra dev
uv run python scripts/configure.py

echo
echo "Setup complete. For hosted MUSK, use two terminals:"
echo "  Terminal 1: ./scripts/start_delta_tunnel.sh"
echo "  Terminal 2: ./run.sh"
