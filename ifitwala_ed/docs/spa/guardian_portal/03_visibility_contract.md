# Guardian Portal Visibility Contract (v0.2)

Status: Active
Audience: Humans, coding agents
Scope: Data visible through `/hub/guardian`
Last updated: 2026-03-13

This document defines the current server-enforced visibility rules for the guardian portal.

## 1. Guardian Scope Resolution

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/students/doctype/guardian/guardian.json`
- `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
- `ifitwala_ed/students/doctype/guardian_student/guardian_student.json`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_users.py`

Rules:

1. The current user must resolve to a `Guardian` record through `Guardian.user`.
2. Student scope is derived from `Student Guardian.parent` and `Guardian Student.student`.
3. The snapshot includes only linked students that are currently `Student.enabled = 1`.
4. If no guardian record exists, the endpoint must fail with a permission error instead of returning guessed data.

## 2. Visible Data Classes

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/docs/docs_md/task-delivery.md`
- `ifitwala_ed/docs/docs_md/task-outcome.md`
- `ifitwala_ed/students/doctype/student_log/student_log.json`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. Timeline and preparation rows are limited to linked students and their current schedule or delivery context.
2. Student log rows appear only when `Student Log.visible_to_guardians = 1`.
3. Recent task-result rows appear only when `Task Outcome.is_published = 1`.
4. Attendance rows on Guardian Home are exception-focused and limited to linked students.

## 3. Communication And Read-State

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/docs/spa/07_org_communication_messaging_contract.md`
- `ifitwala_ed/students/doctype/portal_read_receipt/portal_read_receipt.py`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_org_communication_interactions.py`

Rules:

1. Guardian-visible communications are audience-scoped on the server before they reach the snapshot payload.
2. Unread state is derived from `Portal Read Receipt`.
3. A guardian's own communication interaction rows also count as seen for summary logic.
4. Hidden communications must not contribute to unread counts, attention rows, or recent activity.

## 4. Explicit Prohibitions

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. The guardian portal must not expose `rotation_day`, `block_number`, or other internal schedule keys.
2. The guardian portal must not expose draft grading, unpublished outcomes, staff-only student logs, or cross-family data.
3. Frontend hiding is not a visibility control; all filtering happens before the payload reaches the SPA.
4. Any new guardian-visible data class must add an explicit server gate and be documented here before release.

## 5. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/students/doctype/student_log/student_log.json`
- `ifitwala_ed/students/doctype/portal_read_receipt/portal_read_receipt.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_users.py`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | Guardian links, guardian-visible student logs, portal read receipts, published outcomes | `students/doctype/guardian/*`, `students/doctype/student_guardian/*`, `students/doctype/guardian_student/*`, `students/doctype/student_log/*`, `students/doctype/portal_read_receipt/*` | `api/test_users.py`, `api/test_guardian_home.py` |
| Controller / workflow logic | Guardian scope resolution, snapshot filtering, communication seen-state rules | `api/guardian_home.py`, `api/org_communication_interactions.py` | `api/test_guardian_home.py`, `api/test_org_communication_interactions.py` |
| API endpoints | Guardian snapshot and org communication interaction workflows | `api/guardian_home.py`, `api/org_communication_interactions.py` | `api/test_guardian_home.py`, `api/test_org_communication_interactions.py` |
| SPA / UI surfaces | Guardian Home and child drill-down consume filtered payload only | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue` | None |
| Reports / dashboards / briefings | Guardian Home counts and zone summaries | `ui-spa/src/pages/guardian/GuardianHome.vue`, `api/guardian_home.py` | `api/test_guardian_home.py` |
| Scheduler / background jobs | None in the guardian portal visibility contract | None | None |
| Tests | Redirect, snapshot visibility, communication seen-state | `api/test_users.py`, `api/test_guardian_home.py`, `api/test_org_communication_interactions.py` | Implemented |
