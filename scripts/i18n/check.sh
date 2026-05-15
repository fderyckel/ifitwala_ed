#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report_dir="$(mktemp -d "${TMPDIR:-/tmp}/ifitwala-i18n-check.XXXXXX")"

cleanup() {
  rm -rf "$report_dir"
}
trap cleanup EXIT

python3 "$root_dir/scripts/i18n/audit.py" \
  --root "$root_dir" \
  --output "$report_dir/current.json" \
  --fail-on-critical

echo "i18n guardrails: ok"
