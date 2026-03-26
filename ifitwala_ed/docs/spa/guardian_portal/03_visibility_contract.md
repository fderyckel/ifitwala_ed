# Guardian Portal Visibility Contract (v0.3)

Status: Active
Audience: Humans, coding agents
Scope: Data visible through `/hub/guardian`
Last updated: 2026-03-26

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
5. The family attendance surface may read only linked-student rows from `Student Attendance`, `Student Attendance Code`, and `Course`.

## 3. Policy Visibility

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`
- `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Guardian policy rows are resolved from active `Institutional Policy` and active `Policy Version` records where `applies_to` includes `Guardian`.
2. Policy scope is derived from the organizations and schools of the guardian's signer-authorized linked students.
3. Guardian acknowledgement state is limited to `Policy Acknowledgement` rows for `acknowledged_for = Guardian`, `context_doctype = Guardian`, and `context_name = Guardian.name`.
4. Guardians must not see policy rows for children where the guardian lacks signer authority, or rows whose audience is staff-only, student-only, or applicant-only.

## 4. Finance Visibility

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/students/doctype/guardian/guardian.json`
- `ifitwala_ed/students/doctype/student/student.json`
- `ifitwala_ed/accounting/doctype/account_holder/account_holder.json`
- `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.json`
- `ifitwala_ed/accounting/doctype/payment_entry/payment_entry.json`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Finance scope starts from linked students and their `Student.account_holder` values; the portal never guesses unrelated account holders.
2. A guardian may see a linked student's account holder only when either `Guardian.is_financial_guardian = 1` or `Account Holder.primary_email` matches `Guardian.guardian_email` or the logged-in user.
3. Finance payloads include only submitted invoices and submitted payment entries for authorized account holders.
4. If no linked account holder passes the authority rule, the finance payload returns an explicit access-limited empty state instead of cross-family data.

## 5. Communication And Read-State

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

## 6. Monitoring Visibility

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/students/doctype/student_log/student_log.json`
- `ifitwala_ed/students/doctype/portal_read_receipt/portal_read_receipt.json`
- `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Monitoring rows are limited to guardian-visible student logs and published task outcomes for linked students only.
2. The optional child filter may only target a linked student; any out-of-scope filter must fail with a permission error.
3. Monitoring uses the same guardian scope resolution as the rest of `/hub/guardian`.
4. Guardian-visible student logs derive unread/seen state from `Portal Read Receipt`, scoped to the logged-in guardian user.
5. `mark_guardian_student_log_read` may only write a read receipt for a linked student's guardian-visible log and for the current guardian user.
6. Monitoring must not expose unpublished task outcomes, staff-only logs, or non-linked children.

## 7. Attendance Visibility

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/students/doctype/student_attendance/student_attendance.json`
- `ifitwala_ed/school_settings/doctype/student_attendance_code/student_attendance_code.json`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Attendance rows are limited to linked students only, and the optional child filter may only target a linked student.
2. Day-state color and labels are derived from `Student Attendance Code.count_as_present` plus the code label, not from ad-hoc client logic.
3. Attendance detail may expose time, attendance code, course, location, and remark for linked students only.
4. Attendance detail must not expose `rotation_day`, `block_number`, unpublished academic outcomes, or non-linked student data.
5. Days with no attendance rows must remain unfilled; the server must not invent inferred attendance for missing dates.

## 8. Course Selection Visibility

Status: Implemented

Code refs:

- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.json`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`

Test refs:

- `ifitwala_ed/api/test_self_enrollment.py`

Rules:

1. Guardian course-selection payloads are limited to linked students only and to windows whose `audience = Guardian`.
2. Guardians may see only the `Program Enrollment Request` linked to the matching `Program Offering Selection Window Student` row for that linked child.
3. Guardians may edit draft request rows only while the selection window is open and the linked request is still `Draft`.
4. Course rows shown in the guardian selection editor must come from the authoritative `Program Offering` semantics; the portal must not invent or expose off-offering choices.
5. The course-selection exception does not authorize visibility into unrelated draft academic records, staff review notes, or other children outside guardian scope.

## 9. Explicit Prohibitions

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. The guardian portal must not expose `rotation_day`, `block_number`, or other internal schedule keys.
2. The guardian portal must not expose draft grading, unpublished outcomes, staff-only student logs, unrelated draft academic records, or cross-family data.
3. Frontend hiding is not a visibility control; all filtering happens before the payload reaches the SPA.
4. Finance rows must not expose account holders outside the authority rule, even if the guardian can see the student.
5. Any new guardian-visible data class must add an explicit server gate and be documented here before release.

## 10. Contract Matrix

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/students/doctype/student_log/student_log.json`
- `ifitwala_ed/students/doctype/student_attendance/student_attendance.json`
- `ifitwala_ed/school_settings/doctype/student_attendance_code/student_attendance_code.json`
- `ifitwala_ed/students/doctype/portal_read_receipt/portal_read_receipt.py`
- `ifitwala_ed/students/doctype/portal_read_receipt/portal_read_receipt.json`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`

Test refs:

- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/api/test_self_enrollment.py`
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_users.py`

| Concern                          | Canonical owner                                                                                                                                          | Code refs                                                                                                                                                                                                                                                                                                                                                                                      | Test refs                                                                                                                                                                                       |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Schema / DocType                 | Guardian links, policy acknowledgements, guardian-visible student logs, attendance, published outcomes, account holders, invoices, payments, portal read receipts | `students/doctype/guardian/*`, `students/doctype/student_guardian/*`, `students/doctype/guardian_student/*`, `governance/doctype/policy_acknowledgement/*`, `students/doctype/student_log/*`, `students/doctype/student_attendance/*`, `school_settings/doctype/student_attendance_code/*`, `assessment/doctype/task_outcome/*`, `accounting/doctype/account_holder/*`, `accounting/doctype/sales_invoice/*`, `accounting/doctype/payment_entry/*`, `students/doctype/portal_read_receipt/*` | `api/test_users.py`, `api/test_guardian_home.py`, `api/test_guardian_phase2.py`                                                                                                                 |
| Controller / workflow logic      | Guardian scope resolution, snapshot filtering, course-selection filtering, policy scope filtering, attendance visibility filtering, finance authority filtering, monitoring filtering, communication seen-state rules | `api/guardian_home.py`, `api/self_enrollment.py`, `api/guardian_policy.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`, `api/org_communication_interactions.py`                                                                                                                                                                                      | `api/test_guardian_home.py`, `api/test_self_enrollment.py`, `api/test_guardian_phase2.py`, `api/test_org_communication_interactions.py`                                                                 |
| API endpoints                    | Guardian snapshot, guardian course selection, guardian policy, guardian attendance, guardian finance, guardian monitoring, and org communication interaction workflows             | `api/guardian_home.py`, `api/self_enrollment.py`, `api/guardian_policy.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`, `api/org_communication_interactions.py`                                                                                                                                                                                      | `api/test_guardian_home.py`, `api/test_self_enrollment.py`, `api/test_guardian_phase2.py`, `api/test_org_communication_interactions.py`                                                                 |
| SPA / UI surfaces                | Guardian Home, child drill-down, course selection, policies, attendance, finance, and monitoring consume filtered payload only                                            | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue`, `ui-spa/src/pages/guardian/GuardianCourseSelection.vue`, `ui-spa/src/pages/guardian/GuardianCourseSelectionDetail.vue`, `ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ui-spa/src/pages/guardian/GuardianAttendance.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue`                                                                                 | `ui-spa/src/pages/guardian/__tests__/GuardianCourseSelection.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts` |
| Reports / dashboards / briefings | Guardian Home, family attendance cards, family finance cards, and monitoring counts                                                                      | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianAttendance.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue`, `api/guardian_home.py`, `api/guardian_attendance.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`                                                                                                                                                 | `api/test_guardian_home.py`, `api/test_guardian_phase2.py`                                                                                                                                      |
| Scheduler / background jobs      | None in the guardian portal visibility contract                                                                                                          | None                                                                                                                                                                                                                                                                                                                                                                                           | None                                                                                                                                                                                            |
| Tests                            | Redirect, guardian snapshot visibility, guardian Phase-2 visibility, communication seen-state                                                            | `api/test_users.py`, `api/test_guardian_home.py`, `api/test_guardian_phase2.py`, `api/test_org_communication_interactions.py`                                                                                                                                                                                                                                                                  | Implemented                                                                                                                                                                                     |
