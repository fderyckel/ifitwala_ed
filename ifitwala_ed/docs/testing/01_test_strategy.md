<!-- ifitwala_ed/docs/testing/01_test_strategy.md -->
# Ifitwala_Ed Test Strategy (Canonical)

## 1. Purpose

This document defines the canonical testing strategy for `ifitwala_ed`.

Goals:
1. Protect locked architectural invariants.
2. Catch regressions early in pull requests.
3. Keep test feedback fast for contributors.
4. Run heavy regression suites nightly on dedicated non-production infrastructure.

## 2. Test Pyramid for Ifitwala_Ed

1. Domain unit/invariant tests (highest volume)
- Pure helper functions and deterministic controller/service invariants.
- Fast, low setup, high signal.

2. Frappe DocType integration tests (moderate volume)
- Validate transactional and permission behavior at the Document boundary.
- Use `FrappeTestCase` when DB interactions are part of the invariant.

3. API contract tests (targeted)
- Ensure endpoint-level payload and visibility contracts.
- Focus on high-risk endpoints (attendance, calendar, activity booking, enrollment, assessment).

4. SPA unit/contract tests (growing)
- Verify client transport contracts and composable logic.
- Validate locked UI contract invariants (payload shape, overlay behavior, TDZ safety checks where feasible).

5. Nightly heavy suites
- Full app backend run and extended domain/API suites.

## 3. Prioritized Invariants

1. Enrollment remains transactional and snapshot-based.
2. Assessment truth stays criterion-authoritative.
3. Permissions are always server-side and hierarchy-safe.
4. Time logic always follows site timezone and canonical coercion.
5. File governance remains dispatcher/classification enforced.
6. SPA contract shape remains canonical (`api(method, payload)`).

## 4. Test Authoring Rules

1. Prefer deterministic tests over brittle UI-path tests.
2. Keep each test focused on one invariant.
3. Use mocks/patches for external systems where possible.
4. Avoid schema invention; use existing DocType fields only.
5. Add or update tests in the same PR as behavior changes.

## 5. Success Metrics (tracked by `scripts/test_metrics.sh`)

1. `placeholder_test_files`
2. `doctype_controllers_with_real_tests`
3. `api_modules_with_real_tests`

The metrics script is informational by default and can be enforced with environment thresholds in CI.
