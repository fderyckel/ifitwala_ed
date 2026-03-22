# Academic Load Dashboard Contract (v1)

Status: Active

This document is the canonical contract for the Academic Load dashboard surface, its school-configurable scoring policy, and its supporting API methods.

Authority order:

1. `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`
2. `ifitwala_ed/docs/spa/06_analytics_pages.md`
3. `ifitwala_ed/docs/high_concurrency_contract.md`
4. This document

If implementation changes this feature, update this document in the same change.

## 1. Surface and Routing

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/AcademicLoad.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`

Test refs:
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/AcademicLoad.test.ts`

Rules:

1. The canonical staff route is `/staff/analytics/academic-load`.
2. The canonical route name is `staff-academic-load`.
3. The page lives under `ui-spa/src/pages/staff/analytics/` and owns orchestration only.
4. Staff Home links to this page from the Scheduling & Capacity analytics category.
5. The page uses the shared `FiltersBar` and POST-only analytics calls.

## 2. Access and Scope Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/academic_load.py`
- `ifitwala_ed/api/portal.py`
- `ifitwala_ed/api/student_log_dashboard.py`
- `ifitwala_ed/school_settings/doctype/academic_load_policy/academic_load_policy.py`

Test refs:
- `ifitwala_ed/api/test_academic_load.py`
- `ifitwala_ed/api/test_analytics_permissions.py`

Rules:

1. Dashboard access is restricted to `Academic Admin`, `Academic Assistant`, `Assistant Admin`, `Curriculum Coordinator`, `System Manager`, and `Administrator`.
2. `Instructor` and `Academic Staff` do not receive page access or Staff Home discoverability for this dashboard.
3. Selected school scope must be intersected with `get_authorized_schools(user)` before aggregation.
4. Parent-school selection includes descendants server-side only.
5. `Academic Load Policy` desk access is school-scoped and must not leak sibling schools.

## 3. Policy and Zero-Config Contract

Status: Implemented

Code refs:
- `ifitwala_ed/school_settings/doctype/academic_load_policy/academic_load_policy.json`
- `ifitwala_ed/school_settings/doctype/academic_load_policy/academic_load_policy.py`
- `ifitwala_ed/school_settings/doctype/school/school.py`
- `ifitwala_ed/patches/create_default_academic_load_policies.py`

Test refs:
- `ifitwala_ed/school_settings/doctype/academic_load_policy/test_academic_load_policy.py`

Rules:

1. Every school must have one active default `Academic Load Policy`.
2. Existing schools are backfilled through a patch; new schools create a default policy on insert.
3. The default policy is zero-config usable with these defaults:
   - teaching weight `1.0`
   - student weight `1.0`
   - student ratio divisor `15`
   - activity weight `1.0`
   - meeting weight `0.75`
   - school event weight `0.75`
   - meeting window `30` days
   - future horizon `14` days
   - blend mode `Blended Past + Future`
   - thresholds `12 / 24 / 30`
   - exclude cancelled meetings `1`
4. `was_customized` flips when an existing policy is edited.
5. Only one active policy per school is allowed.

## 4. Facts, Scoring, and v1 Exclusions

Status: Implemented

Code refs:
- `ifitwala_ed/api/academic_load.py`
- `ifitwala_ed/hr/doctype/employee_booking/employee_booking.json`
- `ifitwala_ed/setup/doctype/meeting/meeting.json`
- `ifitwala_ed/setup/doctype/meeting_participant/meeting_participant.json`
- `ifitwala_ed/school_settings/doctype/school_event/school_event.json`
- `ifitwala_ed/school_settings/doctype/school_event_participant/school_event_participant.json`
- `ifitwala_ed/eca/doctype/program_offering_activity_section/program_offering_activity_section.json`

Test refs:
- `ifitwala_ed/api/test_academic_load.py`

Rules:

1. The page separates observable workload facts from configurable school scoring.
2. v1 facts are limited to:
   - teaching load from materialized `Employee Booking` teaching rows joined to `Student Group`
   - student adjustment from active `Student Group Student` counts
   - activity load from activity `Student Group` rows and linked activity sections
   - meeting load from explicit `Meeting Participant.employee`
   - school event load from explicit `School Event Participant.participant -> Employee.user_id`
3. School events count only explicit participants in v1. Audience rows do not contribute workload.
4. Duties, cover history, and persisted snapshots are intentionally out of scope for v1.
5. The final score is a comparison aid only; the UI must always show the component breakdown.

## 5. API and Cache Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/academic_load.py`
- `ifitwala_ed/hooks.py`

Test refs:
- `ifitwala_ed/api/test_academic_load.py`

Rules:

1. `get_academic_load_filter_meta(payload=None)` returns allowed schools, academic years, student-group options, staff-role options, and the active policy summary.
2. Academic year options must support nearest-ancestor fallback when the selected school keeps its calendar higher in the school tree, and may infer year names from visible student groups when no direct `Academic Year` rows exist in scope.
3. `get_academic_load_dashboard(payload=None, start=0, page_length=50)` returns `policy`, `summary`, `kpis`, `rows`, `fairness`, and `effective_filters`.
4. `get_academic_load_staff_detail(payload=None, employee=None)` returns one educator detail payload with breakdown tabs.
5. `get_academic_load_cover_candidates(payload=None, student_group=None, from_datetime=None, to_datetime=None)` ranks substitute candidates for one requested block.
6. Dashboard caches are Redis-scoped by user, filters, and an Academic Load cache version.
7. Cache invalidation is triggered by `Student Group`, `Student Group Student`, `Student Group Instructor`, `Program Offering`, `Program Offering Activity Section`, `Meeting`, `Meeting Participant`, `School Event`, `School Event Participant`, `Employee Booking`, and `Academic Load Policy` changes.

## 6. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/school_settings/doctype/academic_load_policy/academic_load_policy.py`
- `ifitwala_ed/api/academic_load.py`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/AcademicLoad.vue`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`

Test refs:
- `ifitwala_ed/school_settings/doctype/academic_load_policy/test_academic_load_policy.py`
- `ifitwala_ed/api/test_academic_load.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/AcademicLoad.test.ts`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | `Academic Load Policy` | `school_settings/doctype/academic_load_policy/*` | `school_settings/doctype/academic_load_policy/test_academic_load_policy.py` |
| Controller / workflow logic | policy defaults, single-active enforcement, default-policy creation | `academic_load_policy.py`, `school.py`, `patches/create_default_academic_load_policies.py` | `test_academic_load_policy.py` |
| API endpoints | filter meta, dashboard, detail, cover candidates | `api/academic_load.py` | `api/test_academic_load.py` |
| SPA / UI surfaces | staff analytics page and Staff Home discoverability | `AcademicLoad.vue`, `router/index.ts`, `StaffHome.vue` | `AcademicLoad.test.ts` |
| Reports / dashboards | fairness distribution and cover ranking | `api/academic_load.py`, `AcademicLoad.vue` | `api/test_academic_load.py`, `AcademicLoad.test.ts` |
| Scheduler / background jobs | none in v1 | none | none |
| Cache invalidation | doc-event version bumping for hot-path freshness | `hooks.py`, `academic_load_policy.py` | `api/test_academic_load.py` |
