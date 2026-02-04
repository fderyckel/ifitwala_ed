#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
types_dir="$root_dir/ifitwala_ed/ui-spa/src/types"
spa_dir="$root_dir/ifitwala_ed/ui-spa/src"

if rg -n "export const" "$types_dir"; then
  echo "ERROR: runtime export found under ui-spa/src/types/"
  exit 1
fi

if rg -n "fetch\\s*\\(" "$spa_dir"; then
  echo "ERROR: fetch() usage found under ui-spa/src/"
  exit 1
fi

echo "contracts guardrails: ok"
