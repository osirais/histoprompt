#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$project_dir/.env.local" ]]; then
  # shellcheck disable=SC1091
  source "$project_dir/.env.local"
fi

delta_username="${DELTA_USERNAME:-${1:-}}"
remote_host="${DELTA_MUSK_HOST:-}"
remote_port="${DELTA_MUSK_PORT:-8001}"
local_port="${MUSK_TUNNEL_PORT:-8801}"

if [[ -z "$delta_username" ]]; then
  echo "Set DELTA_USERNAME in .env.local or pass your NCSA username:"
  echo "  ./scripts/start_delta_tunnel.sh <username>"
  exit 1
fi

if [[ -z "$remote_host" ]]; then
  echo "DELTA_MUSK_HOST is missing. Copy the current MUSK host into .env.local."
  exit 1
fi

echo "Opening local port $local_port to the NCSA-hosted MUSK service."
echo "Complete the NCSA password and Duo prompts; leave this terminal open."
exec ssh \
  -o ExitOnForwardFailure=yes \
  -N \
  -L "127.0.0.1:${local_port}:${remote_host}:${remote_port}" \
  "${delta_username}@login.delta.ncsa.illinois.edu"

