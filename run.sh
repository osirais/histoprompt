#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"

if ! command -v uv >/dev/null 2>&1; then
  echo "Ashby needs uv. Install it from https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if [[ ! -f .env.local ]]; then
  cp .env.example .env.local
  echo "Created .env.local. Add DELTA_USERNAME, then restart Ashby."
fi

# shellcheck disable=SC1091
source .env.local

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

