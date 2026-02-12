#!/usr/bin/env bash
set -euo pipefail

# scripts/test_metrics.sh

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
app_dir="$root_dir/ifitwala_ed"

total_test_files=$(find "$app_dir" -type f -name 'test_*.py' | wc -l | tr -d ' ')

placeholder_files=0
real_test_files=0
while IFS= read -r test_file; do
	if rg -q "^[[:space:]]*def test_" "$test_file"; then
		real_test_files=$((real_test_files + 1))
	elif rg -q "^[[:space:]]*pass[[:space:]]*$" "$test_file"; then
		placeholder_files=$((placeholder_files + 1))
	fi
done < <(find "$app_dir" -type f -name 'test_*.py' | sort)

doctype_controllers=0
controllers_with_real_tests=0
while IFS= read -r controller; do
	doctype_controllers=$((doctype_controllers + 1))
	dir="$(dirname "$controller")"
	base="$(basename "$controller" .py)"
	test_file="$dir/test_${base}.py"
	if [ -f "$test_file" ] && rg -q "^[[:space:]]*def test_" "$test_file"; then
		controllers_with_real_tests=$((controllers_with_real_tests + 1))
	fi
done < <(find "$app_dir" -type f -path '*/doctype/*/*.py' ! -name '__init__.py' ! -name 'test_*.py' ! -name 'hooks.py' | sort)

api_modules=0
api_modules_with_tests=0
while IFS= read -r api_file; do
	api_modules=$((api_modules + 1))
	base="$(basename "$api_file" .py)"
	test_file="$(dirname "$api_file")/test_${base}.py"
	if [ -f "$test_file" ] && rg -q "^[[:space:]]*def test_" "$test_file"; then
		api_modules_with_tests=$((api_modules_with_tests + 1))
	fi
done < <(find "$app_dir/api" -maxdepth 1 -type f -name '*.py' ! -name '__init__.py' ! -name 'test_*.py' | sort)

api_modules_without_tests=$((api_modules - api_modules_with_tests))

cat <<METRICS
== Ifitwala Test Metrics ==
total_test_files=$total_test_files
real_test_files=$real_test_files
placeholder_test_files=$placeholder_files
doctype_controllers=$doctype_controllers
doctype_controllers_with_real_tests=$controllers_with_real_tests
api_modules=$api_modules
api_modules_with_real_tests=$api_modules_with_tests
api_modules_without_real_tests=$api_modules_without_tests
METRICS

if [ "${ENFORCE_TEST_BASELINE:-0}" = "1" ]; then
	max_placeholder="${MAX_PLACEHOLDER_TEST_FILES:-9999}"
	min_real_tests="${MIN_REAL_TEST_FILES:-0}"

	if [ "$placeholder_files" -gt "$max_placeholder" ]; then
		echo "ERROR: placeholder test files ($placeholder_files) exceed MAX_PLACEHOLDER_TEST_FILES=$max_placeholder"
		exit 1
	fi

	if [ "$real_test_files" -lt "$min_real_tests" ]; then
		echo "ERROR: real test files ($real_test_files) below MIN_REAL_TEST_FILES=$min_real_tests"
		exit 1
	fi
fi
