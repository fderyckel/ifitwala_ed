---
title: "Instructor: Teaching Identity Linked to Employee"
slug: instructor
category: Schedule
doc_order: 2
version: "1.1.0"
last_change_date: "2026-04-02"
summary: "Link an employee with user identity, school scope, and durable student-group teaching history so schedule, class, and visibility flows can treat them as an instructor."
seo_title: "Instructor: Teaching Identity Linked to Employee"
seo_description: "Link an employee with user identity, school scope, and teaching context so schedule and class workflows can treat them as an instructor."
---

## Instructor: Teaching Identity Linked to Employee

`Instructor` is the Schedule-domain teaching identity for a staff member. It is a controlled projection of `Employee`, not a free-form person record, and it is the object other schedule flows use when assigning staff to `Student Group` teaching work.

## Before You Start (Prerequisites)

- Create the linked `Employee` first.
- Ensure the employee has a valid `user_id`; the controller blocks Instructor creation without it.
- Ensure the employee is anchored to the correct school context if you rely on school-scoped visibility.

## Why It Matters

- It is the staff identity used by `Student Group Instructor`.
- It drives instructor-scoped visibility in schedule flows.
- It grants and removes the `Instructor` role on the linked `User` according to status and linked identity changes.
- It maintains the read-only `Instructor Log` history of Student Group involvement across course, activity, and pastoral teaching assignments.

## Where It Is Used Across the ERP

- `Student Group Instructor` links directly to `Instructor`.
- `Student Group` schedule and staffing flows constrain schedule rows to valid instructors on the group.
- Instructor-specific list visibility and self-read access are enforced through the Instructor permission helpers.

## Lifecycle and Linked Documents

1. Create the `Instructor` from an `Employee`.
2. On save, the controller syncs:
   - `linked_user_id`
   - `gender`
   - `instructor_name`
   - `instructor_image`
3. The controller reconciles `instructor_log` against `Student Group Instructor` links so current assignments stay open and ended assignments stay visible as history.
4. On insert and update, the linked `User` gains or loses the `Instructor` role depending on `status` and linked user changes.

## Related Docs

- [**Student Group**](/docs/en/student-group/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/instructor/instructor.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/instructor/instructor.py`
- **Required fields (`reqd=1`)**:
  - `employee` (`Link` -> `Employee`)
- **Key computed fields**:
  - `linked_user_id`
  - `gender`
  - `instructor_name`
  - `instructor_image`
- **Key child table**:
  - `instructor_log` -> `Instructor Log`
- **Lifecycle hooks in controller**:
  - `autoname`
  - `validate`
  - `before_save`
  - `after_insert`
  - `on_update`

### Current Contract

- `autoname()` uses `Employee.employee_full_name`.
- `validate()` syncs employee-derived fields and blocks duplicate employee links.
- `before_save()` reconciles the persisted `instructor_log` history against current Student Group assignments.
- `after_insert()` grants the `Instructor` role only when the instructor is not inactive.
- `on_update()` moves or removes the `Instructor` role when `linked_user_id` or `status` changes.
- `sync_instructor_logs(...)` is the bounded history-sync helper used when Student Group instructor membership changes.

### Operational Queries and Public Methods

- `get_instructor_log(instructor)`
  reconciles and returns the latest instructor log payload for Desk form display
- `instructor_employee_query(...)`
  returns employee choices eligible to become or remain an instructor while preserving school scoping and current-row editing

### Permission and Visibility Notes

- Full create/write/delete access in schema currently exists for:
  - `System Manager`
  - `Schedule Maker`
  - `Academic Admin`
  - `Academic Assistant`
- Read-only schema access currently exists for:
  - `Academic Staff`
  - `Instructor`
  - `Student`
  - `Accreditation Visitor`
- `get_permission_query_conditions(user)` and `has_permission(...)` additionally enforce school-scoped visibility plus self-read access for the linked user.

### Current Constraints To Preserve In Review

- `Instructor` is employee-derived. It must not drift into a second source of truth for user identity fields.
- `instructor_log` is server-owned history derived from Student Group assignment data and should stay non-editable.
- Current rows are inferred from active `Student Group Instructor` links; closed rows preserve ended involvement.
- Legacy deleted assignment rows from before this history contract cannot be reconstructed unless another durable audit source exists.
- Any role-management change here must be reviewed together with Student Group staffing flows.
