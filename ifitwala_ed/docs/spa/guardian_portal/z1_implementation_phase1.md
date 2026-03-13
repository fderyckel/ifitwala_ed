# Guardian Portal Implementation Plan (March 2026)

Status: Working note
Authority: Non-authoritative
Scope: Implementation plan derived from the canonical guardian portal contracts
Last updated: 2026-03-13

This note turns the authoritative `/hub/guardian` contracts into a concrete implementation sequence. It does not define behavior on its own.

## 1. Current Baseline

Status: Completed

Source docs:
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/04_guardian_actions.md`

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/guardianHomeService.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`

Baseline summary:

1. The proposed Phase-1 guardian home bundle already exists and is wired through the SPA.
2. `/hub/guardian`, `/hub/guardian/students/:student_id`, `/hub/guardian/activities`, and `/hub/guardian/portfolio` already exist.
3. The main remaining work is contract alignment, regression coverage, and closure of explicitly deferred guardian actions.

## 2. Risks To Control

Status: In progress

Source docs:
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/04_guardian_actions.md`

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`

Primary risks:

1. Visibility regressions that leak data outside linked-student scope.
2. Contract drift between the snapshot payload, the TypeScript types, and the rendered guardian pages.
3. Silent UI dead-ends where an action is blocked without user feedback.
4. Expanding planned actions without first documenting the workflow endpoint and permission model.

## 3. Recommended PR Sequence

Status: In progress

Source docs:
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/04_guardian_actions.md`

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/api/activity_booking.py`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`

PR sequence:

1. Documentation consolidation: keep the four guardian portal contracts authoritative and keep notes non-authoritative.
2. Guardian home regression expansion: add endpoint tests that exercise linked students, guardian-visible logs, published outcomes, unread communication counts, and forbidden-key protection end to end.
3. SPA contract parity: add page-level tests for `GuardianHome.vue` and `GuardianStudentShell.vue` so zone order, blocked states, and empty states are locked.
4. Actionability pass: make every guardian blocker and attention item route to a direct action or explicit next step where the backend already provides one.
5. Deferred-scope decision: choose whether policy acknowledgement, direct messaging, monitoring mode, uploads, or payments belong on `/hub/guardian`; each one requires an explicit contract update before implementation.

## 4. Exact Files To Touch In The Next Implementation Pass

Status: Planned

Source docs:
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/04_guardian_actions.md`

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/api/test_activity_booking.py`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- New UI tests: Planned

Target files by concern:

1. Snapshot parity and visibility: `api/guardian_home.py`, `api/test_guardian_home.py`.
2. Guardian home rendering and blocked states: `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue`.
3. SPA regression coverage: new guardian page tests adjacent to the guardian pages plus `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`.
4. Guardian activity actions: `api/activity_booking.py`, `api/test_activity_booking.py`, and `ui-spa/src/pages/guardian/GuardianActivities.vue` only if the contract changes.

## 5. Done Definition

Status: Planned

Source docs:
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/04_guardian_actions.md`

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/api/activity_booking.py`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- Guardian page tests: Planned

Done means:

1. The four authoritative guardian portal docs match the real `/hub/guardian` code paths.
2. The guardian snapshot payload, TypeScript contract, and rendered zones stay in lock-step under regression tests.
3. Every guardian-visible item is server-filtered and every guardian action uses a named workflow endpoint.
4. Deferred actions remain clearly marked as planned until their routes, APIs, and tests exist.
