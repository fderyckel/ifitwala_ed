# Guardian Home Information Contract (v0.3)

Status: Active
Audience: Humans, coding agents
Scope: `/hub/guardian` family information surfaces
Last updated: 2026-03-15

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
2. The summary cards show `unread_communications`, `unread_visible_student_logs`, `upcoming_due_tasks`, and `upcoming_assessments`.
3. Quick links route guardians to activities, policies, finance, monitoring, portfolio, and the family snapshot.
4. The landing page remains a briefing surface; navigation is secondary.

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
2. Policy rows are family-scoped by the guardian's linked students and include current acknowledgement state for the logged-in guardian only.
3. Acknowledge actions call one named endpoint: `acknowledge_guardian_policy`.
4. Repeated acknowledgement clicks must be idempotent; already-acknowledged policy versions return a stable success result instead of creating duplicates.

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
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/mark_guardian_student_log_read.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts`

Rules:

1. `/guardian/monitoring` is a family-wide monitoring surface, not one portal view per child.
2. The page shows guardian-visible student logs and published task results for all linked children by default.
3. Child filtering is optional and does not change server visibility; it only narrows the already-authorized payload.
4. Guardian-visible student log rows expose per-user unread/seen state and an explicit `Mark as seen` action for unread rows.
5. Monitoring mode must not introduce sibling ranking, gradebook editing, or unpublished results.

## 8. Explicit Exclusions

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`

Test refs:

- `ifitwala_ed/api/test_guardian_home.py`

Rules:

1. Guardian Home must not expose `rotation_day` or `block_number` anywhere in the payload or UI.
2. Guardian surfaces must not expose live gradebook rows, staff-only notes, or sibling comparison data.
3. Guardian finance does not create or submit payments in Phase 2; it remains a read-only visibility surface.
4. Any new information block on `/hub/guardian` must be added to this document before it is treated as canonical.

## 9. Contract Matrix

Status: Implemented

Code refs:

- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/api/guardian_finance.py`
- `ifitwala_ed/api/guardian_monitoring.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/guardianHomeService.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_policy_overview.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/acknowledge_guardian_policy.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_finance_snapshot.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_monitoring_snapshot.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/mark_guardian_student_log_read.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianFinance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`

Test refs:

- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts`

| Concern                          | Canonical owner                                                                                                                                                                                    | Code refs                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Test refs                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Schema / DocType                 | Guardian surfaces read guardian links, student logs, outcomes, communications, policy acknowledgements, account holders, invoices, payments, and portal read receipts                              | `api/guardian_home.py`, `governance/doctype/policy_acknowledgement/*`, `accounting/doctype/account_holder/*`, `accounting/doctype/sales_invoice/*`, `accounting/doctype/payment_entry/*`, `students/doctype/student_log/*`, `students/doctype/portal_read_receipt/*`, `assessment/doctype/task_outcome/*`                                                                                                                                                                 | `api/test_guardian_home.py`, `api/test_guardian_phase2.py`                                                                                                                                                                                                                                                                                                                                                    |
| Controller / workflow logic      | Snapshot builder, drill-down filtering, policy acknowledgement flow, finance visibility assembly, monitoring aggregation                                                                           | `api/guardian_home.py`, `api/guardian_policy.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue`                                                                                                                                                                                                                                                                                                           | `api/test_guardian_home.py`, `api/test_guardian_phase2.py`                                                                                                                                                                                                                                                                                                                                                    |
| API endpoints                    | `get_guardian_home_snapshot`, `get_guardian_policy_overview`, `acknowledge_guardian_policy`, `get_guardian_finance_snapshot`, `get_guardian_monitoring_snapshot`, `mark_guardian_student_log_read` | `api/guardian_home.py`, `api/guardian_policy.py`, `api/guardian_finance.py`, `api/guardian_monitoring.py`                                                                                                                                                                                                                                                                                                                                                                 | `api/test_guardian_home.py`, `api/test_guardian_phase2.py`                                                                                                                                                                                                                                                                                                                                                    |
| SPA / UI surfaces                | Guardian Home, Guardian Student Shell, Guardian Policies, Guardian Finance, Guardian Monitoring                                                                                                    | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianStudentShell.vue`, `ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue`                                                                                                                                                                                                                 | `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts` |
| Reports / dashboards / briefings | Home summary cards, finance summary cards, and monitoring summary cards                                                                                                                            | `ui-spa/src/pages/guardian/GuardianHome.vue`, `ui-spa/src/pages/guardian/GuardianFinance.vue`, `ui-spa/src/pages/guardian/GuardianMonitoring.vue`                                                                                                                                                                                                                                                                                                                         | `api/test_guardian_home.py`, `api/test_guardian_phase2.py`                                                                                                                                                                                                                                                                                                                                                    |
| Scheduler / background jobs      | None                                                                                                                                                                                               | None                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | None                                                                                                                                                                                                                                                                                                                                                                                                          |
| Tests                            | Endpoint unit coverage, service transport coverage, and guardian Phase-2 page regression coverage                                                                                                  | `api/test_guardian_home.py`, `api/test_guardian_phase2.py`, `ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts` | Implemented                                                                                                                                                                                                                                                                                                                                                                                                   |
