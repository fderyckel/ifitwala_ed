---
title: "Course Enrollment Tool: Add One Course to Many Enrollments"
slug: course-enrollment-tool
category: Enrollment
doc_order: 7
version: "1.1.0"
last_change_date: "2026-03-11"
summary: "Add a selected offering course to many eligible students' Program Enrollments using server-side eligibility checks, term-window defaults, and basket-group safety rules."
seo_title: "Course Enrollment Tool: Add One Course to Many Enrollments"
seo_description: "Add a selected offering course to many eligible students' Program Enrollments using server-side eligibility checks, term-window defaults, and basket-group safety rules."
---

## Course Enrollment Tool: Add One Course to Many Enrollments

`Course Enrollment Tool` is a single doctype for assigning one selected course to multiple students who already have matching `Program Enrollment` context.

## Before You Start (Prerequisites)

- Select `program_offering`, `academic_year`, and `course`.
- Ensure selected course exists in the offering-course rows.
- Ensure target students already have active `Program Enrollment` in that offering and year.
- Use a basket-aware flow instead of this tool when the selected optional course belongs to more than one basket group.

## Why It Matters

- Prevents manual per-enrollment course row edits.
- Uses a server eligibility query to list only students without that course already.
- Preserves offering-bound course policy and term precedence when adding rows.

<Callout type="tip" title="Term precedence on insert">
When adding a course row: `Course.term_long + tool.term` wins first, then offering-course term bounds, then school AY term bounds fallback.
</Callout>

## Workflow

1. Choose `program_offering` (tool derives and locks `program`, sets `school`).
2. Choose `academic_year` (scoped to offering AY list).
3. Choose `course` (scoped to offering courses, AY-aware).
4. Load eligible students (server query excludes enrollments already containing the course).
5. Optionally add individual students manually in table.
6. Click `Add Course` to append rows to each target `Program Enrollment`.

## Worked Examples

### Example 1: Add Optional Course Mid-Year

- Offering: `IB DP 2026`
- AY: `AY-2026-2027`
- Course: `Visual Arts`
- Tool lists only students with matching enrollment and without existing `Visual Arts` row.
- Action appends `Program Enrollment Course(status=Enrolled)` on each eligible enrollment.

### Example 2: Basket-Aware Boundary

- Course: `ESS`
- Offering basket groups:
  - `ESS -> Group 3 Humanities`
  - `ESS -> Group 4 Sciences`

Result: the tool does not guess the credited basket group. It stops with a clear error so staff use a basket-aware workflow instead of creating ambiguous enrollment truth.

## Related Docs

- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Program Offering Course**](/docs/en/program-offering-course/)
- [**Basket Group**](/docs/en/basket-group/)
- [**Student Enrollment Playbook**](/docs/en/student-enrollment-playbook/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.py`
- **Required fields (`reqd=1`)**:
  - `program_offering` (`Link`)
  - `academic_year` (`Link`)
  - `course` (`Link`)
- **Lifecycle hooks in controller**: none beyond standard document behavior
- **Operational/public methods**:
  - document method `add_course_to_program_enrollment()` (whitelisted)
  - `fetch_eligible_students(...)`
  - `get_courses_for_offering(...)`
  - `list_offering_academic_years_desc(...)`

- **DocType**: `Course Enrollment Tool` (`ifitwala_ed/schedule/doctype/course_enrollment_tool/`)
- **Single doc**: `issingle = 1`
- **Server checks**:
  - selected AY must be in offering AY set
  - selected course must exist in offering-course map
  - rows are added only for existing active Program Enrollments in that offering and AY
  - duplicate course rows per enrollment are prevented
  - `required` is synced from offering semantics
  - single-group optional courses auto-fill `credited_basket_group`
  - multi-group optional courses are rejected so the tool cannot invent a basket assignment

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Schedule Maker` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | Yes | Yes |
