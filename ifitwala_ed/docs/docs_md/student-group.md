---
title: "Student Group: Operational Teaching Group Contract"
slug: student-group
category: Schedule
doc_order: 1
version: "1.0.3"
last_change_date: "2026-03-29"
summary: "Define the operational class, cohort, activity, or pastoral group used for rostering, instructor assignment, schedule intent, attendance scope, and downstream teaching materialization."
seo_title: "Student Group: Operational Teaching Group Contract"
seo_description: "Define the operational class, cohort, activity, or pastoral group used for rostering, instructor assignment, schedule intent, and attendance scope."
---

## Student Group: Operational Teaching Group Contract

`Student Group` is the operational teaching-group record for the Schedule domain. It binds roster, instructor set, attendance scope, and timetable intent to a specific `Program Offering` and `Academic Year`, then feeds downstream scheduling, attendance, and teaching workflows.

Current workspace note: when a selected Program Offering has exactly one Academic Year in its offering spine, the Student Group form now auto-fills `academic_year`. Schedule rows also default `instructor` when exactly one instructor is attached to the group, and save-time validation warns, without blocking, only for course-based Student Groups that land in non-instructional or mismatched schedule blocks.

## Before You Start (Prerequisites)

- Create the parent [**Program Offering**](/docs/en/program-offering/) first.
- Create the target `Academic Year`, and create `Term` when the group is term-scoped.
- Decide the grouping mode up front:
  - `Course`
  - `Cohort`
  - `Activity`
  - `Pastoral`
- For course groups, confirm the selected `Course` is actually offered in the selected offering and Academic Year.
- For cohort groups, confirm the target cohort exists on eligible `Program Enrollment` rows.
- Prepare the `Student Group Instructor` roster before bulk block booking if you want schedule rows to use only valid instructors.

## Why It Matters

- It is the canonical rostered class identity used by teaching workflows.
- It is the source of abstract timetable intent through `Student Group Schedule`.
- It scopes instructor conflict checks, location conflict checks, and employee-booking materialization.
- It controls whether attendance is per block, whole day, or disabled.
- It is the bridge between enrollment context and real teaching context for downstream records.

## Where It Is Used Across the ERP

- [**Task Delivery**](/docs/en/task-delivery/) targets a specific `Student Group`.
- [**Lesson Instance**](/docs/en/lesson-instance/) uses `Student Group` as the taught-session context.
- Scheduling materialization rebuilds `Employee Booking` rows from active Student Group schedule rows.
- Student-group schedule changes invalidate meeting-date projections and related teaching schedule context.
- Instructor log rebuilding and referral/access sync use the group’s instructor and student membership tables.

## Lifecycle and Linked Documents

1. Create the group with `program_offering`, `group_based_on`, and `student_group_abbreviation`.
   If the selected Program Offering has exactly one `offering_academic_years` row, Desk auto-fills `academic_year`.
2. Add the mode-specific anchor:
   - `course` for `Course`
   - `cohort` for `Cohort`
   - no extra required selector for `Activity` or `Pastoral`
3. Add `students` and `instructors`.
4. Optionally choose `school_schedule`, or let validation auto-resolve the correct schedule for `Course` and `Activity` groups.
5. Add `student_group_schedule` rows manually or through the quick-add block dialog.
6. Save the group:
   - names and title are derived from abbreviation plus AY, term, or cohort
   - schedule row times are stamped from `School Schedule Block`
   - overlap, capacity, and room checks run
   - for course-based groups only, non-instructional or mismatched schedule blocks raise warnings only
7. On later saves, active-student changes, instructor changes, and schedule changes trigger downstream sync and materialization updates.

### Naming Rules

- `Course` and `Activity` groups use `student_group_abbreviation + "/" + term` when `term` exists, otherwise `student_group_abbreviation + "/" + academic_year`.
- `Cohort` groups use `student_group_abbreviation + "/" + cohort`.
- Other group modes use `student_group_abbreviation`.

### Attendance Scope

`attendance_scope` currently supports:

- `Per Block`
- `Whole Day`
- `None`

`Whole Day` groups are treated as homeroom-style attendance groups by the controller property `is_whole_day_group`.

## Related Docs

- [**Program Offering**](/docs/en/program-offering/)
- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Task Delivery**](/docs/en/task-delivery/)
- [**Lesson Instance**](/docs/en/lesson-instance/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/student_group/student_group.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- **Client script**: `ifitwala_ed/schedule/doctype/student_group/student_group.js`
- **Supporting scheduling helper**: `ifitwala_ed/schedule/student_group_scheduling.py`
- **Required fields (`reqd=1`)**:
  - `program_offering` (`Link` -> `Program Offering`)
  - `academic_year` (`Link` -> `Academic Year`)
  - `group_based_on` (`Select`)
  - `student_group_abbreviation` (`Data`)
- **Key child tables**:
  - `students` -> `Student Group Student`
  - `instructors` -> `Student Group Instructor`
  - `student_group_schedule` -> `Student Group Schedule`
- **Lifecycle hooks in controller**:
  - `autoname`
  - `validate`
  - `before_save`
  - `after_save`
  - `on_update`
  - `on_trash`
  - `after_delete`
- **Client-side Desk affordances**:
  - AY, school, course, and schedule link queries are offering-aware
  - selecting `program_offering` auto-fills `academic_year` when exactly one offering AY exists
  - student bulk-add is enabled for non-activity flows
  - schedule row instructor choices are constrained to the group’s instructor table
  - blank schedule rows default the instructor when exactly one instructor exists

### Current Contract

- `validate()` enforces:
  - Academic Year membership inside the selected Program Offering spine
  - school ancestry rules
  - course scoping for course-based groups
  - roster integrity and duplicate-student protection
  - internal student and instructor rotation/block clash checks
  - cross-group instructor and student overlap checks
  - location capacity rules
  - schedule-row validation against the resolved `School Schedule`
- `validate_students()` enforces enabled-student membership and offering-aligned enrollment integrity.
- `_get_school_schedule()` is the canonical schedule resolver. It validates an explicit `school_schedule` when present, otherwise resolves one from the allowed school ancestry chain for the selected Academic Year.
- `_validate_schedule_rows()` stamps `from_time` and `to_time` from `School Schedule Block`, enforces instructor membership, and emits advisory warnings for:
  - course-based groups scheduled in non-instructional blocks such as recess, assembly, and lunch-style blocks
  - course-based groups scheduled in block types that do not match course teaching, for example a course group scheduled in an activity block
- `validate_location_conflicts_absolute()` expands abstract schedule rows into real datetimes via rotation dates, then checks governed room conflicts against materialized bookings.
- `before_save()` and `after_save()` compute change deltas for students, instructors, and schedule rows so downstream sync stays bounded.
- `on_update()` rebuilds employee bookings only for active groups that actually have schedule rows.

### Operational Queries and Public Methods

- `get_students(...)`
  returns eligible students for the current grouping mode and offering/AY context
- `allowed_school_query(...)`
  narrows school options to the AY and Program Offering intersection
- `fetch_students(...)`
  powers Desk student picking with offering-first enrollment logic
- `offering_ay_query(...)`
  returns Academic Years attached to the selected Program Offering
- `offering_course_query(...)`
  returns Program Offering courses valid for the selected AY and optional term
- `schedule_picker_query(...)`
  returns School Schedules for the selected AY inside the allowed school ancestry chain

### Permission and Visibility Notes

- Full create/write/delete access in schema currently exists for:
  - `System Manager`
  - `Schedule Maker`
  - `Academic Admin`
  - `Academic Assistant`
  - `Curriculum Coordinator`
- Read-only or limited schema access currently exists for:
  - `Instructor`
  - `Admission Officer`
  - `Academic Staff`
  - `Accreditation Visitor`
- `get_permission_query_conditions()` adds server-side list scoping:
  - `Instructor` users are constrained to groups where they appear in `Student Group Instructor`
  - `Student` users are constrained to groups where they appear in `Student Group Student`

### Current Constraints To Preserve In Review

- `Student Group Schedule` remains abstract intent. Concrete room and employee bookings come from controlled materialization flows.
- Child-table workflow logic must remain in the parent `Student Group` controller.
- Any future change to schedule resolution, block booking warnings, or materialization triggers must be updated together with:
  - this page
  - [**Program Offering**](/docs/en/program-offering/)
  - [**Task Delivery**](/docs/en/task-delivery/)
  - [**Lesson Instance**](/docs/en/lesson-instance/)
