# Guardian Home Information Contract (v0.2)

Status: Active
Audience: Humans, coding agents
Scope: `/hub/guardian` landing surface
Last updated: 2026-03-13

This document defines the canonical information contract for Guardian Home and its child drill-down surface.

## 1. Snapshot Payload Owner

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/guardianHomeService.ts`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`

Rules:

1. Guardian Home consumes one canonical payload: `get_guardian_home_snapshot`.
2. The request contract is `anchor_date?`, `school_days?`, and `debug?`.
3. The response contract is the `Response` type in `ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`.
4. The SPA service calls the endpoint with a flat JSON body and returns the domain payload directly.

## 2. Header, Counts, And Quick Links

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`
- `ifitwala_ed/ui-spa/src/router/index.ts`

Test refs:
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`
- Page-level tests: None

Rules:

1. Guardian Home shows the portal heading, the configured school-day window, and a refresh action.
2. The summary cards show `unread_communications`, `unread_visible_student_logs`, `upcoming_due_tasks`, and `upcoming_assessments`.
3. Quick links route guardians to activities, the family snapshot, the guardian portfolio, and the update-focused home view.
4. The landing page remains a briefing surface; navigation is secondary.

## 3. Home Zone Order And Content

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- Page-level tests: None

Rules:

1. Guardian Home renders four zones in this order: `family_timeline`, `attention_needed`, `preparation_and_support`, `recent_activity`.
2. `family_timeline` is grouped by day and contains one child row per linked student present in that day window.
3. `attention_needed` is exception-oriented and mixes attendance, guardian-visible student logs, and guardian-visible communications.
4. `preparation_and_support` is forward-looking and remains low-noise.
5. `recent_activity` is a calm feed of published task results, guardian-visible student logs, and communications.

## 4. Student Drill-Down

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`

Test refs:
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`
- Page-level tests: None

Rules:

1. `/guardian/students/:student_id` reuses the same guardian snapshot instead of creating a second student-only backend contract.
2. The drill-down surface filters timeline, attention, preparation, and recent activity to one linked student.
3. If the student is outside guardian scope, the page must render an explicit blocked state.
4. Child drill-down is subordinate to Guardian Home and must not redefine data visibility rules.

## 5. Explicit Exclusions

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. Guardian Home must not expose `rotation_day` or `block_number` anywhere in the payload or UI.
2. Guardian Home must not expose live gradebook rows, staff-only notes, or sibling comparison data.
3. Guardian Home must not depend on more than the snapshot contract plus router navigation.
4. Any new information block on `/hub/guardian` must be added to this document before it is treated as canonical.

## 6. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/guardianHomeService.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`
- Page-level tests: None

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | Guardian snapshot reads guardian links, student logs, attendance, outcomes, communications, and read receipts | `api/guardian_home.py`, `students/doctype/student_log/*`, `students/doctype/portal_read_receipt/*` | `api/test_guardian_home.py` |
| Controller / workflow logic | Snapshot builder and drill-down filtering | `api/guardian_home.py`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue` | `api/test_guardian_home.py` |
| API endpoints | `get_guardian_home_snapshot` | `api/guardian_home.py` | `api/test_guardian_home.py` |
| SPA / UI surfaces | Guardian Home and Guardian Student Shell | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue` | `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts` |
| Reports / dashboards / briefings | Home summary cards and four-zone layout | `ui-spa/src/pages/guardian/GuardianHome.vue` | None |
| Scheduler / background jobs | None | None | None |
| Tests | Endpoint unit coverage and service transport coverage | `api/test_guardian_home.py`, `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts` | Implemented |
