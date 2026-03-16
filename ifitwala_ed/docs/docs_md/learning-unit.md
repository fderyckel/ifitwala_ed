---
title: "Learning Unit: Planned Curriculum Container Inside a Course"
slug: learning-unit
category: Curriculum
doc_order: 5
version: "1.0.0"
last_change_date: "2026-03-12"
summary: "Plan a course-level unit with sequence, pedagogy, standards alignment, and lesson structure, then optionally anchor reusable tasks to it."
seo_title: "Learning Unit: Planned Curriculum Container Inside a Course"
seo_description: "Plan a course-level unit with sequence, pedagogy, standards alignment, and lesson structure, then optionally anchor reusable tasks to it."
---

## Learning Unit: Planned Curriculum Container Inside a Course

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.py`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.js`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: None (scaffold only: `ifitwala_ed/curriculum/doctype/learning_unit/test_learning_unit.py`)

`Learning Unit` is the planned-curriculum container inside a `Course`. It holds sequence, pedagogy, standards alignment, and reflections, and it is the highest-granularity curriculum record that `Task` can currently reference directly.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`
Test refs: None

- Create the parent `Course` first because `course` is required.
- Decide whether the unit also needs a `Program` reference and publication state.
- Prepare any standards metadata you want to record in the `standards` child table.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/curriculum/workspace/curriculum/curriculum.json`
Test refs: None

- Parent context for [**Lesson**](/docs/en/lesson/) rows.
- Optional curriculum anchor for [**Task**](/docs/en/task/) through `Task.learning_unit`.
- Surfaced as a top-level planning DocType in the Curriculum workspace.
- The live `Task Delivery` schema does not point to `Learning Unit` directly; runtime teaching context starts later at [**Lesson Instance**](/docs/en/lesson-instance/).

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.py`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: None (scaffold only: `ifitwala_ed/curriculum/doctype/learning_unit/test_learning_unit.py`)

1. Create the unit with `unit_name` and required `course`.
2. Capture pedagogy, content, skills, concepts, misconceptions, and publication state.
3. Add `Learning Unit Standard Alignment` rows and any planning reflections.
4. Add ordered `Lesson` rows under the unit.
5. Optionally anchor reusable `Task` rows to the unit; delivery and assessment happen later through `Task Delivery`.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Course**](/docs/en/course/)
- [**Learning Standards**](/docs/en/learning-standards/)
- [**Learning Unit Standard Alignment**](/docs/en/learning-unit-standard-alignment/)
- [**Lesson**](/docs/en/lesson/)
- [**Task**](/docs/en/task/)
- [**Task Delivery**](/docs/en/task-delivery/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.py`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.js`
Test refs: None (scaffold only: `ifitwala_ed/curriculum/doctype/learning_unit/test_learning_unit.py`)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.py`
- **Desk client script**: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.js`
- **Required fields (`reqd=1`)**:
  - `unit_name` (`Data`)
  - `course` (`Link` -> `Course`)
- **Child tables**:
  - `standards` (`Learning Unit Standard Alignment`)
  - `reflections` (`Curriculum Planning Reflection`)
- **Lifecycle hooks in controller**:
  - `before_insert`
  - `before_save`
- **Operational/public methods**:
  - `reorder_learning_units(course, unit_names)` (whitelisted)

### Current Contract

- `Learning Unit` owns ordering within a course through `unit_order`.
- `learning_unit.py` auto-assigns or repairs `unit_order` collisions in steps of 10.
- `task.py` validates that any `Task.learning_unit` belongs to the same course as `Task.default_course`.
- `learning_unit.js` provides lesson-list and lesson-reorder actions from the unit form.

### Current Constraints To Preserve In Review

- The unit is a planning record, not a teaching event and not a grading fact table.
- `Task Delivery` does not point back to `Learning Unit` directly in the current runtime contract.
- `learning_unit.js` calls `lesson.reorder_lessons`, but the current `lesson.py` does not define that server method.
