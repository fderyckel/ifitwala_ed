---
title: "Program Offering Course: Delivery Window and Capacity Row"
slug: program-offering-course
category: Enrollment
doc_order: 3
version: "1.0.0"
last_change_date: "2026-02-28"
summary: "Define per-course delivery windows, required/elective role, and capacity controls inside one Program Offering."
seo_title: "Program Offering Course: Delivery Window and Capacity Row"
seo_description: "Define per-course delivery windows, required/elective role, and capacity controls inside one Program Offering."
---

## Program Offering Course: Delivery Window and Capacity Row

`Program Offering Course` is the per-course operational row inside a Program Offering. It controls when that course is offered and how capacity should be interpreted.

## Before You Start (Prerequisites)

- Parent [**Program Offering**](/docs/en/program-offering/) must exist with AY spine.
- Linked [**Course**](/docs/en/course/) must be available.
- Decide if this row is required, elective, capacity-limited, or a non-catalog exception.

## Why It Matters

- Enrollment engine reads these rows as the basket universe for request validation.
- Capacity checks and seat-risk calculations use per-row `capacity`.
- Date/term windows determine whether a course is valid for a selected enrollment AY/term.

<Callout type="info" title="Window precedence">
Effective delivery window is derived from AY bounds, optionally narrowed by start/end terms, then optionally overridden by explicit `from_date`/`to_date` (validated by parent offering rules).
</Callout>

## Row Semantics

- Identity/policy:
  - `course`, `required`, `elective_group`, optional `grade_scale`
- Capacity controls:
  - `capacity`, `waitlist_enabled`, `reserved_seats`
- Delivery window:
  - `start_academic_year`, `end_academic_year`
  - optional `start_academic_term`, `end_academic_term`
  - optional explicit `from_date`, `to_date`
- Exception controls:
  - `non_catalog`, `exception_reason`

## Worked Examples

### Example 1: Required Full-Year Course

- `course = English A`
- `required = 1`
- `start_academic_year = AY-2026-2027`
- `end_academic_year = AY-2026-2027`
- No explicit dates

Result: row inherits AY boundaries (and head-window clamping if offering head dates are narrower).

### Example 2: Term-Limited Elective

- `course = Visual Arts`
- `required = 0`
- `start_academic_term = Term-1`
- `end_academic_term = Term-2`
- `capacity = 20`

Result: request/enrollment validation only treats this course as offered within the mapped term window.

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/program_offering_course/program_offering_course.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/program_offering_course/program_offering_course.py`
- **Required fields (`reqd=1`)**: none at schema level.
- **Lifecycle hooks in controller**: none (child-table controller is `pass`).
- **Operational/public methods**: none.

- **DocType**: `Program Offering Course` (`ifitwala_ed/schedule/doctype/program_offering_course/`)
- **Enforced by parent `Program Offering` validation**:
  - start/end AY must belong to offering AY spine
  - term AY and school ancestry checks
  - date ordering checks and head-window constraints
  - course must be in program catalog unless explicit `non_catalog` exception path is used

### Permission Model

`Program Offering Course` is a child table (`istable=1`) and follows parent [**Program Offering**](/docs/en/program-offering/) permissions.

## Related Docs

- [**Program Offering**](/docs/en/program-offering/)
- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Program Enrollment**](/docs/en/program-enrollment/)
