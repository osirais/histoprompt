#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"

if ! command -v uv >/dev/null 2>&1; then
  echo "HistoPrompt needs uv. Install it from https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if [[ ! -f .env.local ]]; then
  echo "Local configuration is missing. Run ./scripts/setup.sh first."
  exit 1
fi

# shellcheck disable=SC1091
source .env.local

if [[ -z "${LUMEN_API_KEY:-}" ]]; then
  echo "LUMEN_API_KEY is missing. Run ./scripts/setup.sh."
  exit 1
fi

if [[ "${MUSK_BACKEND:-remote}" == "remote" && -z "${MUSK_API_KEY:-}" ]]; then
  echo "MUSK_API_KEY is missing. Run ./scripts/setup.sh."
  exit 1
fi

if [[ "${MUSK_BACKEND:-remote}" == "local" ]]; then
  uv sync --extra musk --extra dev
else
  uv sync --extra dev
fi

if [[ "${MUSK_BACKEND:-remote}" == "remote" ]]; then
  echo "MUSK uses the Delta tunnel. Keep this running in another terminal:"
  echo "  ./scripts/start_delta_tunnel.sh"
fi

exec uv run python app.py

