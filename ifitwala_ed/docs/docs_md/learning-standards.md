---
title: "Learning Standards: Standards Catalog for Curriculum Taxonomy"
slug: learning-standards
category: Curriculum
doc_order: 3
version: "1.0.0"
last_change_date: "2026-03-12"
summary: "Catalog standards-framework rows for curriculum taxonomy, even though current task and unit flows do not yet link to this master directly."
seo_title: "Learning Standards: Standards Catalog for Curriculum Taxonomy"
seo_description: "Catalog standards-framework rows for curriculum taxonomy, even though current task and unit flows do not yet link to this master directly."
---

## Learning Standards: Standards Catalog for Curriculum Taxonomy

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.py`, `ifitwala_ed/curriculum/workspace/curriculum/curriculum.json`, `ifitwala_ed/students/doctype/tag_taxonomy/tag_taxonomy.json`
Test refs: None

`Learning Standards` is the standalone standards catalog for framework metadata such as framework name, subject area, strand, substrand, code, and description.

Current workspace note: this master exists, but `Learning Unit` does not currently link to it by field. Unit-level standards are still stored inline via `Learning Unit Standard Alignment`, and neither `Task` nor `Task Delivery` references `Learning Standards` directly.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`
Test refs: None

- Decide the framework naming convention first (`framework_name`, `framework_version`).
- Confirm the taxonomy scope first (`subject_area`, optional `program`, strand, substrand).
- Treat this as a reference catalog, not as a runtime grading or delivery record.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/curriculum/workspace/curriculum/curriculum.json`, `ifitwala_ed/students/doctype/tag_taxonomy/tag_taxonomy.json`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
Test refs: None

- The Curriculum workspace exposes `Learning Standards` as a top-level planning master.
- `Tag Taxonomy` can link to `Learning Standards`.
- The canonical curriculum contract treats this DocType as the standards catalog beside, not inside, the current task and delivery runtime.
- `Task` and `Task Delivery` do not read this DocType directly in the live schema.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.json`
Test refs: None

1. Create the standards catalog row with framework and taxonomy metadata.
2. Use it as the reference vocabulary for curriculum planning and future mastery-tracking work.
3. When documenting a `Learning Unit` today, re-enter the relevant framework metadata inside `Learning Unit Standard Alignment` rows because the current schema does not link those rows back to this master.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Learning Unit**](/docs/en/learning-unit/)
- [**Learning Unit Standard Alignment**](/docs/en/learning-unit-standard-alignment/)
- [**Lesson**](/docs/en/lesson/)
- [**Task**](/docs/en/task/)
- [**Task Delivery**](/docs/en/task-delivery/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`, `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.py`
Test refs: None

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/learning_standards/learning_standards.py`
- **Required fields (`reqd=1`)**: none at schema level.
- **Lifecycle hooks in controller**: none.

### Current Contract

- `Learning Standards` is a standalone master, not a child table.
- The controller is empty; the current contract is purely metadata storage.
- The live task stack does not dereference this master when creating `Task` or `Task Delivery` rows.

### Current Constraints To Preserve In Review

- Do not claim that `Learning Unit` rows point to `Learning Standards`; they currently do not.
- Do not claim that standards mastery is aggregated through this DocType in the current gradebook contract.
