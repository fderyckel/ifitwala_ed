---
title: "Learning Standards: Standards Catalog for Curriculum Taxonomy"
slug: learning-standards
category: Curriculum
doc_order: 3
version: "1.2.0"
last_change_date: "2026-04-07"
summary: "Catalog standards-framework rows for curriculum taxonomy while the live curriculum runtime still publishes unit standards inline and reporting still aggregates official outcome truth."
seo_title: "Learning Standards: Standards Catalog for Curriculum Taxonomy"
seo_description: "Catalog standards-framework rows for curriculum taxonomy while the live curriculum runtime still publishes unit standards inline and reporting still aggregates official outcome truth."
---

## Learning Standards: Standards Catalog for Curriculum Taxonomy

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.py`, `ifitwala_ed/curriculum/workspace/curriculum/curriculum.json`, `ifitwala_ed/students/doctype/tag_taxonomy/tag_taxonomy.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/assessment/term_reporting.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

`Learning Standards` is the standalone standards catalog for framework metadata such as framework name, subject area, strand, substrand, code, and description.

Current runtime note: this master exists, but `Unit Plan` does not currently link to it by field. Unit-level standards are still stored inline via `Learning Unit Standard Alignment`, the student learning space publishes those unit-alignment rows, and neither `Task` nor `Task Delivery` dereferences `Learning Standards` directly in the live schema.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`
Test refs: None

- Decide the framework naming convention first (`framework_name`, `framework_version`).
- Confirm the taxonomy scope first (`subject_area`, optional `program`, strand, substrand).
- Treat this as a reference catalog, not as a runtime grading or delivery record.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/curriculum/workspace/curriculum/curriculum.json`, `ifitwala_ed/students/doctype/tag_taxonomy/tag_taxonomy.json`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/assessment/term_reporting.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

- The Curriculum workspace exposes `Learning Standards` as a top-level planning master.
- `Tag Taxonomy` can link to `Learning Standards`.
- The canonical curriculum contract treats this DocType as the standards catalog behind, not inside, the current task and delivery runtime.
- `get_student_learning_space()` exposes standards from the unit-alignment child rows so students can see published learning goals in context.
- Term reporting and gradebook truth still aggregate from `Task Outcome` and `Task Outcome Criterion`, not directly from this standards master.
- `Task` and `Task Delivery` do not read this DocType directly in the live schema.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.json`
Test refs: None

1. Create the standards catalog row with framework and taxonomy metadata.
2. Use it as the reference vocabulary for curriculum planning and future mastery-tracking work.
3. When documenting a `Unit Plan` today, re-enter the relevant framework metadata inside `Learning Unit Standard Alignment` rows because the current schema does not link those rows back to this master.
4. Treat standards visibility and assessed mastery as separate layers today:
   - published unit goals come from the unit alignment rows
   - official reporting truth still comes from outcomes/criteria

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Unit Plan**](/docs/en/unit-plan/)
- [**Learning Unit Standard Alignment**](/docs/en/learning-unit-standard-alignment/)
- [**Task**](/docs/en/task/)
- [**Task Delivery**](/docs/en/task-delivery/)
- `ifitwala_ed/docs/assessment/05_term_reporting_notes.md`

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/assessment/term_reporting.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.py`
- **Required fields (`reqd=1`)**: none at schema level.
- **Lifecycle hooks in controller**: none.

### Current Contract

- `Learning Standards` is a standalone master, not a child table.
- The controller is empty; the current contract is purely metadata storage.
- The live task stack does not dereference this master when creating `Task` or `Task Delivery` rows.
- Student LMS surfaces standards through `Learning Unit Standard Alignment` serialization, not by direct master lookup.
- Reporting and gradebook mastery truth still derives from `Task Outcome` and `Task Outcome Criterion`.

### Current Constraints To Preserve In Review

- Do not claim that `Unit Plan` rows point to `Learning Standards`; they currently do not.
- Do not claim that standards mastery is aggregated through this DocType in the current gradebook or term-reporting contract.
