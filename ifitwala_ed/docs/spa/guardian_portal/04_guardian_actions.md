# Guardian Portal Actions Contract (v0.2)

Status: Active
Audience: Humans, coding agents
Scope: Guardian-initiated actions inside `/hub/guardian`
Last updated: 2026-03-13

This document defines what guardians can currently do through the guardian portal and what remains planned.

## 1. Action Model

Status: Implemented

Code refs:
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`

Test refs:
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. Guardian actions are named workflow actions, not generic CRUD assembled on the client.
2. Visibility and action authority are separate concerns; seeing a row does not imply edit rights.
3. Every guardian mutation must be server-enforced and context-bound to linked students.
4. The current `/hub/guardian` implementation is read-mostly outside the activity booking flow.

## 2. Implemented Actions

Status: Partial

Code refs:
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/activity_booking/get_activity_portal_board.ts`
- `ifitwala_ed/docs/enrollment/activity_booking_architecture.md`

Test refs:
- `ifitwala_ed/api/test_activity_booking.py`

Implemented guardian actions:

1. Open Guardian Home and refresh the family snapshot.
2. Drill from the family view into a linked student's read-only detail surface.
3. Open the guardian portfolio surface.
4. Use `/guardian/activities` to submit bookings, confirm offered places, cancel permitted bookings, and review booking logistics through the activity booking workflow APIs.

## 3. Planned But Not Wired On `/hub/guardian`

Status: Planned

Code refs:
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`

Test refs:
- None

Rules:

1. Monitoring mode is not implemented on the current guardian portal.
2. Policy acknowledgement, document upload, payments, and direct guardian messaging are not implemented on the current guardian portal routes.
3. These actions must not be treated as canonical until they have a wired route, a named server workflow, and tests.
4. When one of these actions is added, this document and the product contract must be updated in the same change.

## 4. Explicitly Forbidden Actions

Status: Implemented

Code refs:
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/docs/enrollment/activity_booking_architecture.md`

Test refs:
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. Guardians must not edit grades, unpublished outcomes, staff notes, health records, or guardian-student relationships.
2. Guardians must not bypass booking capacity checks, overlap checks, publication gates, or audience scoping.
3. Guardians must not compare siblings academically through any portal action.
4. Requests for staff-owned changes must route to staff workflows, not mutate records directly.

## 5. Contract Matrix

Status: Partial

Code refs:
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPortfolioFeed.vue`

Test refs:
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_guardian_home.py`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | Guardian links plus activity booking lifecycle records | `students/doctype/guardian/*`, `students/doctype/student_guardian/*`, `students/doctype/guardian_student/*`, activity booking doctypes reached via `api/activity_booking.py` | `api/test_activity_booking.py` |
| Controller / workflow logic | Activity booking workflows and guardian snapshot reads | `api/activity_booking.py`, `api/guardian_home.py` | `api/test_activity_booking.py`, `api/test_guardian_home.py` |
| API endpoints | Activity booking workflow endpoints and `get_guardian_home_snapshot` | `api/activity_booking.py`, `api/guardian_home.py` | `api/test_activity_booking.py`, `api/test_guardian_home.py` |
| SPA / UI surfaces | Guardian Home, student drill-down, activities, portfolio | `ui-spa/src/pages/guardian/*` | None |
| Reports / dashboards / briefings | Guardian Home summary cards and activity board summaries | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianActivities.vue` | `api/test_activity_booking.py` |
| Scheduler / background jobs | None documented for guardian actions in this contract | None | None |
| Tests | Activity booking backend coverage and guardian snapshot backend coverage | `api/test_activity_booking.py`, `api/test_guardian_home.py` | Implemented |
