# Student Overview Dashboard Contract (v1)

Status: Active

This document is the canonical contract for the Student Overview dashboard surface and its supporting API methods.

Authority order:

1. `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`
2. `ifitwala_ed/docs/spa/06_analytics_pages.md`
3. This document

If implementation changes this feature, update this document in the same change.

## 1. Surface and Routing

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentOverview.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`

Test refs:
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StudentOverview.test.ts`

Rules:

1. The canonical staff route is `/staff/analytics/student-overview`.
2. The canonical route name is `staff-student-overview`.
3. The page lives under `ui-spa/src/pages/staff/analytics/` and owns orchestration only.
4. Staff Home links to this page from the Academic Performance analytics section.
5. Class Hub also links to this named route.

## 2. Load and View-Mode Contract

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentOverview.vue`
- `ifitwala_ed/api/student_overview_dashboard.py`

Test refs:
- `ifitwala_ed/api/test_student_overview_dashboard.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StudentOverview.test.ts`

Rules:

1. The page owns one filter object with `school`, `program`, and `student`.
2. `get_filter_meta()` auto-loads on page mount and may set the default school.
3. When `school` changes, the page clears the selected `program` and `student`.
4. The snapshot is loaded only when `school`, `program`, and `student` are all present.
5. The snapshot request is a POST to `get_student_center_snapshot(student, school, program, view_mode)` with the JSON body sent directly, not wrapped inside a nested payload key.
6. The current SPA selector exposes `staff`, `student`, and `guardian` view modes.
7. The backend permission helper also accepts `admin`, `counselor`, and `attendance` as non-student view modes, but the current page does not expose those options.
8. The student search API can support blank search on the server, but the current page only issues search requests when the user has typed a non-empty query.
9. Snapshot reloads are debounced on the client and skipped while an in-flight snapshot request is already loading; this is a UX throttle, not a correctness guarantee.
10. Task, attendance, wellbeing, and history year-scope controls refer to academic years, not calendar years.
11. The top school/program/student controls must render inside the shared `FiltersBar` component.

## 3. Visibility and Scope Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/student_overview_dashboard.py`
- `ifitwala_ed/api/student_log_dashboard.py`
- `ifitwala_ed/api/portal.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/students/doctype/student_log/student_log.py`

Test refs:
- `ifitwala_ed/api/test_student_overview_dashboard.py`
- Direct permission regression coverage for this module: `None`

Rules:

1. Guest users are denied before any dashboard data is returned.
2. Student users are mapped from `Student.student_email == session user`.
3. Guardian users are mapped through `Student Guardian` rows linked from `Guardian.user`.
4. Students and guardians can only view students inside their resolved scope.
5. Staff eligibility is restricted to `Academic Admin`, `Counselor`, `Curriculum Coordinator`, `Attendance`, `Pastoral Lead`, `System Manager`, `Administrator`, `Academic Staff`, and `Instructor`.
6. `Academic Assistant` must not be treated as a Student Overview staff role or as a proxy through another analytics capability.
7. Staff Home discoverability for this page must use a dedicated Student Overview capability, not `analytics_attendance`.
8. Staff scope is derived from `get_authorized_schools(user)`.
9. For staff snapshot requests, the selected `school` must be inside the authorized school set.
10. School scoping for student search uses descendant schools from `get_descendant_schools(...)`, intersected with the staff authorized set when applicable.
11. Program scoping uses the `Program` NestedSet subtree when a program filter is present.
12. Snapshot access does not hard-deny on program mismatch; student scope and school scope are the canonical guards.
13. Student log rows and student log support counts inside the snapshot must reuse `get_student_log_visibility_predicate(..., allow_aggregate_only=False)`.

## 4. Snapshot Payload Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/student_overview_dashboard.py`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentOverview.vue`

Test refs:
- `ifitwala_ed/api/test_student_overview_dashboard.py`
- Block-level payload coverage beyond query-shape assertions: `None`

Rules:

1. `get_student_center_snapshot(...)` returns exactly these top-level blocks: `meta`, `identity`, `kpis`, `learning`, `attendance`, `wellbeing`, `history`.
2. `meta.current_academic_year` is copied from `identity.program_enrollment.academic_year`.
3. `identity` is assembled from `Student`, the latest matching `Program Enrollment` inside the selected program subtree and selected school descendants, and `Student Group Student` joined to `Student Group`.
4. `kpis` currently contains attendance, task, support, and placeholder academic summary values.
5. `learning` is assembled from current `Task Delivery` rows scoped to the student through `Student Group Student`, left-joined to `Task Outcome`, `Student Group`, and `Course`, plus `Program Enrollment Course` rows for current courses.
6. Task-derived KPI, learning, and history blocks now read the current `Task Delivery` / `Task Outcome` model; the snapshot no longer uses the legacy `Task Student` table.
7. `attendance` is assembled from `Student Attendance`, `Student Attendance Code`, and `Course`, and the snapshot returns attendance rows across available academic years so the SPA can apply `This academic year`, `Last academic year`, and `All academic years` client-side.
8. `wellbeing.timeline` is event-only and merges visible `Student Log`, `Student Referral`, and `Student Patient Visit` rows, then sorts newest-first and trims to 30 items.
9. `wellbeing.timeline[].summary` returns stripped text for each capped row; the SPA owns collapse/expand behavior and renders the latest 10 timeline rows before older dashboard rows move into a scroll region.
10. `wellbeing.health_note` is a separate optional staff-facing card sourced from `Student Patient.medical_info`; it is not inserted into the date-sorted timeline.
11. Referral rows in `wellbeing.timeline` must honor `Student Referral` server-side permission rules before they are returned to the SPA.
12. Nurse visit rows in `wellbeing.timeline` must use `Student Patient Visit.note` only; `treatment` is not part of the dashboard timeline contract.
13. `history.year_options` use `Program Enrollment.academic_year` as the canonical backbone.
14. `history.academic_trend` is derived from task rows grouped by academic year.
15. `history.attendance_trend` is derived from distinct `Student Attendance.academic_year` values.
16. `history.reflection_flags` is currently returned as an empty list.

## 5. Query and Frappe v16 Contract Notes

Status: Implemented

Code refs:
- `ifitwala_ed/api/student_overview_dashboard.py`
- `ifitwala_ed/api/test_student_overview_dashboard.py`

Test refs:
- `ifitwala_ed/api/test_student_overview_dashboard.py`

Rules:

1. Student-scoped filter metadata queries must use simple field names plus `distinct=True`; raw select fragments such as `fields=["distinct school"]` are not part of the valid Frappe v16 contract.
2. History attendance-year queries must use simple field names plus `distinct=True`; raw select fragments such as `fields=["distinct academic_year as ay"]` are not part of the valid Frappe v16 contract.
3. The student overview API must not rely on query syntax that Frappe rejects before business permission checks, because that produces false `403` responses in the SPA.
4. The regression test module locks the safe distinct-query shape for both `get_filter_meta()` and `_history_block(...)`.
5. The task reader path must use the current `Task Delivery` / `Task Outcome` contract and must not reintroduce a `Task Student` compatibility read path.
6. This feature currently has no Redis snapshot cache, no ETag contract, and no background job fan-out; the snapshot is request-time computed.

## 6. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/api/student_overview_dashboard.py`
- `ifitwala_ed/api/student_log_dashboard.py`
- `ifitwala_ed/students/doctype/student_log/student_log.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentOverview.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`

Test refs:
- `ifitwala_ed/api/test_student_overview_dashboard.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StudentOverview.test.ts`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | `Student`, `Program Enrollment`, `Program Enrollment Course`, `Student Group`, `Student Group Student`, `Student Attendance`, `Student Attendance Code`, `Task`, `Task Delivery`, `Task Outcome`, `Student Log`, `Student Referral`, `Student Patient`, `Student Patient Visit` | `ifitwala_ed/api/student_overview_dashboard.py` | `ifitwala_ed/api/test_student_overview_dashboard.py` |
| Controller / workflow logic | `student_overview_dashboard.py` block builders and scope checks | `ifitwala_ed/api/student_overview_dashboard.py` | `ifitwala_ed/api/test_student_overview_dashboard.py` |
| API endpoints | `get_filter_meta`, `search_students`, `get_student_center_snapshot` | `ifitwala_ed/api/student_overview_dashboard.py` | `ifitwala_ed/api/test_student_overview_dashboard.py` |
| SPA/UI surfaces | Staff analytics page and its named route | `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentOverview.vue` | `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StudentOverview.test.ts` |
| Reports / dashboards / briefings | Staff Home and Class Hub entry points into Student Overview | `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue` | `None` |
| Scheduler / background jobs | None | None | None |
| Tests | Backend regression coverage for Frappe v16-safe distinct queries plus the Student Overview SPA shell contract | `ifitwala_ed/api/test_student_overview_dashboard.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StudentOverview.test.ts` | `ifitwala_ed/api/test_student_overview_dashboard.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StudentOverview.test.ts` |
