---
title: "Program Course: Catalog Row Inside a Program"
slug: program-course
category: Curriculum
doc_order: 3
version: "1.1.0"
last_change_date: "2026-03-11"
summary: "Configure how each course behaves inside a specific program, including required status, level, repeatability, maximum attempts, and the basket-group memberships defined on the parent Program."
seo_title: "Program Course: Catalog Row Inside a Program"
seo_description: "Configure how each course behaves inside a specific program, including required status, level, repeatability, maximum attempts, and the basket-group memberships defined on the parent Program."
---

## Program Course: Catalog Row Inside a Program

`Program Course` is the child-table row that binds a `Course` into one `Program` with program-specific constraints.

## Before You Start (Prerequisites)

- Create parent [**Program**](/docs/en/program/).
- Create the linked [**Course**](/docs/en/course/).
- Decide if this course is required and whether repeats are allowed in this specific program.
- If the course may satisfy one or more basket requirements, plan the related [**Basket Group**](/docs/en/basket-group/) memberships on the parent `Program`.

## Why It Matters

- Defines which courses belong to a program catalog.
- Carries repeat/attempt policy inputs used by enrollment validation.
- Feeds level and attempt-policy metadata used by enrollment validation.
- Pairs with `Program.course_basket_groups` when a course belongs to one or more basket requirements.

<Callout type="tip" title="Program-specific policy">
A course can behave differently across programs. `repeatable` and `max_attempts` are program-row settings, not global course settings.
</Callout>

## Where It Is Used Across the ERP

- Parent doctype: [**Program**](/docs/en/program/) (`courses` child table).
- Enrollment engine (`_get_program_courses` in `schedule/enrollment_engine.py`):
  - reads `repeatable`, `max_attempts`, and `level`
  - merges basket-group memberships from `Program.course_basket_groups`
  - enforces repeat/attempt eligibility per request
- Program Offering catalog helpers:
  - hydrate `required`
  - expose `basket_groups` lists derived from parent program mappings

## Worked Examples

### Example 1: Mandatory Core Course

- `course = English A`
- `required = 1`
- `level = Standard Level`
- `repeatable = 0`

Result: this row becomes a required part of the program catalog consumed by enrollment validation.

### Example 2: Optional Course With Multi-Group Eligibility

- `course = ESS`
- `required = 0`
- `repeatable = 1`
- parent `Program.course_basket_groups` rows:
  - `ESS -> Group 3 Humanities`
  - `ESS -> Group 4 Sciences`

Result: the program catalog still has one course row, while downstream offering and request flows know the course can satisfy more than one basket group.

## Related Docs

- [**Program**](/docs/en/program/)
- [**Basket Group**](/docs/en/basket-group/)
- [**Program Course Prerequisite**](/docs/en/program-course-prerequisite/)
- [**Program Offering Course**](/docs/en/program-offering-course/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/program_course/program_course.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/program_course/program_course.py`
- **Required fields (`reqd=1`)**:
  - `course` (`Link` -> `Course`)
- **Lifecycle hooks in controller**: none (child-table controller is `pass`)
- **Operational/public methods**: none

- **DocType**: `Program Course` (`ifitwala_ed/curriculum/doctype/program_course/`)
- **Child-table fields of interest**:
  - `required`
  - `credit_value`, `credit_unit`
  - `level`
  - `repeatable`
  - `max_attempts`
- **Important boundary**:
  - basket-group membership is no longer stored on the `Program Course` row itself
  - basket-group links live on parent `Program.course_basket_groups`

### Permission Model

`Program Course` is a child table (`istable=1`) and follows parent [**Program**](/docs/en/program/) permissions.
