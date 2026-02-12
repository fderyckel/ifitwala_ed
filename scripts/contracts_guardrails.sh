#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
types_dir="$root_dir/ifitwala_ed/ui-spa/src/types"
contracts_types_dir="$types_dir/contracts"
spa_dir="$root_dir/ifitwala_ed/ui-spa/src"
frappe_transport_file="$spa_dir/lib/frappe.ts"
legacy_client_file="$spa_dir/lib/client.ts"

# Contract-only types should remain type-only.
if [ -d "$contracts_types_dir" ] && rg -n "export const" "$contracts_types_dir"; then
  echo "ERROR: runtime export found under ui-spa/src/types/contracts/"
  exit 1
fi

# Only transport boundary modules may call fetch directly.
legacy_fetch_hits="$(rg -n -P '(?<![\w\.])fetch\s*\(' "$spa_dir" || true)"
legacy_fetch_hits="$(printf '%s\n' "$legacy_fetch_hits" | rg -v '/lib/frappe.ts:|/lib/client.ts:' || true)"
legacy_fetch_hits="$(printf '%s\n' "$legacy_fetch_hits" | rg -v -F 'function fetch(' || true)"
if [ -n "$legacy_fetch_hits" ]; then
  echo "WARN: direct fetch() usage found outside transport boundary modules."
  echo "$legacy_fetch_hits"
  echo "WARN: allowed temporarily for legacy surfaces; migrate progressively to transport wrappers."
fi

# Only lib/frappe.ts may call frappeRequest directly.
if rg -n -P "(?<![\\w\\.])frappeRequest\\s*\\(" "$spa_dir" \
  --glob '!lib/frappe.ts'; then
  echo "ERROR: frappeRequest() usage found outside lib/frappe.ts"
  exit 1
fi

# Enforce canonical POST payload shape: api(method, payload)
# Wrapping with { payload } is forbidden unless server signature requires it.
if rg -n "api\\s*\\(\\s*[^,]+\\s*,\\s*\\{\\s*payload\\s*\\}" "$spa_dir"; then
  echo "ERROR: forbidden wrapped payload shape detected: api(method, { payload })"
  exit 1
fi

# SPA navigation guardrail: do not hardcode /portal route base in client code.
legacy_portal_nav_hits="$(rg -n "window\\.location\\s*=\\s*['\\\"]/portal/" "$spa_dir" || true)"
if [ -n "$legacy_portal_nav_hits" ]; then
  echo "WARN: hardcoded /portal navigation detected."
  echo "$legacy_portal_nav_hits"
  echo "WARN: allowed temporarily for legacy surfaces; migrate to named routes."
fi

if [ ! -f "$frappe_transport_file" ] || [ ! -f "$legacy_client_file" ]; then
  echo "ERROR: expected transport boundary files are missing."
  exit 1
fi

echo "contracts guardrails: ok"
