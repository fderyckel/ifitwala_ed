---
title: "Program Course Prerequisite: Frozen Eligibility Thresholds"
slug: program-course-prerequisite
category: Curriculum
doc_order: 4
version: "1.0.0"
last_change_date: "2026-02-28"
summary: "Define program-scoped prerequisite rules with DNF grouping and immutable numeric threshold snapshots for auditable enrollment decisions."
seo_title: "Program Course Prerequisite: Frozen Eligibility Thresholds"
seo_description: "Define program-scoped prerequisite rules with DNF grouping and immutable numeric threshold snapshots for auditable enrollment decisions."
---

## Program Course Prerequisite: Frozen Eligibility Thresholds

`Program Course Prerequisite` stores prerequisite policy rows inside a `Program` and snapshots numeric thresholds used by enrollment evaluation.

## Before You Start (Prerequisites)

- Parent [**Program**](/docs/en/program/) and target `apply_to_course` must exist.
- Required prior courses must exist as [**Course**](/docs/en/course/) records.
- Program/course grade-scale context must be valid so threshold resolution can run.

## Why It Matters

- Uses DNF grouping (`prereq_group`) to model OR-of-AND prerequisite logic.
- Stores immutable threshold evidence (`grade_scale_used`, `min_numeric_score`) once resolved.
- Supports historical auditability: past eligibility decisions keep original numeric thresholds.

<Callout type="warning" title="Program-scoped only">
Catalog-level prerequisite fields on `Course` are intentionally blocked by enrollment services. Use this child table on `Program`.
</Callout>

## Rule Semantics

- Rows with same `prereq_group` are evaluated together (AND).
- Different groups are alternatives (OR).
- `apply_to_level` optionally narrows rule application by level.
- `required_course` is the evidence source.
- `min_grade` is translated to numeric once and stored in immutable snapshot fields.

## Worked Examples

### Example 1: Single Threshold

- `apply_to_course = Biology HL`
- `prereq_group = 1`
- `required_course = Science 10`
- `min_grade = B-`

On first save, controller resolves:

- `grade_scale_used` from `Course.grade_scale` (fallback `Program.grade_scale`)
- `min_numeric_score` from scale mapping

### Example 2: Alternative Paths

- Group 1:
  - `required_course = Math SL`, `min_grade = 5`
  - `required_course = Science 10`, `min_grade = 5`
- Group 2:
  - `required_course = Integrated Science`, `min_grade = 6`

Student passes if any full group passes.

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/program_course_prerequisite/program_course_prerequisite.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/program_course_prerequisite/program_course_prerequisite.py`
- **Required fields (`reqd=1`)**: none at schema level (controller enforces required threshold inputs).
- **Lifecycle hooks in controller**: `before_save`
- **Operational/public methods**: none.

- **DocType**: `Program Course Prerequisite` (`ifitwala_ed/curriculum/doctype/program_course_prerequisite/`)
- **Controller behavior**:
  - resolves `min_numeric_score` via `resolve_min_numeric_score(min_grade, grade_scale_used)`
  - resolves `grade_scale_used` from `required_course.grade_scale`, fallback `Program.grade_scale`
  - enforces immutability after first save for `grade_scale_used` and `min_numeric_score`
  - asserts both snapshot fields are present before save completes

### Permission Model

`Program Course Prerequisite` is a child table (`istable=1`) and follows parent [**Program**](/docs/en/program/) permissions.

## Related Docs

- [**Program**](/docs/en/program/)
- [**Program Course**](/docs/en/program-course/)
- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
