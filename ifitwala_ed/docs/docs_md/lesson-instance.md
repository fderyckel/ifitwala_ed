---
title: "Lesson Instance (Retired)"
slug: lesson-instance
category: Curriculum
doc_order: 9
version: "2.0.0"
last_change_date: "2026-04-01"
summary: "Lesson Instance has been retired from the live model and replaced by Class Session."
seo_title: "Lesson Instance (Retired)"
seo_description: "Lesson Instance is no longer part of the live schema. Use Class Session for real teaching-session context."
---

## Lesson Instance (Retired)

Status: Deprecated
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/docs_md/class-session.md`
Test refs: None

`Lesson Instance` is no longer part of the live `ifitwala_ed` schema or runtime code.

As of `2026-04-01`, the product uses [**Class Session**](/docs/en/class-session/) as the single educator-facing runtime object for class-session planning and taught-session context.

## Replacement

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

Use [**Class Session**](/docs/en/class-session/) instead when you need:

- planned or live session context for one class
- session lifecycle state
- session activities
- optional task-delivery anchoring
- optional reflection anchoring

## Related Docs

Status: Implemented
Code refs: None
Test refs: None

- [**Class Session**](/docs/en/class-session/)
- [**Task Delivery**](/docs/en/task-delivery/)
- [**Lesson**](/docs/en/lesson/)
- [**Lesson Activity**](/docs/en/lesson-activity/)

## Technical Notes (IT)

Status: Deprecated
Code refs: `ifitwala_ed/docs/curriculum/02_educator_centered_curriculum_replatform_plan.md`
Test refs: None

### Removal Note

- The old `ifitwala_ed/curriculum/doctype/lesson_instance/*` doctype files have been removed.
- Any new implementation that still refers to `lesson_instance` is a regression against the approved curriculum contract.
