# Guardian Portal Actions Contract (v0.4)

Status: Active
Audience: Humans, coding agents
Scope: Guardian-initiated actions inside `/hub/guardian`
Last updated: 2026-04-23

This document defines what guardians can currently do through the guardian portal and what remains planned.

## 1. Action Model

Status: Implemented

Code refs:
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`

Test refs:
- `ifitwala_ed/api/test_self_enrollment.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. Guardian actions are named workflow actions, not generic CRUD assembled on the client.
2. Visibility and action authority are separate concerns; seeing a row does not imply edit rights.
3. Every guardian mutation must be server-enforced and context-bound to linked students.
4. The current `/hub/guardian` implementation is read-mostly outside the activity booking flow.

## 2. Implemented Actions

Status: Implemented

Code refs:
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelectionDetail.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianAttendance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianFinance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/activity_booking/get_activity_portal_board.ts`
- `ifitwala_ed/docs/enrollment/06_activity_booking_architecture.md`

Test refs:
- `ifitwala_ed/api/test_self_enrollment.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`
- `ifitwala_ed/ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`

Implemented guardian actions:

1. Open Guardian Home and refresh the family snapshot.
2. Drill from the family view into a linked student's read-only detail surface.
3. Open the guardian portfolio surface.
4. Use `/guardian/course-selection` to review each linked child’s invited academic selection window, save draft choices, and submit the linked `Program Enrollment Request`.
   Submission stays in `Draft` until the current choices pass live validation; the portal must explain what needs attention before the guardian can submit.
   Save Draft is optional. Submit must use the guardian's latest unsaved selections for that screen and either complete the submission or return a plain-language validation message.
   When a guardian selects a course inside a choice section, the portal should prefill that section as the counted section and show a plain-language preference-rank hint with a default rank so the guardian usually does not need to type a number manually.
5. Use `/guardian/activities` to submit bookings, confirm offered places, cancel permitted bookings, and review booking logistics through the activity booking workflow APIs.
6. Use `/guardian/policies` to acknowledge missing guardian policy versions through a named acknowledgement endpoint.
7. Use `/guardian/attendance` to review family-wide attendance by day and open plain-language day details for a selected child/date.
8. Use `/guardian/finance` to review authorized invoices and payment history for the family.
9. Use `/guardian/monitoring` to review family-wide guardian-visible logs in full plain text and published results with optional child filtering, land on the first unread log when Guardian Home hands off with unread focus, then mark visible logs as seen.
10. Use `/guardian/communications` to review family-wide org communications and school events, optionally narrow to one linked child, open full messages, open event details, mark org communications as seen, and, when the communication mode allows it, react or comment through the shared named interaction workflows.
11. Use the `School Calendar` quick link on Guardian Home to open a large monthly overlay, move between months, filter by linked child or family school, include or exclude holidays and school events, open inline day details for one selected date, and open school-event detail directly from a calendar event item when it exposes it.

## 3. Planned But Not Wired On `/hub/guardian`

Status: Partial

Code refs:
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`

Test refs:
- None

Rules:

1. Document upload and direct guardian messaging are not implemented on the current guardian portal routes.
2. Guardian finance remains read-only in Phase 2; submitting payments or creating payment requests from the portal is not yet wired.
3. These actions must not be treated as canonical until they have a wired route, a named server workflow, and tests.
4. When one of these actions is added, this document and the product contract must be updated in the same change.

## 4. Explicitly Forbidden Actions

Status: Implemented

Code refs:
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/docs/enrollment/06_activity_booking_architecture.md`

Test refs:
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. Guardians must not edit grades, unpublished outcomes, staff notes, health records, guardian-student relationships, or draft academic requests outside an invited selection window.
2. Guardians must not bypass booking capacity checks, overlap checks, publication gates, or audience scoping.
3. Guardians must not compare siblings academically through any portal action or ranking surface.
4. Guardians must not create financial visibility over account holders that fail the Phase-2 authority rule.
5. Requests for staff-owned changes must route to staff workflows, not mutate records directly.

## 5. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelectionDetail.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianAttendance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianFinance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPortfolioFeed.vue`

Test refs:
- `ifitwala_ed/api/test_self_enrollment.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCourseSelection.test.ts`
- `ifitwala_ed/ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | Guardian links, guardian-visible school events, selection-window rows, activity booking lifecycle records, policy acknowledgements, account holders, invoices, and payments | `students/doctype/guardian/*`, `students/doctype/student_guardian/*`, `students/doctype/guardian_student/*`, `school_settings/doctype/school_event/*`, `school_settings/doctype/school_event_audience/*`, `school_settings/doctype/school_event_participant/*`, `schedule/doctype/program_offering_selection_window/*`, `schedule/doctype/program_enrollment_request/*`, `governance/doctype/policy_acknowledgement/*`, `accounting/doctype/account_holder/*`, `accounting/doctype/sales_invoice/*`, `accounting/doctype/payment_entry/*`, activity booking doctypes reached via `api/activity_booking.py` | `api/test_self_enrollment.py`, `api/test_activity_booking.py`, `api/test_guardian_phase2.py` |
| Controller / workflow logic | Guardian course-selection workflows, activity booking workflows, guardian snapshot reads, guardian calendar overlay reads, guardian communication-center reads, guardian policy acknowledgement, guardian attendance visibility, guardian finance visibility, guardian monitoring reads and mark-read actions | `api/self_enrollment.py`, `api/activity_booking.py`, `api/guardian_home.py`, `api/guardian_calendar.py`, `api/guardian_communications.py`, `api/guardian_policy.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py` | `api/test_self_enrollment.py`, `api/test_activity_booking.py`, `api/test_guardian_home.py`, `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py` |
| API endpoints | Guardian course-selection workflow endpoints plus activity booking, guardian snapshot, guardian calendar overlay, guardian communication-center, policy, attendance, finance, and monitoring endpoints | `api/self_enrollment.py`, `api/activity_booking.py`, `api/guardian_home.py`, `api/guardian_calendar.py`, `api/guardian_communications.py`, `api/guardian_policy.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py` | `api/test_self_enrollment.py`, `api/test_activity_booking.py`, `api/test_guardian_home.py`, `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py` |
| SPA / UI surfaces | Guardian Home, Guardian Calendar Overlay, Guardian Communication Center, student drill-down, course selection, activities, attendance, policies, finance, monitoring, portfolio | `ui-spa/src/pages/guardian/*`, `ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue` | `ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianCourseSelection.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts` |
| Reports / dashboards / briefings | Guardian Home summary cards, the home-launched school-calendar month view, communication-center communication and event summaries, course-selection board summaries, activity board summaries, attendance summary cards, finance summary cards, monitoring summary cards | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`, `ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`, `ui-spa/src/pages/guardian/GuardianCourseSelection.vue`, `ui-spa/src/pages/guardian/GuardianActivities.vue`, `ui-spa/src/pages/guardian/GuardianAttendance.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue` | `api/test_self_enrollment.py`, `api/test_activity_booking.py`, `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py` |
| Scheduler / background jobs | None documented for guardian actions in this contract | None | None |
| Tests | Guardian course-selection backend coverage, activity booking backend coverage, guardian snapshot backend coverage, and guardian Phase-2 regression coverage | `api/test_self_enrollment.py`, `api/test_activity_booking.py`, `api/test_guardian_home.py`, `api/test_guardian_phase2.py` | Implemented |
