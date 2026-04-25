# Nested Scope Contract

Status: Active

This document is the canonical contract for NestedSet-backed scope resolution across school-scoped reports, shared visibility helpers, quick-create rooming flows, and location subtree capacity behavior in Ifitwala Ed.

## 1. Canonical Scope Rules

Status: Implemented

Code refs:
- `ifitwala_ed/utilities/tree_utils.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/school_settings/doctype/term/term.py`
- `ifitwala_ed/students/report/attendance_report/attendance_report.py`
- `ifitwala_ed/schedule/report/enrollment_trend_report/enrollment_trend_report.py`
- `ifitwala_ed/schedule/report/enrollment_report/enrollment_report.py`
- `ifitwala_ed/api/enrollment_analytics.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/api/student_overview_dashboard.py`
- `ifitwala_ed/stock/doctype/location/location.py`
- `ifitwala_ed/curriculum/doctype/program/program.py`
- `ifitwala_ed/curriculum/doctype/program/program.js`
- `ifitwala_ed/curriculum/doctype/course/course.js`
- `ifitwala_ed/school_settings/doctype/term/term.js`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.js`

Test refs:
- `ifitwala_ed/utilities/test_school_tree.py`
- `ifitwala_ed/utilities/test_tree_utils.py`
- `ifitwala_ed/students/report/attendance_report/test_attendance_report.py`
- `ifitwala_ed/schedule/report/enrollment_trend_report/test_enrollment_trend_report.py`
- `ifitwala_ed/schedule/report/enrollment_report/test_enrollment_report.py`
- `ifitwala_ed/students/report/case_entries_activity_log/test_case_entries_activity_log.py`
- `ifitwala_ed/accounting/report/student_attribution/test_student_attribution.py`
- `ifitwala_ed/accounting/report/trial_balance/test_trial_balance.py`
- `ifitwala_ed/accounting/report/aged_receivables/test_aged_receivables.py`
- `ifitwala_ed/school_settings/test_school_settings_utils.py`
- `ifitwala_ed/school_settings/doctype/term/test_term.py`
- `ifitwala_ed/api/test_room_utilization.py`
- `ifitwala_ed/stock/doctype/location/test_location.py`
- `ifitwala_ed/curriculum/doctype/program/test_program.py`

Rules:

1. When a feature contract is school-tree-aware, selecting a parent school implies the selected school plus all descendant schools.
2. Tree-aware scope must be applied server-side in SQL `WHERE` clauses before aggregation, not after grouping or client-side in the SPA.
3. Requested school scope must always be intersected with the caller's visible school subtree to preserve sibling isolation.
4. Exact-match school filters are allowed only when the owning contract explicitly states that descendant inheritance is not part of that report or workflow.
5. Shared visibility helpers must preserve the same descendant-aware behavior as the reports and APIs they support.
6. Organization fallback for school-scoped staff visibility must resolve the authorized organization descendant scope first, then use `employee_utils.get_schools_for_organization_scope()` to bridge to schools.
7. Ancestor-school locations may only widen visibility to descendant schools through an explicit location-level sharing rule; sibling schools remain hidden by default.
8. Location capacity enforcement is part of the same nested-scope contract: parent locations must account for descendant-room utilization when capacity is enforced at the parent node.
9. New school-scoped Desk forms may prefill the current user's default school when the document is new and the school field is empty, but the prefill must remain editable unless the workflow contract says the context is locked.
10. Program assessment categories may resolve dynamically from the nearest ancestor when the child program has no local assessment-category rows; local rows remain the canonical override.

## 2. High-Concurrency Plan

Status: Partial

Code refs:
- `ifitwala_ed/utilities/tree_utils.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/stock/doctype/location/location.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/utilities/location_utils.py`
- `ifitwala_ed/students/report/case_entries_activity_log/case_entries_activity_log.py`
- `ifitwala_ed/accounting/report/trial_balance/trial_balance.py`
- `ifitwala_ed/accounting/report/aged_receivables/aged_receivables.py`
- `ifitwala_ed/accounting/report/student_attribution/student_attribution.py`
- `ifitwala_ed/docs/concurrency_01_proposal.md`
- `ifitwala_ed/docs/concurrency_02_proposal.md`
- `ifitwala_ed/docs/high_concurrency_03.md`

Test refs:
- `ifitwala_ed/utilities/test_tree_utils.py`
- `ifitwala_ed/students/report/attendance_report/test_attendance_report.py`
- `ifitwala_ed/schedule/report/enrollment_trend_report/test_enrollment_trend_report.py`
- `ifitwala_ed/schedule/report/enrollment_report/test_enrollment_report.py`
- `ifitwala_ed/school_settings/test_school_settings_utils.py`
- `ifitwala_ed/api/test_room_utilization.py`
- `ifitwala_ed/stock/doctype/location/test_location.py`
- `ifitwala_ed/curriculum/doctype/program/test_program.py`

Plan:

1. Keep scope resolution centralized and cacheable; avoid per-report ad hoc subtree expansion or repeated `get_doc()` traversal in request paths.
2. Prioritize high-traffic read surfaces first: report and analytics scope parity that can be fixed with pre-aggregation `IN %(scope)s` filters and targeted regression tests.
3. Treat remaining exact-match report filters as contract-review items, not blind auto-fixes; accounting and operational reports may have intentionally narrower semantics.
4. Location subtree capacity now uses one descendant-scope expansion plus grouped SQL; keep that pattern request-bounded and avoid per-child loops to preserve write-path concurrency.
5. Shared-location visibility for rooming surfaces must stay centralized in `location_utils.py`; do not reimplement ancestor-sharing math independently in each endpoint or page.
6. School-tree and organization-tree traversal now share a generic utility wrapper; keep future work additive and compatibility-preserving rather than doing a risky repo-wide import rewrite.
7. Keep UX/product follow-ups intentionally small. Default-school prefills and inherited Program assessment-category hints are implemented, but more ambitious UX redesigns still belong in owner docs rather than scope-correctness audits.

## 3. Decision Matrix

Status: Partial

Code refs:
- `ifitwala_ed/students/report/attendance_report/attendance_report.py`
- `ifitwala_ed/schedule/report/enrollment_trend_report/enrollment_trend_report.py`
- `ifitwala_ed/schedule/report/enrollment_report/enrollment_report.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/stock/doctype/location/location.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/curriculum/doctype/program/program.py`
- `ifitwala_ed/setup/setup.py`
- `ifitwala_ed/stock/doctype/location/location.py`
- `ifitwala_ed/students/report/case_entries_activity_log/case_entries_activity_log.py`
- `ifitwala_ed/accounting/report/trial_balance/trial_balance.py`
- `ifitwala_ed/accounting/report/aged_receivables/aged_receivables.py`
- `ifitwala_ed/accounting/report/student_attribution/student_attribution.py`

Test refs:
- `ifitwala_ed/students/report/attendance_report/test_attendance_report.py`
- `ifitwala_ed/schedule/report/enrollment_trend_report/test_enrollment_trend_report.py`
- `ifitwala_ed/schedule/report/enrollment_report/test_enrollment_report.py`
- `ifitwala_ed/school_settings/test_school_settings_utils.py`
- `ifitwala_ed/api/test_room_utilization.py`
- `ifitwala_ed/students/report/case_entries_activity_log/test_case_entries_activity_log.py`
- `ifitwala_ed/accounting/report/student_attribution/test_student_attribution.py`
- `ifitwala_ed/accounting/report/trial_balance/test_trial_balance.py`
- `ifitwala_ed/accounting/report/aged_receivables/test_aged_receivables.py`

| Concern | Status | Decision | Priority | Code refs | Test refs |
| --- | --- | --- | --- | --- | --- |
| Attendance Report parent-school inheritance | Implemented | Keep descendant-aware SQL filter | P0 complete | `students/report/attendance_report/attendance_report.py` | `students/report/attendance_report/test_attendance_report.py` |
| Enrollment Trend Report parent-school inheritance | Implemented | Keep descendant-aware SQL filter | P0 complete | `schedule/report/enrollment_trend_report/enrollment_trend_report.py` | `schedule/report/enrollment_trend_report/test_enrollment_trend_report.py` |
| Enrollment Report helper parity | Implemented | Keep descendant-aware helper intersection contract | P0 complete | `school_settings/school_settings_utils.py`, `schedule/report/enrollment_report/enrollment_report.py` | `school_settings/test_school_settings_utils.py`, `schedule/report/enrollment_report/test_enrollment_report.py` |
| Term DocType parent-school visibility | Implemented | Scripted permissions keep descendant subtree visibility and nearest-ancestor academic-year fallback for the user's branch | P1 complete | `school_settings/doctype/term/term.py` | `school_settings/doctype/term/test_term.py` |
| Ancestor-shared location visibility | Implemented | Allow ancestor-school facilities only through explicit location-level sharing while preserving sibling isolation | P0 complete | `utilities/location_utils.py`, `api/room_utilization.py`, `api/calendar_quick_create.py` | `stock/doctype/location/test_location.py`, `api/test_room_utilization.py` |
| Case Entries Activity Log school filter parity | Implemented | Use descendant-aware school scope intersected with the caller's visible branch via `get_allowed_schools(...)` | P1 complete | `students/report/case_entries_activity_log/case_entries_activity_log.py`, `school_settings/school_settings_utils.py` | `students/report/case_entries_activity_log/test_case_entries_activity_log.py` |
| Trial Balance school-dimension semantics | Implemented | Keep exact-match `GL Entry.school` filtering; descendant inheritance is not part of legal trial-balance semantics | P1 complete | `accounting/report/trial_balance/trial_balance.py`, `docs/accounting/accounting_notes.md` | `accounting/report/trial_balance/test_trial_balance.py` |
| Aged Receivables school-dimension semantics | Partial | Keep exact-match invoice-line existence filtering until the owner contract decides whether the report should stay invoice-level or become line-aware | P1 | `accounting/report/aged_receivables/aged_receivables.py`, `docs/accounting/accounting_notes.md`, `docs/accounting/fees_full_cycle_note.md` | `accounting/report/aged_receivables/test_aged_receivables.py` |
| Student Attribution school filter parity | Implemented | Expand the selected school to its descendant branch on `Sales Invoice Item.school` while keeping `Organization` as the legal scope anchor | P1 complete | `accounting/report/student_attribution/student_attribution.py`, `docs/accounting/accounting_notes.md`, `docs/accounting/fees_full_cycle_note.md` | `accounting/report/student_attribution/test_student_attribution.py` |
| Location descendant-capacity enforcement | Implemented | Parent locations now validate capacity against their descendant booking scope | P1 complete | `stock/doctype/location/location.py`, `utilities/location_utils.py` | `stock/doctype/location/test_location.py` |
| Auto-default school on record creation | Implemented | New `Course`, `Term`, and `Program Enrollment` forms prefill the user's default school when empty | P1 complete | `curriculum/doctype/course/course.js`, `school_settings/doctype/term/term.js`, `schedule/doctype/program_enrollment/program_enrollment.js` | None |
| Program assessment fallback vs copy button | Implemented | Empty child Programs now resolve assessment categories from the nearest ancestor while preserving explicit local rows and the copy action | P1 complete | `curriculum/doctype/program/program.py`, `curriculum/doctype/program/program.js` | `curriculum/doctype/program/test_program.py` |
| Hierarchical school/org picker UI | Planned | Track as SPA product enhancement, not scope-correctness blocker | P2 | Multiple Desk/SPA surfaces | None |
| Generic `tree_utils` refactor | Implemented | Shared tree wrapper added; existing school/org helpers now delegate to it | P1 complete | `utilities/tree_utils.py`, `utilities/school_tree.py`, `utilities/employee_utils.py` | `utilities/test_tree_utils.py` |

## 4. Contract Matrix

Status: Partial

Code refs:
- `ifitwala_ed/utilities/tree_utils.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/students/report/attendance_report/attendance_report.py`
- `ifitwala_ed/schedule/report/enrollment_trend_report/enrollment_trend_report.py`
- `ifitwala_ed/schedule/report/enrollment_report/enrollment_report.py`
- `ifitwala_ed/api/enrollment_analytics.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/api/student_overview_dashboard.py`
- `ifitwala_ed/stock/doctype/location/location.py`
- `ifitwala_ed/utilities/location_utils.py`
- `ifitwala_ed/curriculum/doctype/program/program.py`
- `ifitwala_ed/curriculum/doctype/program/program.js`
- `ifitwala_ed/curriculum/doctype/course/course.js`
- `ifitwala_ed/school_settings/doctype/term/term.js`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.js`

Test refs:
- `ifitwala_ed/utilities/test_school_tree.py`
- `ifitwala_ed/utilities/test_tree_utils.py`
- `ifitwala_ed/students/report/attendance_report/test_attendance_report.py`
- `ifitwala_ed/schedule/report/enrollment_trend_report/test_enrollment_trend_report.py`
- `ifitwala_ed/schedule/report/enrollment_report/test_enrollment_report.py`
- `ifitwala_ed/students/report/case_entries_activity_log/test_case_entries_activity_log.py`
- `ifitwala_ed/accounting/report/student_attribution/test_student_attribution.py`
- `ifitwala_ed/accounting/report/trial_balance/test_trial_balance.py`
- `ifitwala_ed/accounting/report/aged_receivables/test_aged_receivables.py`
- `ifitwala_ed/school_settings/test_school_settings_utils.py`
- `ifitwala_ed/api/test_room_utilization.py`
- `ifitwala_ed/stock/doctype/location/test_location.py`
- `ifitwala_ed/curriculum/doctype/program/test_program.py`
- `ifitwala_ed/setup/test_setup_roles.py`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | NestedSet-backed `School`, `Organization`, `Location`, and `Program` | `utilities/tree_utils.py`, `utilities/school_tree.py`, `utilities/location_utils.py`, `stock/doctype/location/location.py`, `curriculum/doctype/program/program.py` | `utilities/test_school_tree.py`, `utilities/test_tree_utils.py`, `curriculum/doctype/program/test_program.py` |
| Controller / workflow logic | Shared scope helpers, Program ancestor fallback, and Location capacity enforcement | `school_settings/school_settings_utils.py`, `curriculum/doctype/program/program.py`, `stock/doctype/location/location.py` | `school_settings/test_school_settings_utils.py`, `curriculum/doctype/program/test_program.py`, `stock/doctype/location/test_location.py` |
| DocType scripted permissions | Term visibility keeps descendant subtree access plus nearest-ancestor fallback per academic year for the user's branch | `school_settings/doctype/term/term.py` | `school_settings/doctype/term/test_term.py` |
| API endpoints | Analytics and rooming endpoints that honor descendant scope plus explicit ancestor-sharing | `api/enrollment_analytics.py`, `api/student_overview_dashboard.py`, `api/room_utilization.py`, `api/calendar_quick_create.py` | `api/test_room_utilization.py` plus existing endpoint tests outside this contract |
| SPA / UI surfaces | Tree-aware analytics/report entry points plus default-school prefill and inherited Program assessment-category hinting | `docs/spa/06_analytics_pages.md`, `curriculum/doctype/program/program.js`, `curriculum/doctype/course/course.js`, `school_settings/doctype/term/term.js`, `schedule/doctype/program_enrollment/program_enrollment.js` | None |
| Reports / dashboards / briefings | Attendance, Enrollment Trend, Enrollment Report, Case Entries Activity Log, and Student Attribution are implemented; Trial Balance exact-match semantics are locked; Aged Receivables still needs an owner decision on invoice-vs-line school semantics | `students/report/attendance_report/attendance_report.py`, `students/report/case_entries_activity_log/case_entries_activity_log.py`, `schedule/report/enrollment_trend_report/enrollment_trend_report.py`, `schedule/report/enrollment_report/enrollment_report.py`, `accounting/report/student_attribution/student_attribution.py`, `accounting/report/trial_balance/trial_balance.py`, `accounting/report/aged_receivables/aged_receivables.py` | Report tests listed above |
| Scheduler / background jobs | None currently required for scope parity; location fix must remain request-bounded | None | None |
| Tests | School-tree helper and report query-contract regression coverage | `utilities/test_school_tree.py`, `students/report/attendance_report/test_attendance_report.py`, `schedule/report/enrollment_trend_report/test_enrollment_trend_report.py`, `schedule/report/enrollment_report/test_enrollment_report.py`, `school_settings/test_school_settings_utils.py` | Same |

## 5. Technical Notes (IT)

Status: Partial

Code refs:
- `ifitwala_ed/utilities/tree_utils.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/utilities/location_utils.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/api/calendar_quick_create.py`
- `ifitwala_ed/curriculum/doctype/program/program.py`

Test refs:
- `ifitwala_ed/utilities/test_school_tree.py`
- `ifitwala_ed/utilities/test_tree_utils.py`
- `ifitwala_ed/school_settings/test_school_settings_utils.py`
- `ifitwala_ed/api/test_room_utilization.py`
- `ifitwala_ed/stock/doctype/location/test_location.py`
- `ifitwala_ed/curriculum/doctype/program/test_program.py`

- School subtree resolution should prefer existing helpers over bespoke direct traversal inside reports.
- Generic tree traversal now lives in `utilities/tree_utils.py`; doctype-specific helpers remain as compatibility wrappers so callers do not drift all at once.
- Scope caches must always be keyed by permission scope and selected filter context; stale shared caches are a data-leak risk.
- Term Desk visibility now keeps descendant subtree access and only widens to the nearest ancestor term source per academic year for the user's own branch; sibling terms remain hidden.
- Report fixes should continue to favor SQL `IN %(scope)s` predicates over Python-side filtering for both correctness and concurrency.
- Shared ancestor-school facilities must be opt-in on the Location row itself; broad parent-school visibility remains a multi-tenant defect.
- Setup seeds persisted global roots for `Program`, `Department`, and `Location`. The `All Locations` root is an unscoped global container only; child Locations still own their Organization and must pass the normal school/organization membership checks.
- Location capacity validation now uses descendant location scope in one grouped query so parent-room capacity checks stay concurrency-safe.
- Program assessment categories now resolve from the nearest ancestor only when the local child table is empty; explicit local rows remain the canonical override.
- Deleting the superseded audit is safe only because this document now owns the open decisions, statuses, and execution order.
