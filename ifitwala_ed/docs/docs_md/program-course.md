---
title: "Program Course: Catalog Row Inside a Program"
slug: program-course
category: Curriculum
doc_order: 3
version: "1.0.0"
last_change_date: "2026-02-28"
summary: "Configure how each course behaves inside a specific program, including mandatory/elective role, level, repeatability, and maximum attempts."
seo_title: "Program Course: Catalog Row Inside a Program"
seo_description: "Configure how each course behaves inside a specific program, including mandatory/elective role, level, repeatability, and maximum attempts."
---

## Program Course: Catalog Row Inside a Program

`Program Course` is the child-table row that binds a `Course` into one `Program` with program-specific constraints.

## Before You Start (Prerequisites)

- Create parent [**Program**](/docs/en/program/).
- Create the linked [**Course**](/docs/en/course/).
- Decide if this course is mandatory and whether repeats are allowed in this specific program.

## Why It Matters

- Defines which courses belong to a program catalog.
- Carries repeat/attempt policy inputs used by enrollment validation.
- Feeds level and attempt-policy metadata used by enrollment validation.

<Callout type="tip" title="Program-specific policy">
A course can behave differently across programs. `repeatable` and `max_attempts` are program-row settings, not global course settings.
</Callout>

## Where It Is Used Across the ERP

- Parent doctype: [**Program**](/docs/en/program/) (`courses` child table).
- Enrollment engine (`_get_program_courses` in `schedule/enrollment_engine.py`):
  - reads `repeatable`, `max_attempts`, `level`, `category`
  - enforces repeat/attempt eligibility per request
- Program Offering course curation via catalog helpers.

## Worked Examples

### Example 1: Mandatory Core Course

- `course = English A`
- `required = 1`
- `level = Standard Level`
- `repeatable = 0`

Result: this row becomes part of the program catalog context consumed by enrollment validation.

### Example 2: Elective With Attempt Limit

- `course = Visual Arts`
- `required = 0`
- `repeatable = 1`
- `max_attempts = 2`

Result: enrollment engine allows retake attempts up to policy limit and blocks requests beyond `max_attempts`.

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/program_course/program_course.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/program_course/program_course.py`
- **Required fields (`reqd=1`)**:
  - `course` (`Link` -> `Course`)
- **Lifecycle hooks in controller**: none (child-table controller is `pass`).
- **Operational/public methods**: none.

- **DocType**: `Program Course` (`ifitwala_ed/curriculum/doctype/program_course/`)
- **Child-table fields of interest**:
  - `required`
  - `credit_value`, `credit_unit`
  - `category` (`Course Group`)
  - `level`
  - `repeatable`
  - `max_attempts`

### Permission Model

`Program Course` is a child table (`istable=1`) and follows parent [**Program**](/docs/en/program/) permissions.

## Related Docs

- [**Program**](/docs/en/program/)
- [**Program Course Prerequisite**](/docs/en/program-course-prerequisite/)
- [**Program Offering Course**](/docs/en/program-offering-course/)
