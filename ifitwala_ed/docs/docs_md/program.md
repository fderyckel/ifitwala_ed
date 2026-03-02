---
title: "Program: Curriculum Container and Enrollment Policy Anchor"
slug: program
category: Curriculum
doc_order: 1
version: "1.0.0"
last_change_date: "2026-02-28"
summary: "Define the academic program tree, its catalog courses, assessment model, and prerequisite policy foundation used by offerings and enrollment validation."
seo_title: "Program: Curriculum Container and Enrollment Policy Anchor"
seo_description: "Define the academic program tree, its catalog courses, assessment model, and prerequisite policy foundation used by offerings and enrollment validation."
---

## Program: Curriculum Container and Enrollment Policy Anchor

`Program` is the curriculum-level definition of academic intent. It is not a student enrollment record; it is the policy container used by offerings and enrollment validation.

## Before You Start (Prerequisites)

- Create all relevant [**Course**](/docs/en/course/) records first.
- Prepare the default [**Grade Scale**](/docs/en/grade-scale/) for program-level prerequisite resolution.
- Decide parent/child structure if you need a program tree (`NestedSet`).

## Why It Matters

- Defines program identity and hierarchy (`parent_program`, `is_group`, `lft`, `rgt`).
- Holds catalog rows (`Program Course`) and prerequisite rows (`Program Course Prerequisite`).
- Feeds [**Program Offering**](/docs/en/program-offering/) as the operational enrollment surface.
- Supplies baseline grade-scale intent for prerequisite threshold resolution.

<Callout type="tip" title="Locked enrollment alignment">
In enrollment architecture, Program is intent/structure. Enrollment truth is committed later in `Program Enrollment`.
</Callout>

## Where It Is Used Across the ERP

- [**Program Offering**](/docs/en/program-offering/) (`program` link).
- [**Program Enrollment**](/docs/en/program-enrollment/) denormalized program anchor.
- Enrollment engine (`ifitwala_ed/schedule/enrollment_engine.py`):
  - loads `Program Course` metadata (`repeatable`, `max_attempts`, `level`)
  - loads `Program Course Prerequisite` rows for DNF prerequisite checks
- Admissions/intent surfaces that collect program choice.

## Lifecycle and Linked Documents

1. Create program identity and (optional) tree parent.
2. Add `courses` rows ([**Program Course**](/docs/en/program-course/)).
3. Add prerequisite rows ([**Program Course Prerequisite**](/docs/en/program-course-prerequisite/)).
4. Configure assessment settings and `assessment_categories` rows.
5. Publish only when website fields are valid (`program_slug`, not archived).

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Keep only `Course.status = Active` rows in the program catalog.</Do>
  <Do>Use program prerequisites for enrollment policy, not course-level prerequisite fields.</Do>
  <Dont>Add duplicate course rows in `courses`.</Dont>
  <Dont>Publish archived programs or publish without `program_slug`.</Dont>
</DoDont>

## Worked Examples

### Example 1: DP Program Setup

- Program: `IB Diploma Programme`
- Catalog rows:
  - `Biology HL` (required)
  - `English A` (required)
  - `Visual Arts` (elective)
- Program prerequisite rows enforce minimum prior-course performance for selected HL courses.

### Example 2: Parent/Child Program Tree

- Parent program: `High School` (`is_group = 1`)
- Child programs: `Grade 11`, `Grade 12`
- Each child has its own catalog and prerequisite rows while preserving tree navigation.

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/program/program.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/program/program.py`
- **Required fields (`reqd=1`)**:
  - `program_name` (`Data`)
- **Lifecycle hooks in controller**: `validate`
- **Operational/public methods**:
  - `inherit_assessment_categories(program, overwrite=1)` (whitelisted)

- **DocType**: `Program` (`ifitwala_ed/curriculum/doctype/program/`)
- **Autoname**: `field:program_name`
- **Tree config**:
  - class `Program(NestedSet)`
  - `nsm_parent_field = parent_program`
- **Child tables**:
  - `courses` -> `Program Course`
  - `prerequisites` -> `Program Course Prerequisite`
  - `assessment_categories` -> `Program Assessment Category`
  - `program_coordinators` -> `Program Coordinator`
- **Validation guarantees** (`program.py`):
  - duplicate course rows are blocked
  - only Active courses can be added
  - publish guard (`archive` + `program_slug`) enforced
  - assessment-category duplicate and weight guards
  - when `points = 1`, active category weights must exist and total must be `<= 100`

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | No | No |
| `Curriculum Coordinator` | Yes | Yes | Yes | No |
| `Admission Officer` | Yes | Yes | No | No |
| `Admission Manager` | Yes | Yes | No | No |
| `Instructor` | Yes | No | No | No |
| `Academic Staff` | Yes | No | No | No |
| `Accreditation Visitor` | Yes | No | No | No |

## Related Docs

- [**Program Course**](/docs/en/program-course/)
- [**Program Course Prerequisite**](/docs/en/program-course-prerequisite/)
- [**Course**](/docs/en/course/)
- [**Program Offering**](/docs/en/program-offering/)
