---
title: "Learning Unit Standard Alignment: Unit-Level Standards Snapshot"
slug: learning-unit-standard-alignment
category: Curriculum
doc_order: 4
version: "1.2.1"
last_change_date: "2026-04-23"
summary: "Record the standards coverage and alignment notes that a specific unit plan claims, using a validated link to the approved standards catalog plus a unit-owned inline snapshot."
seo_title: "Learning Unit Standard Alignment: Unit-Level Standards Snapshot"
seo_description: "Record the standards coverage and alignment notes that a specific learning unit claims, stored inline as child rows on the parent unit."
---

## Learning Unit Standard Alignment: Unit-Level Standards Snapshot

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.json`, `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.py`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/planning.py`
Test refs: `ifitwala_ed/curriculum/test_planning_unit.py`, `ifitwala_ed/curriculum/doctype/unit_plan/test_unit_plan.py`, `ifitwala_ed/patches/test_backfill_unit_plan_standard_links.py`

`Learning Unit Standard Alignment` is the child table that stores a unit's standards coverage claim. Each row now selects an existing `Learning Standards` record, then stores a validated inline snapshot of the approved framework metadata, code, and description inside the parent `Unit Plan`.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/learning_unit_standard_alignment/learning_unit_standard_alignment.json`
Test refs: None

- Create the parent `Unit Plan` first.
- Ensure the required standards already exist in `Learning Standards` because teachers now select from the approved catalog instead of typing the standard identity from scratch.
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
3. Select the existing `Learning Standards` row, then capture unit-specific coverage, strength, and notes.
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
- The schema now stores both:
  - a `Learning Standards` link for identity and validation
  - a unit-owned snapshot of the approved metadata for stable downstream reads
- Runtime save paths require the `learning_standard` link itself to resolve to an existing `Learning Standards` record; legacy broken links are remediated through the one-shot patch `ifitwala_ed.patches.backfill_unit_plan_standard_links` instead of being rebuilt during unit validation.

### Current Constraints To Preserve In Review

- Do not add business rules to this child controller unless the parent contract is explicitly redesigned.
- Do not treat free-typed framework metadata as valid. The parent `Unit Plan` now validates that every standards row resolves to an existing `Learning Standards` record.
