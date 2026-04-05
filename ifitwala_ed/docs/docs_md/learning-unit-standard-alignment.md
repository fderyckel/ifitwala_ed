---
title: "Learning Unit Standard Alignment: Unit-Level Standards Snapshot"
slug: learning-unit-standard-alignment
category: Curriculum
doc_order: 4
version: "1.1.1"
last_change_date: "2026-04-05"
summary: "Record the standards coverage and alignment notes that a specific unit plan claims, stored inline as child rows on the parent unit."
seo_title: "Learning Unit Standard Alignment: Unit-Level Standards Snapshot"
seo_description: "Record the standards coverage and alignment notes that a specific learning unit claims, stored inline as child rows on the parent unit."
---

## Learning Unit Standard Alignment: Unit-Level Standards Snapshot

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.json`, `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.py`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`
Test refs: None

`Learning Unit Standard Alignment` is the child table that stores a unit's standards coverage claim. It captures framework metadata, code, description, coverage level, alignment strength, and notes directly inside the parent `Unit Plan`.

Current workspace note: these rows do not currently contain a `Link` to `Learning Standards`. They are an inline snapshot owned by the unit plan.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.json`
Test refs: None

- Create the parent `Unit Plan` first.
- Decide the standards framework details first because the row stores them inline.
- Treat this row as planning metadata only; it is not a runtime grading or delivery record.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
Test refs: None

- Stored only in `Unit Plan.standards`.
- Used to express planned standards alignment for a unit.
- Reaches the task stack only indirectly, through a `Task` choosing that `Unit Plan` as an optional curriculum anchor.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/assessment/doctype/task/task.json`
Test refs: None

1. Open the parent `Unit Plan`.
2. Add one or more `Learning Unit Standard Alignment` rows to `standards`.
3. Capture framework metadata, code, description, coverage, and notes for the unit.
4. Optionally author `Task` rows against that unit. The task inherits the unit link only; it does not copy or denormalize these child rows.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Unit Plan**](/docs/en/unit-plan/)
- [**Learning Standards**](/docs/en/learning-standards/)
- [**Task**](/docs/en/task/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.json`, `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.py`
Test refs: None

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.py`
- **DocType type**: child table (`istable = 1`)
- **Required fields (`reqd=1`)**: none at schema level.
- **Lifecycle hooks in controller**: none.

### Current Contract

- The child row belongs to `Unit Plan` only.
- Business logic remains on the parent doctype; the child controller is intentionally empty.
- The schema duplicates framework metadata inline instead of linking to `Learning Standards`.

### Current Constraints To Preserve In Review

- Do not add business rules to this child controller unless the parent contract is explicitly redesigned.
- Do not document this child row as a standalone reusable standards library item.
