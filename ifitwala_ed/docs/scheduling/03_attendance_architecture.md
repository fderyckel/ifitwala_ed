# Attendance Architecture

## Status

Active. Canonical attendance architecture note for ledger ownership, meeting-date resolution, staff and guardian read models, and the scheduling boundary that attendance depends on.

Code refs:
- `ifitwala_ed/students/doctype/student_attendance/student_attendance.py`
- `ifitwala_ed/students/doctype/student_attendance/student_attendance.json`
- `ifitwala_ed/schedule/attendance_utils.py`
- `ifitwala_ed/schedule/attendance_jobs.py`
- `ifitwala_ed/api/student_attendance.py`
- `ifitwala_ed/api/attendance.py`
- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.json`

Test refs:
- `ifitwala_ed/schedule/test_attendance_utils.py`
- `ifitwala_ed/api/test_attendance.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/students/report/attendance_report/test_attendance_report.py`

This document is authoritative for:

- what object is attendance truth
- how valid meeting dates are derived
- how group attendance is written today
- which read surfaces own staff, analytics, and guardian attendance views
- which cache and invalidation rules attendance depends on
- which current gaps must not be papered over during refactors

If code and this note disagree, stop and resolve the drift explicitly.

Related architecture:

- `docs/scheduling/01_scheduling_architecture.md`
- `docs/scheduling/02_student_group_generation_architecture.md`
- `docs/enrollment/02_school_calendar_architecture.md`
- `docs/enrollment/08_enrollment_scheduling_contract.md`
- `docs/student/student_attendance_analytics.md`
- `docs/docs_md/student-group.md`

---

## 1. Core Definition

### 1.1 Attendance truth lives in the ledger

`Student Attendance` is the canonical attendance fact table.

Attendance truth is not:

- inferred from `Student Group Schedule`
- inferred from `Employee Booking` or `Location Booking`
- inferred from analytics aggregates
- inferred client-side from meeting dates alone

Every attendance-facing surface must ultimately read or write `Student Attendance`.

### 1.2 Attendance is downstream of scheduling, not a substitute for it

Attendance consumes scheduling context to decide:

- whether a date is a valid meeting day
- which block number and rotation day apply
- which instructor and location metadata should be stamped on insert

Attendance does not own:

- timetable construction
- school calendar definition
- booking materialization
- enrollment entitlement

If a change tries to make attendance recreate scheduling rules ad hoc, that change is architecturally wrong.

---

## 2. Canonical Layer Stack

Status: Active
Code refs:
- `ifitwala_ed/students/doctype/student_attendance/student_attendance.py`
- `ifitwala_ed/schedule/attendance_utils.py`
- `ifitwala_ed/api/student_attendance.py`
- `ifitwala_ed/api/attendance.py`
- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
Test refs:
- `ifitwala_ed/schedule/test_attendance_utils.py`
- `ifitwala_ed/api/test_attendance.py`
- `ifitwala_ed/api/test_guardian_phase2.py`

Attendance is only correct when these layers stay separate:

| Layer | Responsibility | Must not be treated as |
| --- | --- | --- |
| `School Calendar` + `School Schedule` + `Academic Year` | instructional date envelope, rotation expansion, holiday exclusion | attendance truth |
| `Student Group` + `Student Group Schedule` | attendance-eligible operational group, block usage, attendance scope metadata | attendance ledger |
| `attendance_utils.get_meeting_dates(...)` | cached valid meeting-date expansion for one group | a UI-only helper or client-owned calculation |
| `Student Attendance` | durable attendance ledger facts | derived analytics or schedule intent |
| `api/student_attendance.py` | staff tool bootstrap and scoped roster read model | source of truth for the ledger itself |
| `api/attendance.py` | analytics read model and aggregates | write path or permission bypass |
| `api/guardian_attendance.py` | guardian-scoped family read model | general attendance query API |

---

## 3. Attendance Record Models

Status: Active with partial runtime split
Code refs:
- `ifitwala_ed/students/doctype/student_attendance/student_attendance.py`
- `ifitwala_ed/students/doctype/student_attendance/student_attendance.json`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.json`
- `ifitwala_ed/api/attendance.py`
Test refs:
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/students/report/attendance_report/test_attendance_report.py`

There are two attendance record shapes in current runtime.

### 3.1 Block attendance

Block attendance is one ledger row per:

- student
- student group
- attendance date
- block number

This is the verified canonical write model for the staff attendance tool today.

### 3.2 Whole-day attendance

Whole-day attendance is one ledger row per:

- student
- attendance date
- `whole_day = 1`

This shape is implemented in the `Student Attendance` controller and consumed by downstream reads and analytics.

### 3.3 Non-negotiable separation rule

Whole-day and block attendance are separate modes.

They must not be mixed implicitly in:

- analytics summaries
- guardian day-state resolution
- tool defaults
- refactors that try to collapse both shapes into one generic record path

The analytics note under `docs/student/student_attendance_analytics.md` already locks this at the product layer, and runtime code honors it through explicit `whole_day` filtering.

---

## 4. Meeting-Date Resolution Contract

Status: Active
Code refs:
- `ifitwala_ed/schedule/attendance_utils.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/schedule_utils.py`
Test refs:
- `ifitwala_ed/schedule/test_attendance_utils.py`
- `ifitwala_ed/api/test_attendance.py`

`get_meeting_dates(student_group)` is the canonical helper for valid attendance dates.

It resolves dates in this order:

1. read the group's explicit `school_schedule`
2. if missing, resolve the effective schedule for the group's Academic Year and school
3. read the set of rotation days actually used by that group's `Student Group Schedule`
4. expand full rotation dates with `include_holidays=False`
5. keep only dates whose rotation day is used by the group

Operational consequences:

- holidays are excluded
- a group with no schedule rows has no meeting dates
- meeting-date validity is server-owned
- clients must not recreate this date list from raw calendar data

### 4.1 Cache ownership

Meeting dates are cached in Redis per group using the `ifw:meeting_dates:{student_group}` key for one day.

That cache is owned by `attendance_utils`.

Consumers must not:

- create parallel meeting-date caches
- invalidate attendance date caches ad hoc from unrelated modules
- assume cache freshness without using the canonical invalidation path

### 4.2 Invalidation ownership

`Student Group.after_save()` invalidates meeting dates when the inputs that change date validity move:

- `school_schedule`
- `academic_year`
- the set of rotation days used by group schedule rows

That is the canonical invalidation trigger.

### 4.3 Prewarm contract

`schedule/attendance_jobs.py` prewarms meeting-date caches for candidate groups in the current Academic Year during the morning guard window.

This job is an optimization only.

It must not be treated as:

- required for correctness
- a substitute for synchronous meeting-date validation on write

---

## 5. Staff Recording Write Path

Status: Active for block-oriented bulk recording
Code refs:
- `ifitwala_ed/schedule/attendance_utils.py`
- `ifitwala_ed/students/doctype/student_attendance/student_attendance.py`
- `ifitwala_ed/api/student_attendance.py`
Test refs:
- `ifitwala_ed/schedule/test_attendance_utils.py`
- `ifitwala_ed/api/test_attendance.py`

`bulk_upsert_attendance(payload)` in `attendance_utils.py` is the verified canonical bulk write path for staff attendance recording.

### 5.1 Payload model

The current bulk path expects each row to include:

- `student`
- `student_group`
- `attendance_date`
- `attendance_code`
- `block_number`
- `remark`

The write path is group-aware and block-aware.

### 5.2 Server-side guards

The bulk writer owns these validations:

- payload shape validation
- staff permission validation
- current-term edit guard when a current term exists
- Academic Year fallback guard when term resolution is absent
- valid meeting-date enforcement through `get_meeting_dates(...)`
- rotation-day and schedule-row lookup for metadata enrichment

This means the client does not own attendance eligibility.

### 5.3 Permission model

Current runtime allows:

- `Academic Admin` broad write access
- non-admin instructor write access only when the user is assigned to the target `Student Group`

Refactors must preserve that the server, not the client, decides whether the user may record attendance for a group.

### 5.4 Ledger enrichment

On insert, the writer stamps operational metadata onto `Student Attendance`, including:

- `attendance_time`
- `attendance_method`
- `academic_year`
- `term`
- `program`
- `course`
- `school`
- `rotation_day`
- `block_number`
- `instructor`
- `location`

This enrichment exists so downstream analytics and read surfaces can query the ledger directly instead of rejoining schedule context on every request.

### 5.5 Duplicate rules

Current duplicate protection lives in two places:

- `bulk_upsert_attendance(...)` performs composite-key existence checks for update-vs-insert behavior
- `StudentAttendance.validate()` enforces uniqueness rules for normal document writes

Those rules must remain aligned.

---

## 6. Read Models And Surface Ownership

Status: Active
Code refs:
- `ifitwala_ed/api/student_attendance.py`
- `ifitwala_ed/api/attendance.py`
- `ifitwala_ed/api/guardian_attendance.py`
- `ifitwala_ed/schedule/attendance_utils.py`
Test refs:
- `ifitwala_ed/api/test_attendance.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/students/report/attendance_report/test_attendance_report.py`

### 6.1 Staff attendance tool

`api/student_attendance.py` owns the staff tool read model.

It provides:

- scoped student-group lists
- filter bootstrap context
- group context with weekend days, meeting dates, recorded dates, and default selected date
- roster context with students, previous status hints, existing attendance map, and scheduled blocks

This is a bounded bootstrap/read-model design and must stay aligned with `docs/high_concurrency_contract.md`.

### 6.2 Attendance analytics

`api/attendance.py` owns analytics and ledger-style aggregates.

It supports multiple modes, including:

- overview
- heatmap
- risk
- code usage
- my groups
- ledger

Analytics always reads attendance from `Student Attendance` with explicit scope, hierarchy, and `whole_day` mode handling.

Analytics must not infer attendance from schedule rows or client-submitted aggregates.

### 6.3 Guardian attendance

`api/guardian_attendance.py` owns the guardian family attendance snapshot.

It is read-only and family-scoped.

Guardian day-state resolution is derived from ledger rows and `Student Attendance Code` semantics:

- absence when any row is absent and not merely late
- late when at least one row is late and no absence row wins
- present otherwise

Guardian consumers must not bypass this API with raw attendance queries.

---

## 7. Scope, Permissions, And Tenant Rules

Status: Active
Code refs:
- `ifitwala_ed/api/student_attendance.py`
- `ifitwala_ed/api/attendance.py`
- `ifitwala_ed/api/guardian_attendance.py`
Test refs:
- `ifitwala_ed/api/test_attendance.py`
- `ifitwala_ed/api/test_guardian_phase2.py`

Attendance is multi-tenant and role-scoped.

Current runtime separates scope by surface:

- staff tool endpoints clamp group visibility to role and school scope
- analytics resolves school scope, group scope, and student scope server-side
- guardian attendance clamps records to the guardian's children

Non-negotiable rule:

attendance scope must be enforced server-side before query execution.

Do not move these rules into:

- SPA filtering only
- client-side hidden options
- report-specific ad hoc scope math

---

## 8. Concurrency, Caching, And Request Design

Status: Active
Code refs:
- `ifitwala_ed/schedule/attendance_utils.py`
- `ifitwala_ed/schedule/attendance_jobs.py`
- `ifitwala_ed/api/student_attendance.py`
- `ifitwala_ed/api/attendance.py`
Test refs:
- `ifitwala_ed/api/test_attendance.py`

Attendance is a hot-path domain.

Current runtime already uses bounded read-model patterns:

- meeting dates cached per group
- attendance tool bootstrap/context aggregation instead of client waterfalls
- analytics result caching by mode and scope
- optional morning prewarm for meeting-date caches

Refactors must preserve:

- one bounded bootstrap path for staff attendance setup
- ledger-first reads for analytics
- server-owned cache keys and invalidation rules
- no client-owned polling loop for attendance date computation

If a change increases request fan-out or duplicates attendance date resolution in multiple APIs, it is a regression.

---

## 9. Student Group Contract For Attendance

Status: Active with known implementation split
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.json`
- `ifitwala_ed/docs/docs_md/student-group.md`
Test refs:
- no dedicated attendance-scope tests were found in the inspected attendance test set

`Student Group` exposes attendance configuration through `attendance_scope`:

- `Per Block`
- `Whole Day`
- `None`

The controller property `is_whole_day_group` maps `attendance_scope = Whole Day`.

This field is architectural metadata for attendance behavior and must not be ignored in future refactors.

Current implementation nuance:

- the field exists on `Student Group`
- whole-day semantics exist in the ledger and analytics layers
- the verified bulk recording helper in `attendance_utils.py` is still group/block oriented

Do not document or assume a fully unified whole-day recording workflow unless code is added and this note is updated in the same change.

---

## 10. Known Drift And Refactor Constraints

Status: Active with explicit drift
Code refs:
- `ifitwala_ed/schedule/attendance_utils.py`
- `ifitwala_ed/students/doctype/student_attendance/student_attendance.py`
- `ifitwala_ed/api/attendance.py`
- `ifitwala_ed/api/guardian_attendance.py`
Test refs:
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/students/report/attendance_report/test_attendance_report.py`

### 10.1 Whole-day support is real, but the verified bulk writer is not whole-day-first

Current runtime clearly supports:

- whole-day ledger rows
- whole-day uniqueness validation
- whole-day analytics filtering
- whole-day guardian/report reads

But in the inspected attendance helper set, the canonical staff bulk writer still requires `student_group` and `block_number` and validates meeting dates from group schedule context.

Therefore:

- do not claim the current tooling is attendance-mode agnostic
- do not collapse whole-day and block write paths without an explicit design decision
- do not remove current block enrichment fields just because whole-day rows also exist

### 10.2 `attendance_scope = None` is not a substitute for server write enforcement

The inspected bulk attendance helper does not use `attendance_scope` as its primary write gate.

That means future refactors should treat attendance scope enforcement as a design task to be made explicit, not as a rule already guaranteed everywhere.

### 10.3 `student_group` is still stored as `Data` on the ledger

`Student Attendance.student_group` is currently a `Data` field, not a `Link`.

Refactors must not assume link-field semantics, automatic joins, or framework-level referential behavior that does not exist today.

---

## 11. Non-Negotiable Refactor Rules

Status: Locked
Code refs:
- `ifitwala_ed/schedule/attendance_utils.py`
- `ifitwala_ed/api/student_attendance.py`
- `ifitwala_ed/api/attendance.py`
- `ifitwala_ed/api/guardian_attendance.py`

When refactoring attendance:

1. Keep `Student Attendance` as the canonical attendance fact table unless architecture is explicitly changed.
2. Keep meeting-date validity server-owned through the canonical helper, not client inference.
3. Preserve strict separation between block attendance and whole-day attendance semantics.
4. Preserve server-side scope and permission enforcement for staff and guardian surfaces.
5. Preserve ledger enrichment fields unless a replacement read model is designed and documented first.
6. Update this note together with code if whole-day write workflow, attendance scope enforcement, or ledger schema semantics change.
