---
title: "Lesson: Ordered Planned Teaching Segment Within a Unit"
slug: lesson
category: Curriculum
doc_order: 6
version: "1.3.0"
last_change_date: "2026-04-02"
summary: "Define a planned lesson within a unit plan, add thin lesson activities, and optionally use the lesson as the deepest curriculum anchor on a reusable task."
seo_title: "Lesson: Ordered Planned Teaching Segment Within a Unit"
seo_description: "Define a planned lesson within a unit plan, add lesson activities, and optionally use the lesson as the deepest curriculum anchor on a reusable task."
---

## Lesson: Ordered Planned Teaching Segment Within a Unit

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

`Lesson` is the ordered planned teaching segment inside a `Unit Plan`. It can hold type, date, duration, and a child table of `Lesson Activity` rows.

Current workspace note: `Lesson` remains a planned-curriculum record during the replatform. Runtime class delivery now lives in [**Class Session**](/docs/en/class-session/), and `Task Delivery` no longer stores `lesson_instance`.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`
Test refs: None

- Create the parent `Unit Plan` first because `unit_plan` is required.
- Decide whether to populate the optional `course` field or rely on the parent unit as the primary anchor.
- Prepare any `Lesson Activity` rows you want to capture inside the lesson.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

- Child of [**Unit Plan**](/docs/en/unit-plan/).
- Optional curriculum anchor for [**Task**](/docs/en/task/) through `Task.lesson`.
- Legacy planned anchor that may still help educators map shared lesson guidance to a live [**Class Session**](/docs/en/class-session/), though the live session model no longer depends on it.
- Editable and ordered from the staff course-plan workspace in `ui-spa`.
- Desk unit-form helpers still exist, but they are no longer the only authoring path.

## Lifecycle and Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

1. Create the lesson under a `Unit Plan` with required `title`.
2. Set planning metadata such as `lesson_type`, `start_date`, `duration`, and `is_published`.
3. Add `Lesson Activity` rows to break the lesson into pedagogical steps.
4. Staff can create, update, reorder, and remove lesson outlines from the shared course-plan workspace.
5. Optionally anchor reusable `Task` rows to this lesson. Runtime delivery then happens separately through `Task Delivery`.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Unit Plan**](/docs/en/unit-plan/)
- [**Lesson Activity**](/docs/en/lesson-activity/)
- [**Class Session**](/docs/en/class-session/)
- [**Task**](/docs/en/task/)
- [**Task Delivery**](/docs/en/task-delivery/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/lesson/lesson.py`
- **Required fields (`reqd=1`)**:
  - `unit_plan` (`Link` -> `Unit Plan`)
  - `title` (`Data`)
- **Child tables**:
  - `lesson_activities` (`Lesson Activity`)
- **Lifecycle hooks in controller**: none.

### Current Contract

- `Lesson` remains a planned record. The controller stays lightweight and now exposes lesson reordering that the SPA authoring endpoint also reuses.
- `Task._validate_curriculum_alignment()` checks that any selected lesson belongs to the selected unit plan and course context before a task is saved.
- If `Lesson.course` is blank, `Task` validation can still derive course alignment through the lesson's linked unit plan.
- `ifitwala_ed.api.teaching_plans.save_lesson_outline` now owns SPA lesson saves and lesson-activity replacement.

### Current Constraints To Preserve In Review

- `lesson.py` now exposes `reorder_lessons(unit_plan, lesson_names)` for both the staff SPA and the remaining Desk helper.
- Do not document `Lesson` as the runtime delivery row. That role now belongs to `Class Session`, with `Task Delivery` as optional class-assigned work.
