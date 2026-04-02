# Guardian Portal Product Contract (v0.3)

Status: Active
Audience: Humans, coding agents
Scope: `/hub/guardian` portal namespace
Last updated: 2026-03-26

This document is the canonical product contract for the guardian portal rooted at `/hub/guardian`.

## 1. Product Promise

Status: Partial

Code refs:
- `ifitwala_ed/hooks.py`
- `ifitwala_ed/api/users.py`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue`

Test refs:
- `ifitwala_ed/api/test_users.py`
- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. Guardians land in the SPA at `/hub/guardian`, not in Desk.
2. The default experience is family-first and parent-centric.
3. The portal answers three questions first: what is happening, what needs attention, and what needs preparation.
4. The portal is an awareness surface, not a live gradebook or a staff tool.
5. Any curriculum-aware expansion must stay a family briefing layer, not a second student LMS.
6. Curriculum visibility now includes `learning_highlights` on Guardian Home and a child-level learning brief on `/guardian/students/:student_id`.

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
4. Monitoring mode is family-wide, not child-by-child; guardians review logs and published results across all linked children with optional child filtering.
5. Sibling comparison and surveillance-style ranking views are out of scope.

## 3. Implemented `/hub/guardian/*` Surfaces

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelectionDetail.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianAttendance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianFinance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPortfolioFeed.vue`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_self_enrollment.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`
- `ifitwala_ed/ui-spa/src/lib/services/selfEnrollment/__tests__/selfEnrollmentService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCourseSelection.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts`

Surface matrix:

| Route | Surface | Status | Purpose |
| --- | --- | --- | --- |
| `/guardian` | Guardian Home | Implemented | Family snapshot with counts, quick links, and five briefing zones including learning highlights. |
| `/guardian/students/:student_id` | Guardian Student Shell | Implemented | Child-specific learning brief with course themes, upcoming experiences, and home-support prompts. |
| `/guardian/course-selection` | Guardian Course Selection | Implemented | Family-first academic self-enrollment board for linked children. |
| `/guardian/course-selection/:selection_window/:student_id` | Guardian Course Selection Detail | Implemented | Child-specific course-choice editor for one invited selection window. |
| `/guardian/activities` | Guardian Activities | Implemented | Family-first activity booking and management flow. |
| `/guardian/attendance` | Guardian Attendance | Implemented | Family-wide attendance heatmap and day-detail review with optional child filtering. |
| `/guardian/policies` | Guardian Policies | Implemented | Review active guardian policies and acknowledge missing policy versions. |
| `/guardian/finance` | Guardian Finance | Implemented | View family invoices and payment history for account holders the guardian is authorized to see. |
| `/guardian/monitoring` | Guardian Monitoring | Implemented | One family-wide monitoring view for guardian-visible logs and published results with child filters. |
| `/guardian/portfolio` | Guardian Portfolio | Partial | Showcase evidence view for guardian-visible portfolio content. |

## 4. Locked Non-Goals And Deferred Scope

Status: Partial

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/api/activity_booking.py`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. The guardian portal does not expose general draft or unpublished academic truth. The explicit exception is a guardian-scoped `Program Offering Selection Window`, where the guardian may edit only the linked child’s draft `Program Enrollment Request` for that invited window.
2. The guardian portal does not allow guardians to edit relationships, grades, staff notes, or health records.
3. Guardian finance visibility is limited to linked students' account holders that pass the portal finance authority rule; account-holder ownership is not inferred from display alone.
4. Uploads and direct guardian messaging remain outside the current `/hub/guardian` implementation.
5. Any new guardian-facing action must use a named workflow endpoint and server-owned permissions.
6. Family signatures, permission slips, and mutable consents are planned work and are governed by `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md` until implementation lands.

Planned curriculum-awareness expansion is tracked separately in:

- `ifitwala_ed/docs/curriculum/05_student_and_guardian_learning_experience_proposal.md`

## 5. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/students/doctype/guardian/guardian.json`
- `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
- `ifitwala_ed/students/doctype/guardian_student/guardian_student.json`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelectionDetail.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianAttendance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianFinance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPortfolioFeed.vue`

Test refs:
- `ifitwala_ed/api/test_users.py`
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_self_enrollment.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`
- `ifitwala_ed/ui-spa/src/lib/services/selfEnrollment/__tests__/selfEnrollmentService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCourseSelection.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | Guardian identity and guardian-student links, policy acknowledgements, account holders, invoices, payments | `students/doctype/guardian/*`, `students/doctype/student_guardian/*`, `students/doctype/guardian_student/*`, `governance/doctype/policy_acknowledgement/*`, `accounting/doctype/account_holder/*`, `accounting/doctype/sales_invoice/*`, `accounting/doctype/payment_entry/*` | `api/test_users.py`, `api/test_guardian_phase2.py` |
| Controller / workflow logic | Guardian home aggregation, guardian course selection, activity booking, guardian policy acknowledgement, family attendance visibility, family finance visibility, family monitoring reads | `api/guardian_home.py`, `api/self_enrollment.py`, `api/activity_booking.py`, `api/guardian_policy.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py` | `api/test_guardian_home.py`, `api/test_self_enrollment.py`, `api/test_activity_booking.py`, `api/test_guardian_phase2.py` |
| API endpoints | Guardian snapshot, guardian course-selection workflows, activity booking workflows, guardian policy overview/acknowledgement, guardian attendance snapshot, guardian finance snapshot, guardian monitoring snapshot | `api/guardian_home.py`, `api/self_enrollment.py`, `api/activity_booking.py`, `api/guardian_policy.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py` | `api/test_guardian_home.py`, `api/test_self_enrollment.py`, `api/test_activity_booking.py`, `api/test_guardian_phase2.py` |
| SPA / UI surfaces | Guardian Home, student drill-down, course selection, activities, attendance, policies, finance, monitoring, portfolio | `ui-spa/src/pages/guardian/*`, `ui-spa/src/router/index.ts` | `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`, `ui-spa/src/lib/services/selfEnrollment/__tests__/selfEnrollmentService.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianCourseSelection.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts` |
| Reports / dashboards / briefings | Guardian Home snapshot cards plus family attendance, finance, and monitoring summaries | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianAttendance.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue`, `api/guardian_home.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py` | `api/test_guardian_home.py`, `api/test_guardian_phase2.py` |
| Scheduler / background jobs | None in the current guardian portal contract | None | None |
| Tests | Redirect, snapshot payload, guardian service transport, activity booking, guardian policy/attendance/finance/monitoring regressions | `api/test_users.py`, `api/test_guardian_home.py`, `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`, `api/test_activity_booking.py`, `api/test_guardian_phase2.py`, `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts` | Implemented |
