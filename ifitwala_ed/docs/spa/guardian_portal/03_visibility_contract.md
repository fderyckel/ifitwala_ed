# Guardian Portal Visibility Contract (v0.3)

Status: Active
Audience: Humans, coding agents
Scope: Data visible through `/hub/guardian`
Last updated: 2026-03-15

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

## 3. Policy Visibility

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`
- `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Guardian policy rows are resolved from active `Institutional Policy` and active `Policy Version` records where `applies_to = Guardian`.
2. Policy scope is derived from the organizations and schools of the guardian's linked students.
3. Guardian acknowledgement state is limited to `Policy Acknowledgement` rows for `acknowledged_for = Guardian`, `context_doctype = Guardian`, and `context_name = Guardian.name`.
4. Guardians must not see staff, student, or applicant-only policy rows through `/hub/guardian/policies`.

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
5. The `mark_guardian_student_log_read` action may only mark logs that are both linked-child rows and `visible_to_guardians = 1`.
6. Monitoring must not expose unpublished task outcomes, staff-only logs, or non-linked children.

## 7. Explicit Prohibitions

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
4. Finance rows must not expose account holders outside the authority rule, even if the guardian can see the student.
5. Any new guardian-visible data class must add an explicit server gate and be documented here before release.

## 8. Contract Matrix

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/students/doctype/student_log/student_log.json`
- `ifitwala_ed/students/doctype/portal_read_receipt/portal_read_receipt.py`
- `ifitwala_ed/students/doctype/portal_read_receipt/portal_read_receipt.json`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`

Test refs:

- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_users.py`

| Concern                          | Canonical owner                                                                                                                                          | Code refs                                                                                                                                                                                                                                                                                                                                                                                      | Test refs                                                                                                                                                                                       |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Schema / DocType                 | Guardian links, policy acknowledgements, guardian-visible student logs, published outcomes, account holders, invoices, payments, portal read receipts    | `students/doctype/guardian/*`, `students/doctype/student_guardian/*`, `students/doctype/guardian_student/*`, `governance/doctype/policy_acknowledgement/*`, `students/doctype/student_log/*`, `assessment/doctype/task_outcome/*`, `accounting/doctype/account_holder/*`, `accounting/doctype/sales_invoice/*`, `accounting/doctype/payment_entry/*`, `students/doctype/portal_read_receipt/*` | `api/test_users.py`, `api/test_guardian_home.py`, `api/test_guardian_phase2.py`                                                                                                                 |
| Controller / workflow logic      | Guardian scope resolution, snapshot filtering, policy scope filtering, finance authority filtering, monitoring filtering, communication seen-state rules | `api/guardian_home.py`, `api/guardian_policy.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`, `api/org_communication_interactions.py`                                                                                                                                                                                                                                             | `api/test_guardian_home.py`, `api/test_guardian_phase2.py`, `api/test_org_communication_interactions.py`                                                                                        |
| API endpoints                    | Guardian snapshot, guardian policy, guardian finance, guardian monitoring, guardian log seen-state, and org communication interaction workflows          | `api/guardian_home.py`, `api/guardian_policy.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`, `api/org_communication_interactions.py`                                                                                                                                                                                                                                             | `api/test_guardian_home.py`, `api/test_guardian_phase2.py`, `api/test_org_communication_interactions.py`                                                                                        |
| SPA / UI surfaces                | Guardian Home, child drill-down, policies, finance, and monitoring consume filtered payload only                                                         | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue`, `ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue`                                                                                                                                      | `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts` |
| Reports / dashboards / briefings | Guardian Home, family finance cards, and monitoring counts                                                                                               | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue`, `api/guardian_home.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`                                                                                                                                                             | `api/test_guardian_home.py`, `api/test_guardian_phase2.py`                                                                                                                                      |
| Scheduler / background jobs      | None in the guardian portal visibility contract                                                                                                          | None                                                                                                                                                                                                                                                                                                                                                                                           | None                                                                                                                                                                                            |
| Tests                            | Redirect, guardian snapshot visibility, guardian Phase-2 visibility, communication seen-state                                                            | `api/test_users.py`, `api/test_guardian_home.py`, `api/test_guardian_phase2.py`, `api/test_org_communication_interactions.py`                                                                                                                                                                                                                                                                  | Implemented                                                                                                                                                                                     |
