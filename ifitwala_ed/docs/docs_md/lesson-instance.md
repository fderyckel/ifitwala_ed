---
title: "Lesson Instance: Real Taught Event for a Student Group"
slug: lesson-instance
category: Curriculum
doc_order: 8
version: "1.0.0"
last_change_date: "2026-03-12"
summary: "Represent the real taught lesson event for a student group, optionally linking a planned lesson or lesson activity to runtime task delivery and class-hub context."
seo_title: "Lesson Instance: Real Taught Event for a Student Group"
seo_description: "Represent the real taught lesson event for a student group, optionally linking a planned lesson or lesson activity to runtime task delivery and class-hub context."
---

## Lesson Instance: Real Taught Event for a Student Group

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`, `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: None (scaffold only: `ifitwala_ed/curriculum/doctype/lesson_instance/test_lesson_instance.py`)

`Lesson Instance` is the taught-curriculum record for a `Student Group`. It can point to a planned `Lesson` or `Lesson Activity`, but it can also exist without tasks, assessments, or even a planned lesson link.

Current workspace note: `Task Delivery` links to `Lesson Instance` through `lesson_instance`, but does not directly store lesson or lesson-activity fields.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`
Test refs: None

- Create the target `Student Group` first because course and academic-year context are fetched from it.
- Optionally prepare a planned `Lesson` or `Lesson Activity` if you want the instance tied back to planning.
- Decide whether the instance is a `Scheduled Session` or `Async Learning Event`.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`, `ifitwala_ed/api/student_portfolio.py`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

- Optional taught-context link on [**Task Delivery**](/docs/en/task-delivery/).
- Created or reused by `assessment/task_delivery_service.py` when explicit lesson-instance context is supplied.
- Referenced by staff Class Hub payloads and UI types.
- Carried into student portfolio reflection context.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/class_hub.py`
Test refs: None (scaffold only: `ifitwala_ed/curriculum/doctype/lesson_instance/test_lesson_instance.py`)

1. Create the instance manually or through a helper with a `student_group`.
2. Optionally attach `lesson`, `lesson_activity`, dates, times, and creation source metadata.
3. Optionally link a `Task Delivery` to the instance through `lesson_instance`.
4. Reuse the instance in Class Hub or portfolio-style runtime context.

Current workspace note: `resolve_or_create_lesson_instance()` can auto-create an async instance when explicit lesson/activity fields are available on the delivery object, but the current delivery schema and APIs typically require an already-known `lesson_instance` instead.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Lesson**](/docs/en/lesson/)
- [**Lesson Activity**](/docs/en/lesson-activity/)
- [**Task**](/docs/en/task/)
- [**Task Delivery**](/docs/en/task-delivery/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`, `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/class_hub.py`
Test refs: None (scaffold only: `ifitwala_ed/curriculum/doctype/lesson_instance/test_lesson_instance.py`)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.py`
- **Required fields (`reqd=1`)**: none at schema level.
- **Lifecycle hooks in controller**: none.
- **Key links**:
  - `lesson`
  - `lesson_activity`
  - `student_group`
  - `course` (fetched from `student_group`)
  - `academic_year` (fetched from `student_group`)

### Current Contract

- The DocType description is explicit: `Lesson Instance` does not own tasks, does not require assessment, and is never required for grading or submission.
- The controller is empty; runtime creation logic currently lives in `assessment/task_delivery_service.py`.
- `Task Delivery` can store a `lesson_instance`, but the current delivery schema does not expose `lesson` or `lesson_activity` directly.

### Current Constraints To Preserve In Review

- Do not document `Lesson Instance` as mandatory for every task flow.
- `api/class_hub.py` currently returns demo session data and does not persist the full lesson-instance lifecycle.
