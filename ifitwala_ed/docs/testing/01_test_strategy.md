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

## 6. Regression Guardrails (2026-03 Lessons)

1. Fixture setup must respect DocType invariants.
- For guarded identity fields on `Student Applicant`, use lifecycle methods or controlled setup writes (`db_set(..., update_modified=False)`) instead of mutable `.save()` flows that trigger permission/immutability guards.

2. Permission logic must define mixed-role precedence.
- When a principal has both admissions/staff and applicant/family roles, staff precedence must be explicit in permission evaluators and covered by tests.

3. Binary fixtures must be type-valid.
- Do not use fake bytes behind `.pdf`/`.png` extensions; parser-level validation in Frappe/Pillow will fail and create false-negative test noise.

4. Mapping/default tests must assert invariant outcomes, not fragile literals.
- For code-mapped classification, assert slot resolution and completeness, and avoid assumptions that conflict with site-level defaults or environment-specific options.

5. Translation alias `_` is reserved.
- In Python modules importing `from frappe import _`, never shadow `_` with local temporary variables.

6. Governed file/image reads need permission-matrix tests.
- When a route resolves private media for a surface, test who can open it and who gets `403`; do not stop at helper-level URL-selection tests.

7. Private media contracts must stay server-owned.
- SPA and website consumers should receive server-resolved display URLs, never raw private paths, and regressions here should be fixed at the API/display-contract layer.
