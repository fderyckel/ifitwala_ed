---
title: "Lesson Activity: Pedagogical Atom Inside a Lesson"
slug: lesson-activity
category: Curriculum
doc_order: 7
version: "1.1.0"
last_change_date: "2026-03-31"
summary: "Capture the smallest planned activity inside a lesson, including type, content prompts, requiredness, and estimated duration, without turning lesson flow into the reusable materials library."
seo_title: "Lesson Activity: Pedagogical Atom Inside a Lesson"
seo_description: "Capture the smallest planned activity inside a lesson, including type, content prompts, requiredness, and estimated duration."
---

## Lesson Activity: Pedagogical Atom Inside a Lesson

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.py`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/api/student_portfolio.py`
Test refs: None

`Lesson Activity` is the smallest planned instructional step inside a `Lesson`. It stores the activity type plus optional content such as reading text, a video URL, an external link, or a discussion prompt.

Current workspace note: `Lesson Activity` is a child table, not a standalone planning workflow. It may still appear as reflection context, but neither `Class Session` nor `Task Delivery` links to it directly in the live schema, and reusable supporting materials now live outside the lesson body in the materials domain.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`
Test refs: None

- Create the parent `Lesson` first.
- Decide the activity type first because some content fields are type-specific.
- Treat the row as lesson planning metadata, not as assessment evidence or delivery state.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/api/student_portfolio.py`
Test refs: None

- Stored only in `Lesson.lesson_activities`.
- Student portfolio APIs accept lesson-activity context in reflection payloads.
- The current task stack does not expose `lesson_activity` on `Task` or `Task Delivery`.
- Reusable files and reusable reference links should use the materials domain instead of duplicating lesson-activity links.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/api/student_portfolio.py`
Test refs: None

1. Open the parent `Lesson`.
2. Add one or more `Lesson Activity` rows to `lesson_activities`.
3. Set the type, title, order, requiredness, and any relevant content fields.
4. Optionally reference a specific activity from downstream reflection context.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Lesson**](/docs/en/lesson/)
- [**Class Session**](/docs/en/class-session/)
- [**Task**](/docs/en/task/)
- [**Supporting Material**](/docs/en/supporting-material/)
- [**Task Delivery**](/docs/en/task-delivery/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.py`
Test refs: None

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.py`
- **DocType type**: child table (`istable = 1`)
- **Required fields (`reqd=1`)**: none at schema level.
- **Lifecycle hooks in controller**: none.

### Current Contract

- This row belongs to `Lesson.lesson_activities`.
- The child controller is intentionally empty, keeping business logic on the parent or downstream runtime doctypes.
- `lesson_activity` can still be used as reflection metadata, but it is not a direct `Class Session` or `Task Delivery` anchor.
- Video and external links inside lesson activities remain lesson-flow content unless the teacher intentionally creates a reusable supporting material.

### Current Constraints To Preserve In Review

- Do not move task or delivery business logic into this child table.
- Do not document this row as a required runtime object; lessons, class sessions, and assigned-work flows can all exist without it.
- Do not repurpose this child table into the reusable materials system.
