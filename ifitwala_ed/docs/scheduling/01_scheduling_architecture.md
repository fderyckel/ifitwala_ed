# Scheduling Architecture

## Status

Active. Canonical scheduling architecture note for runtime ownership boundaries, abstract-vs-materialized time rules, and the enrollment bridge into operational teaching execution.

Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/student_group_scheduling.py`
- `ifitwala_ed/schedule/student_group_employee_booking.py`
- `ifitwala_ed/schedule/schedule_utils.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- `ifitwala_ed/setup/doctype/meeting/meeting.py`
- `ifitwala_ed/school_settings/doctype/school_event/school_event.py`
- `ifitwala_ed/utilities/employee_booking.py`
- `ifitwala_ed/utilities/location_utils.py`
- `ifitwala_ed/stock/doctype/location_booking/location_booking.py`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/room_utilization.py`

Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`
- `ifitwala_ed/setup/doctype/meeting/test_meeting.py`
- `ifitwala_ed/school_settings/doctype/school_event/test_school_event.py`
- `ifitwala_ed/hr/doctype/employee_booking/test_employee_booking.py`
- `ifitwala_ed/stock/doctype/location_booking/test_location_booking.py`
- `ifitwala_ed/api/test_room_utilization.py`

This document is authoritative for:

- what scheduling owns
- what scheduling consumes from enrollment and calendars
- what remains abstract timetable intent
- what becomes operational free/busy truth
- which layers may answer conflict and availability questions

If code and this note disagree, stop and resolve the drift explicitly.

Related architecture:

- `docs/enrollment/02_school_calendar_architecture.md`
- `docs/enrollment/03_enrollment_architecture.md`
- `docs/enrollment/08_enrollment_scheduling_contract.md`
- `docs/scheduling/employee_booking_notes.md`
- `docs/scheduling/room_booking_notes.md`

---

## 1. Core Definition

### 1.1 What scheduling is

Scheduling in Ifitwala_Ed is the operational execution layer for time-bound teaching, meetings, events, rooms, and staff commitments.

It turns:

- academic time context
- instructional grouping
- block-based timetable intent
- concrete event records

into operational truth that calendars, conflict checks, and readiness gates can trust.

### 1.2 What scheduling is not

Scheduling is not:

- enrollment truth
- curriculum policy truth
- admissions truth
- a free/busy system inferred ad hoc from mixed sources

If a change tries to make scheduling infer academic entitlement from rosters, bookings, or attendance, that change is architecturally wrong.

---

## 2. Canonical Layer Stack

Status: Active
Code refs:
- `ifitwala_ed/schedule/schedule_utils.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/student_group_employee_booking.py`
- `ifitwala_ed/utilities/employee_booking.py`
- `ifitwala_ed/stock/doctype/location_booking/location_booking.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/hr/doctype/employee_booking/test_employee_booking.py`
- `ifitwala_ed/stock/doctype/location_booking/test_location_booking.py`

Scheduling is only correct when these layers stay separate:

| Layer | Responsibility | Must not be treated as |
| --- | --- | --- |
| `Academic Year` + `School Calendar` + `School Schedule` | calendar envelope, holidays, rotation, block definitions | enrollment truth or concrete bookings |
| `Student Group` | operational teaching/activity/pastoral group with roster and instructor set | a substitute for `Program Enrollment` |
| `Student Group Schedule` | abstract timetable intent by rotation day and block | real room or staff occupancy |
| `schedule_utils` / `student_group_scheduling` | schedule resolution, rotation expansion, timetable conflict helpers | operational booking truth |
| `Employee Booking` | concrete staff free/busy truth | room truth or abstract schedule |
| `Location Booking` | concrete room free/busy truth | employee truth or abstract schedule |
| `Meeting` / `School Event` | human-facing workflow documents | direct availability truth without projection |

The stack is intentionally split between abstract intent and materialized fact tables.

---

## 3. Abstract Time Versus Materialized Time

Status: Active
Code refs:
- `ifitwala_ed/schedule/schedule_utils.py`
- `ifitwala_ed/schedule/student_group_employee_booking.py`
- `ifitwala_ed/utilities/employee_booking.py`
- `ifitwala_ed/utilities/location_utils.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/api/test_room_utilization.py`

### 3.1 Abstract timetable intent

`Student Group Schedule` stores:

- rotation day
- block number
- instructor reference
- location reference
- stamped block times from `School Schedule`

That is timetable intent, not operational occupancy.

### 3.2 Materialized operational truth

Operational availability exists only after projection into:

- `Employee Booking` for staff
- `Location Booking` for rooms

Absence of a booking row means free for the relevant truth domain.

### 3.3 Non-negotiable read rule

Consumers that need real availability must read:

- `Employee Booking` for staff
- `Location Booking` for rooms

They must not:

- union raw `Student Group Schedule`
- infer rooms from employee rows
- infer staff availability from room rows
- recompute teaching occupancy client-side

---

## 4. Scheduling Ownership By Runtime Object

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- `ifitwala_ed/setup/doctype/meeting/meeting.py`
- `ifitwala_ed/school_settings/doctype/school_event/school_event.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`
- `ifitwala_ed/setup/doctype/meeting/test_meeting.py`
- `ifitwala_ed/school_settings/doctype/school_event/test_school_event.py`

### 4.1 `Student Group`

`Student Group` is the canonical operational teaching-group record.

It owns:

- rostered instructional grouping
- instructor assignment
- schedule-row validation
- internal timetable clash checks
- downstream booking rebuild triggers

It does not own:

- committed enrollment entitlement
- admissions progression
- portal selection workflow

### 4.2 `Program Offering`

`Program Offering` is a shared boundary object.

On the scheduling side, it owns:

- the operational school/program envelope that groups must sit inside
- activity-section readiness gating
- offering-scoped windows that scheduling consumers use

It does not own daily timetable rows or concrete free/busy truth.

### 4.3 `Meeting` and `School Event`

These are peer scheduling sources, not teaching groups.

They own:

- human-facing workflow
- participant and location intent
- projection into booking facts

They do not replace the booking fact tables for conflict reads.

---

## 5. Conflict Model

Status: Active
Code refs:
- `ifitwala_ed/schedule/student_group_scheduling.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/utilities/employee_booking.py`
- `ifitwala_ed/utilities/location_utils.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`
- `ifitwala_ed/api/test_room_utilization.py`

There are two conflict layers and they must not be collapsed.

### 5.1 Timetable-level clashes

`check_slot_conflicts(...)` handles abstract schedule collisions between `Student Group` rows at the same:

- rotation day
- block number

This covers:

- student double-booking across groups
- instructor double-booking across groups

It does not answer room free/busy for arbitrary datetimes.

### 5.2 Concrete datetime clashes

Concrete conflict checks happen only against materialized bookings:

- `find_employee_conflicts(...)` for staff
- `find_room_conflicts(...)` for rooms

`StudentGroup.validate_location_conflicts_absolute()` bridges the two by expanding abstract timetable rows into concrete datetimes before checking `Location Booking`.

`ProgramOffering.run_activity_preopen_readiness(...)` also relies on materialized bookings, not schedule inference, before opening activity windows.

---

## 6. Materialization Contract

Status: Active with known implementation drift
Code refs:
- `ifitwala_ed/schedule/student_group_employee_booking.py`
- `ifitwala_ed/setup/doctype/meeting/meeting.py`
- `ifitwala_ed/school_settings/doctype/school_event/school_event.py`
- `ifitwala_ed/stock/doctype/location_booking/location_booking.py`
- `ifitwala_ed/utilities/employee_booking.py`
Test refs:
- `ifitwala_ed/setup/doctype/meeting/test_meeting.py`
- `ifitwala_ed/school_settings/doctype/school_event/test_school_event.py`
- `ifitwala_ed/hr/doctype/employee_booking/test_employee_booking.py`
- `ifitwala_ed/stock/doctype/location_booking/test_location_booking.py`

### 6.1 Teaching materialization

`StudentGroup.on_update()` rebuilds bookings for active groups with schedule rows.

`rebuild_employee_bookings_for_student_group(...)` is the canonical teaching projection path. It:

1. resolves a bounded date window, defaulting to the Academic Year
2. expands timetable intent into concrete slots
3. upserts `Location Booking` rows for rooms
4. upserts `Employee Booking` rows for instructors
5. deletes obsolete rows only inside the bounded window

That is the cleanest runtime materialization path in the current codebase.

### 6.2 Meeting and school-event projection

`Meeting` and `School Event` also project into booking facts on write.

Current reality is mixed:

- room projection uses stable single-slot `Location Booking` identity
- employee projection in `Meeting` and `School Event` still clears source rows before recreating them

That reset behavior is important refactor context. Reads must still stay on the booking tables, and future cleanup should converge employee projection toward the same rebuild-safe semantics used by teaching materialization.

---

## 7. Enrollment Bridge

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/enrollment_request_utils.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/student_group_creation_tool.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`

Scheduling consumes enrollment truth; it does not create it.

Current implemented bridge points are:

- `StudentGroup.validate_students()` requires matching `Program Enrollment` rows for the selected offering and Academic Year
- course-based groups additionally require matching `Program Enrollment Course` rows for the selected course/term
- Desk student pickers use offering-first enrollment queries to populate eligible students for course and cohort groups

Current non-automation that must be documented explicitly:

- materializing a `Program Enrollment Request` does not auto-create `Student Group` rows
- `Program Enrollment` updates do not auto-assign or retire `Student Group` memberships
- `Program Enrollment Tool` handles requests and enrollments, not timetable/group generation
- `Student Group Creation Tool` currently has no server-owned orchestration logic in its controller

Any future automation between enrollment and scheduling must therefore be introduced explicitly and transactionally. It must not be documented as already implemented.

---

## 8. Multi-Tenant And Scope Rules

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- `ifitwala_ed/schedule/schedule_utils.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`

Scheduling scope must stay anchored to:

- explicit `Program Offering`
- explicit `Academic Year`
- resolved school ancestry
- explicit group mode (`Course`, `Cohort`, `Activity`, `Pastoral`, `Other`)

Refactors must preserve that:

- schedule resolution happens through allowed ancestor chains
- room/location checks respect school and calendar scope
- eligible student queries remain offering-first, not generic school-wide searches

Sibling isolation remains mandatory.

---

## 9. Anti-Patterns

The following are architectural drift:

- treating `Student Group` membership as committed enrollment truth
- using `Student Group Schedule` directly for room or staff free/busy
- inferring room truth from `Employee Booking`
- inferring staff truth from `Location Booking`
- letting portal self-service mutate `Student Group` or concrete bookings directly
- documenting schedule generation or group creation as automatic when the current runtime does not implement that orchestration
- adding new availability reads that bypass `find_employee_conflicts(...)` or `find_room_conflicts(...)`

---

## 10. Refactor Guardrails

When refactoring scheduling, preserve this order:

1. enrollment or event truth is committed in its own canonical model
2. scheduling resolves operational grouping and timetable intent
3. booking facts are materialized explicitly
4. read surfaces consume the fact tables

Do not collapse those stages into one vague “schedule record.”
