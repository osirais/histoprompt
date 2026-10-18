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
conch_remote_host="${DELTA_CONCH_HOST:-}"
conch_remote_port="${DELTA_CONCH_PORT:-8000}"
conch_local_port="${CONCH_TUNNEL_PORT:-8802}"
quiltnet_remote_host="${DELTA_QUILTNET_HOST:-}"
quiltnet_remote_port="${DELTA_QUILTNET_PORT:-8002}"
quiltnet_local_port="${QUILTNET_TUNNEL_PORT:-8803}"
plip_remote_host="${DELTA_PLIP_HOST:-}"
plip_remote_port="${DELTA_PLIP_PORT:-8003}"
plip_local_port="${PLIP_TUNNEL_PORT:-8804}"

if [[ -z "$delta_username" ]]; then
  echo "Set DELTA_USERNAME in .env.local or pass your NCSA username:"
  echo "  ./scripts/start_delta_tunnel.sh <username>"
  exit 1
fi

if [[ -z "$remote_host" ]]; then
  echo "DELTA_MUSK_HOST is missing. Copy the current MUSK host into .env.local."
  exit 1
fi

forward_args=("-L" "127.0.0.1:${local_port}:${remote_host}:${remote_port}")
if [[ -n "$conch_remote_host" ]]; then
  forward_args+=("-L" "127.0.0.1:${conch_local_port}:${conch_remote_host}:${conch_remote_port}")
  echo "Opening local port $conch_local_port to the NCSA-hosted CONCH service."
else
  echo "CONCH tunnel disabled (set DELTA_CONCH_HOST to enable it)."
fi
if [[ -n "$quiltnet_remote_host" ]]; then
  forward_args+=("-L" "127.0.0.1:${quiltnet_local_port}:${quiltnet_remote_host}:${quiltnet_remote_port}")
  echo "Opening local port $quiltnet_local_port to the NCSA-hosted QuiltNet service."
fi
if [[ -n "$plip_remote_host" ]]; then
  forward_args+=("-L" "127.0.0.1:${plip_local_port}:${plip_remote_host}:${plip_remote_port}")
  echo "Opening local port $plip_local_port to the NCSA-hosted PLIP service."
fi
echo "Opening local port $local_port to the NCSA-hosted MUSK service."
echo "Complete the NCSA password and Duo prompts; leave this terminal open."
exec ssh \
  -o ExitOnForwardFailure=yes \
  -N \
  "${forward_args[@]}" \
  "${delta_username}@login.delta.ncsa.illinois.edu"

