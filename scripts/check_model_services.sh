#!/usr/bin/env bash
set -euo pipefail

for entry in \
  "CONCH_ENDPOINT|${CONCH_ENDPOINT:-http://127.0.0.1:8802}" \
  "MUSK_ENDPOINT|${MUSK_ENDPOINT:-http://127.0.0.1:8801}" \
  "QUILTNET_ENDPOINT|${QUILTNET_ENDPOINT:-http://127.0.0.1:8803}" \
  "PLIP_ENDPOINT|${PLIP_ENDPOINT:-http://127.0.0.1:8804}"; do
  name="${entry%%|*}"
  endpoint="${entry#*|}"
  if response=$(curl --silent --show-error --max-time 5 "${endpoint%/}/health"); then
    echo "$name: $response"
  else
    echo "$name: unavailable ($endpoint)" >&2
  fi
done
