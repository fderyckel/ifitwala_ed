# Guardian Home Information Contract (v0.4)

Status: Active
Audience: Humans, coding agents
Scope: `/hub/guardian` family information surfaces
Last updated: 2026-04-23

This document defines the canonical information contract for Guardian Home plus the Phase-2 guardian policy, finance, and monitoring surfaces.

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

## 2. Family Snapshot Surface

Status: Implemented

Code refs:

- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`
- `ifitwala_ed/ui-spa/src/router/index.ts`

Test refs:

- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`

Rules:

1. Guardian Home shows the portal heading, the configured school-day window, and a refresh action.
2. The summary cards show `unread_communications`, `unread_visible_student_logs`, `upcoming_due_tasks`, and `upcoming_assessments`; the `Unread student logs` card routes to `/guardian/monitoring?focus=unread`, and when `upcoming_assessments` is non-zero that card may jump the guardian to the first in-window timeline day that carries assessment detail.
3. Quick links route guardians to communications, course selection, activities, attendance, policies, finance, monitoring, portfolio, and the family snapshot, and launch the `School Calendar` monthly overlay from Guardian Home.
4. The guardian portal shell may surface an unread communication badge on the `Communications` rail item using the same unread org-communication count shown by the family snapshot.
5. The landing page remains a briefing surface; navigation is secondary.

## 3. Home Zone Order And Content

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`

Test refs:

- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`

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
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

Rules:

1. `/guardian/students/:student_id` reuses the same guardian snapshot instead of creating a second student-only backend contract.
2. The drill-down surface filters timeline, attention, preparation, and recent activity to one linked student.
3. If the student is outside guardian scope, the page must render an explicit blocked state.
4. Child drill-down is subordinate to Guardian Home and must not redefine data visibility rules.

## 5. Policy Surface

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_policy_overview.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/acknowledge_guardian_policy.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`

Rules:

1. `/guardian/policies` consumes one canonical payload: `get_guardian_policy_overview`.
2. Policy rows are scoped by the guardian's signer-authorized linked students and include current acknowledgement state for the logged-in guardian only.
3. Guardian policy rows are eligible only when `Institutional Policy.applies_to` includes `Guardian`.
4. Acknowledge actions call one named endpoint: `acknowledge_guardian_policy`.
5. Repeated acknowledgement clicks must be idempotent; already-acknowledged policy versions return a stable success result instead of creating duplicates.

## 6. Finance Surface

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_finance_snapshot.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianFinance.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`

Rules:

1. `/guardian/finance` consumes one canonical payload: `get_guardian_finance_snapshot`.
2. The finance snapshot is read-only in Phase 2 and shows authorized account holders, submitted invoices, and submitted payment history.
3. Invoice rows may aggregate charges for multiple linked children and must expose the linked-child labels returned by the server.
4. If the guardian does not pass the finance authority rule for any linked account holder, the page renders an explicit access-limited empty state.

## 7. Monitoring Surface

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_monitoring_snapshot.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts`

Rules:

1. `/guardian/monitoring` is a family-wide monitoring surface, not one portal view per child.
2. The page shows guardian-visible student logs and published task results for all linked children by default.
3. Guardian-visible student logs render the full plain-text note body returned by the server; the guardian portal must not truncate those log notes into teaser text on this surface.
4. Child filtering is optional and does not change server visibility; it only narrows the already-authorized payload.
5. Guardian-visible student logs expose an explicit mark-read action through `mark_guardian_student_log_read`, which writes `Portal Read Receipt` for the logged-in guardian only.
6. When the route query includes `focus=unread`, the SPA scrolls the first unread guardian-visible student log into view after the payload loads; if no unread log exists, the page focuses the student-log section itself.
7. Monitoring mode must not introduce sibling ranking, gradebook editing, or unpublished results.

## 8. Communication Center Surface

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_communication_center.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/guardianCommunicationService.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/__tests__/guardianCommunicationService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`

Rules:

1. `/guardian/communications` consumes one canonical payload: `get_guardian_communication_center`.
2. The page is family-first and shows guardian-visible org communications and school events for all linked children by default, with an optional child filter that narrows the already-authorized payload.
3. Feed rows render once per domain record and expose the linked-child labels matched by the server.
4. Org communication rows keep their shared interaction, detail, and read-state behavior.
5. School-event rows are visibility-only items in this surface and open the event detail modal from the bootstrap payload instead of using the org communication interaction workflow.
6. Opening an org communication detail must call `mark_org_communication_read` so the unread state stays aligned with Guardian Home and the guardian shell badge.

## 9. Attendance Surface

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_attendance_snapshot.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianAttendance.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`

Rules:

1. `/guardian/attendance` consumes one canonical payload: `get_guardian_attendance_snapshot`.
2. The page is family-first and shows all linked children by default, with an optional child filter that narrows the already-authorized payload.
3. Attendance cells summarize each recorded day as `present`, `late`, or `absence`, and clicking a day reveals plain-language details for that day only.
4. Attendance detail may expose time, attendance code, course, location, and remark, but it must not expose `rotation_day` or `block_number`.

## 10. School Calendar Overlay

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCalendar/guardianCalendarService.ts`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCalendar/__tests__/guardianCalendarService.test.ts`
- `ifitwala_ed/ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`

Rules:

1. The `School Calendar` quick link on Guardian Home opens one canonical payload: `get_guardian_calendar_overlay`.
2. The overlay payload is month-scoped and includes the family child list, filter options, summary counts, and one merged `items` collection of `holiday` and `school_event` rows.
3. The overlay is read-only and stays family-first by default, with optional child and school filters plus `Show holidays` and `Show school events` toggles.
4. Item rows expose matched child labels from the server and may expose one `open_target` only for school-event detail.
5. Calendar item pills are direct interaction targets: school-event pills may open the existing school-event detail overlay, while holidays and mixed-day review stay inside the inline day-detail sheet below the month grid.

## 11. Explicit Exclusions

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`

Test refs:

- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_guardian_calendar.py`

Rules:

1. Guardian Home must not expose `rotation_day` or `block_number` anywhere in the payload or UI.
2. Guardian surfaces must not expose live gradebook rows, staff-only notes, or sibling comparison data.
3. Guardian finance does not create or submit payments in Phase 2; it remains a read-only visibility surface.
4. School-event rows inside `/guardian/communications` do not create guardian unread/read-state.
5. The calendar overlay does not expose class timetables, meetings, attendance, or assignment dates in v1.
6. Any new information block on `/hub/guardian` must be added to this document before it is treated as canonical.

## 12. Contract Matrix

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_calendar.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/guardianHomeService.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_communication_center.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/guardianCommunicationService.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_calendar_overlay.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCalendar/guardianCalendarService.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_policy_overview.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/acknowledge_guardian_policy.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_attendance_snapshot.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_finance_snapshot.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_monitoring_snapshot.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianAttendance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianFinance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/api/test_guardian_calendar.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/__tests__/guardianCommunicationService.test.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCalendar/__tests__/guardianCalendarService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts`
- `ifitwala_ed/ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts`

| Concern                          | Canonical owner                                                                                                                                                                                    | Code refs                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Test refs                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Schema / DocType                 | Guardian surfaces read guardian links, school calendars and holidays, school events, student logs, attendance, outcomes, communications, policy acknowledgements, account holders, invoices, payments, and portal read receipts | `api/guardian_home.py`, `school_settings/doctype/school_calendar/*`, `school_settings/doctype/school_calendar_holidays/*`, `school_settings/doctype/school_event/*`, `school_settings/doctype/school_event_audience/*`, `school_settings/doctype/school_event_participant/*`, `governance/doctype/policy_acknowledgement/*`, `accounting/doctype/account_holder/*`, `accounting/doctype/sales_invoice/*`, `accounting/doctype/payment_entry/*`, `students/doctype/student_log/*`, `students/doctype/student_attendance/*`, `school_settings/doctype/student_attendance_code/*`, `students/doctype/portal_read_receipt/*`, `assessment/doctype/task_outcome/*` | `api/test_guardian_home.py`, `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py`                                                                                                                                                                                                                                                                                                                   |
| Controller / workflow logic      | Snapshot builder, drill-down filtering, guardian calendar overlay bootstrap, communication-center bootstrap, policy acknowledgement flow, attendance visibility assembly, finance visibility assembly, monitoring aggregation and read-state | `api/guardian_home.py`, `api/guardian_calendar.py`, `api/guardian_communications.py`, `api/guardian_policy.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue`                                                                                                                                                                                                              | `api/test_guardian_home.py`, `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py`                                                                                                                                                                                                                                                                                                                   |
| API endpoints                    | `get_guardian_home_snapshot`, `get_guardian_student_learning_brief`, `get_guardian_calendar_overlay`, `get_guardian_communication_center`, `get_guardian_policy_overview`, `acknowledge_guardian_policy`, `get_guardian_attendance_snapshot`, `get_guardian_finance_snapshot`, `get_guardian_monitoring_snapshot`, `mark_guardian_student_log_read` | `api/guardian_home.py`, `api/guardian_calendar.py`, `api/guardian_communications.py`, `api/guardian_policy.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`                                                                                                                                                                                          | `api/test_guardian_home.py`, `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py`                                                                                                                                                                                                                                                                                                                   |
| SPA / UI surfaces                | Guardian Home, Guardian Calendar Overlay, Guardian Communication Center, Guardian Student Shell, Guardian Policies, Guardian Attendance, Guardian Finance, Guardian Monitoring                      | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`, `ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue`, `ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ui-spa/src/pages/guardian/GuardianAttendance.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue`                                          | `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`, `ui-spa/src/lib/services/guardianCommunication/__tests__/guardianCommunicationService.test.ts`, `ui-spa/src/lib/services/guardianCalendar/__tests__/guardianCalendarService.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts`, `ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts` |
| Reports / dashboards / briefings | Home summary cards, the home-launched calendar month view, communication and school-event summary cards, learning highlights, child learning briefs, attendance summary cards, finance summary cards, and monitoring summary cards | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/overlays/guardian/GuardianCalendarOverlay.vue`, `ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue`, `ui-spa/src/pages/guardian/GuardianAttendance.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue`                                                                                  | `api/test_guardian_home.py`, `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py`                                                                                                                                                                                                                                                                                                                   |
| Scheduler / background jobs      | None                                                                                                                                                                                               | None                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | None                                                                                                                                                                                                                                                                                                                                                                                                          |
| Tests                            | Endpoint unit coverage, service transport coverage, overlay regression coverage, and guardian Phase-2 page regression coverage                                                                   | `api/test_guardian_home.py`, `api/test_guardian_calendar.py`, `api/test_guardian_phase2.py`, `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`, `ui-spa/src/lib/services/guardianCalendar/__tests__/guardianCalendarService.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts`, `ui-spa/src/overlays/guardian/__tests__/GuardianCalendarOverlay.test.ts` | Implemented                                                                                                                                                                                                                                                                          |
