# Guardian Portal Product Contract (v0.2)

Status: Active
Audience: Humans, coding agents
Scope: `/hub/guardian` portal namespace
Last updated: 2026-03-13

This document is the canonical product contract for the guardian portal rooted at `/hub/guardian`.

## 1. Product Promise

Status: Partial

Code refs:
- `ifitwala_ed/hooks.py`
- `ifitwala_ed/api/users.py`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`

Test refs:
- `ifitwala_ed/api/test_users.py`
- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. Guardians land in the SPA at `/hub/guardian`, not in Desk.
2. The default experience is family-first and parent-centric.
3. The portal answers three questions first: what is happening, what needs attention, and what needs preparation.
4. The portal is an awareness surface, not a live gradebook or a staff tool.

## 2. User Model And Interaction Model

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`

Rules:

1. Guardians start on a family snapshot and only drill down to a child when needed.
2. Child scope comes from linked students resolved on the server.
3. The portal uses plain language and must not surface schedule internals such as `rotation_day` or `block_number`.
4. Sibling comparison and surveillance-style performance views are out of scope.

## 3. Implemented `/hub/guardian/*` Surfaces

Status: Partial

Code refs:
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPortfolioFeed.vue`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`

Surface matrix:

| Route | Surface | Status | Purpose |
| --- | --- | --- | --- |
| `/guardian` | Guardian Home | Implemented | Family snapshot with counts, quick links, and four briefing zones. |
| `/guardian/students/:student_id` | Guardian Student Shell | Implemented | Child-specific read view derived from the same guardian snapshot payload. |
| `/guardian/activities` | Guardian Activities | Implemented | Family-first activity booking and management flow. |
| `/guardian/portfolio` | Guardian Portfolio | Partial | Showcase evidence view for guardian-visible portfolio content. |

## 4. Locked Non-Goals And Deferred Scope

Status: Partial

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/api/activity_booking.py`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`

Rules:

1. The guardian portal does not expose draft or unpublished academic truth.
2. The guardian portal does not allow guardians to edit relationships, grades, staff notes, or health records.
3. Monitoring mode, payments, uploads, and policy acknowledgement flows are not part of the current `/hub/guardian` implementation unless a dedicated route and server workflow are wired.
4. Any new guardian-facing action must use a named workflow endpoint and server-owned permissions.

## 5. Contract Matrix

Status: Partial

Code refs:
- `ifitwala_ed/students/doctype/guardian/guardian.json`
- `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
- `ifitwala_ed/students/doctype/guardian_student/guardian_student.json`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPortfolioFeed.vue`

Test refs:
- `ifitwala_ed/api/test_users.py`
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | Guardian identity and guardian-student links | `students/doctype/guardian/*`, `students/doctype/student_guardian/*`, `students/doctype/guardian_student/*` | `api/test_users.py` |
| Controller / workflow logic | Guardian home aggregation and guardian activity booking flows | `api/guardian_home.py`, `api/activity_booking.py` | `api/test_guardian_home.py`, `api/test_activity_booking.py` |
| API endpoints | `get_guardian_home_snapshot` plus activity booking workflow endpoints | `api/guardian_home.py`, `api/activity_booking.py` | `api/test_guardian_home.py`, `api/test_activity_booking.py` |
| SPA / UI surfaces | Guardian Home, student drill-down, activities, portfolio | `ui-spa/src/pages/guardian/*`, `ui-spa/src/router/index.ts` | `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts` |
| Reports / dashboards / briefings | Guardian Home snapshot cards and zone summaries | `ui-spa/src/pages/guardian/GuardianHome.vue`, `api/guardian_home.py` | `api/test_guardian_home.py` |
| Scheduler / background jobs | None in the current guardian portal contract | None | None |
| Tests | Redirect, snapshot payload, guardian service transport, activity booking | `api/test_users.py`, `api/test_guardian_home.py`, `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`, `api/test_activity_booking.py` | Implemented |
