---
title: "Lesson: Ordered Planned Teaching Segment Within a Unit"
slug: lesson
category: Curriculum
doc_order: 6
version: "1.1.0"
last_change_date: "2026-04-01"
summary: "Define a planned lesson within a learning unit, add lesson activities, and optionally use the lesson as the deepest curriculum anchor on a reusable task."
seo_title: "Lesson: Ordered Planned Teaching Segment Within a Unit"
seo_description: "Define a planned lesson within a learning unit, add lesson activities, and optionally use the lesson as the deepest curriculum anchor on a reusable task."
---

## Lesson: Ordered Planned Teaching Segment Within a Unit

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.py`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.js`
Test refs: None (scaffold only: `ifitwala_ed/curriculum/doctype/lesson/test_lesson.py`)

`Lesson` is the ordered planned teaching segment inside a `Learning Unit`. It can hold type, date, duration, and a child table of `Lesson Activity` rows.

Current workspace note: `Lesson` remains a planned-curriculum record during the replatform. Runtime class delivery now lives in [**Class Session**](/docs/en/class-session/), and `Task Delivery` no longer stores `lesson_instance`.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`
Test refs: None

- Create the parent `Learning Unit` first because `learning_unit` is required.
- Decide whether to populate the optional `course` field or rely on the parent unit as the primary anchor.
- Prepare any `Lesson Activity` rows you want to capture inside the lesson.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.js`
Test refs: None

- Child of [**Learning Unit**](/docs/en/learning-unit/).
- Optional curriculum anchor for [**Task**](/docs/en/task/) through `Task.lesson`.
- Legacy planned anchor that may still help educators map shared lesson guidance to a live [**Class Session**](/docs/en/class-session/), though the live session model no longer depends on it.
- Read and ordered from the Learning Unit form helpers in `learning_unit.js`.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: None (scaffold only: `ifitwala_ed/curriculum/doctype/lesson/test_lesson.py`)

1. Create the lesson under a `Learning Unit` with required `title`.
2. Set planning metadata such as `lesson_type`, `start_date`, `duration`, and `is_published`.
3. Add `Lesson Activity` rows to break the lesson into pedagogical steps.
4. Optionally anchor reusable `Task` rows to this lesson. Runtime delivery then happens separately through `Task Delivery`.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Learning Unit**](/docs/en/learning-unit/)
- [**Lesson Activity**](/docs/en/lesson-activity/)
- [**Class Session**](/docs/en/class-session/)
- [**Task**](/docs/en/task/)
- [**Task Delivery**](/docs/en/task-delivery/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.py`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: None (scaffold only: `ifitwala_ed/curriculum/doctype/lesson/test_lesson.py`)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/lesson/lesson.py`
- **Required fields (`reqd=1`)**:
  - `learning_unit` (`Link` -> `Learning Unit`)
  - `title` (`Data`)
- **Child tables**:
  - `lesson_activities` (`Lesson Activity`)
- **Lifecycle hooks in controller**: none.

### Current Contract

- `Lesson` is a planned record; the controller is currently empty.
- `Task._validate_curriculum_alignment()` checks that any selected lesson belongs to the selected learning unit and course context before a task is saved.
- If `Lesson.course` is blank, `Task` validation can still derive course alignment through the lesson's linked learning unit.

### Current Constraints To Preserve In Review

- Do not document lesson ordering as server-enforced beyond the stored `lesson_order` field; there is no live `reorder_lessons()` server implementation in `lesson.py`.
- Do not document `Lesson` as the runtime delivery row. That role now belongs to `Class Session`, with `Task Delivery` as optional class-assigned work.
