---
title: "Program Offering Course: Delivery Window and Capacity Row"
slug: program-offering-course
category: Enrollment
doc_order: 3
version: "1.1.0"
last_change_date: "2026-03-11"
summary: "Define per-course delivery windows, required status, grade-scale overrides, and capacity controls inside one Program Offering; basket-group memberships are carried on the parent offering."
seo_title: "Program Offering Course: Delivery Window and Capacity Row"
seo_description: "Define per-course delivery windows, required status, grade-scale overrides, and capacity controls inside one Program Offering; basket-group memberships are carried on the parent offering."
---

## Program Offering Course: Delivery Window and Capacity Row

`Program Offering Course` is the per-course operational row inside a Program Offering. It controls when that course is offered and how capacity should be interpreted.

## Before You Start (Prerequisites)

- Parent [**Program Offering**](/docs/en/program-offering/) must exist with AY spine.
- Linked [**Course**](/docs/en/course/) must be available.
- Decide if this row is required, capacity-limited, or a non-catalog exception.
- If the course may satisfy one or more basket requirements, create the related parent `offering_course_basket_groups` rows on the offering.

## Why It Matters

- Enrollment engine reads these rows as the offered course universe for request validation.
- Capacity checks and seat-risk calculations use per-row `capacity`.
- Date and term windows determine whether a course is valid for a selected enrollment AY and term.

<Callout type="info" title="Window precedence">
Effective delivery window is derived from AY bounds, optionally narrowed by start/end terms, then optionally overridden by explicit `from_date`/`to_date` (validated by parent offering rules).
</Callout>

## Row Semantics

- Identity and policy:
  - `course`, `required`, optional `grade_scale`
  - for catalog-derived rows, `required` defaults from the matching `Program Course` row
  - basket-group memberships are not stored on this child row; they live on parent `Program Offering.offering_course_basket_groups`
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

Result: the row inherits AY boundaries and is treated as individually required by request and enrollment validation.

### Example 2: Optional Course With Basket Eligibility

- `course = ESS`
- `required = 0`
- `start_academic_term = Term-1`
- `end_academic_term = Term-2`
- parent offering basket-group rows:
  - `ESS -> Group 3 Humanities`
  - `ESS -> Group 4 Sciences`

Result: the request and enrollment layers require an explicit basket-group selection when ESS is chosen in a multi-group flow.

## Related Docs

- [**Program Offering**](/docs/en/program-offering/)
- [**Basket Group**](/docs/en/basket-group/)
- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Program Enrollment**](/docs/en/program-enrollment/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/program_offering_course/program_offering_course.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/program_offering_course/program_offering_course.py`
- **Required fields (`reqd=1`)**: none at schema level
- **Lifecycle hooks in controller**: none (child-table controller is `pass`)
- **Operational/public methods**: none

- **DocType**: `Program Offering Course` (`ifitwala_ed/schedule/doctype/program_offering_course/`)
- **Enforced by parent `Program Offering` validation**:
  - start/end AY must belong to the offering AY spine
  - term AY and school ancestry checks
  - date ordering checks and head-window constraints
  - course must be in program catalog unless explicit `non_catalog` exception path is used
  - basket-group semantics come from parent `offering_course_basket_groups`, not from a field on this row

### Permission Model

`Program Offering Course` is a child table (`istable=1`) and follows parent [**Program Offering**](/docs/en/program-offering/) permissions.
