---
title: "Class Session: The Live Teaching Session for a Class"
slug: class-session
category: Curriculum
doc_order: 8
version: "1.0.2"
last_change_date: "2026-04-05"
summary: "Plan and run a real class session for one class teaching plan, with lifecycle status, learning goal, teacher notes, and session activities."
seo_title: "Class Session: The Live Teaching Session for a Class"
seo_description: "Use Class Session as the educator-facing runtime object for planned, in-progress, taught, changed, or canceled teaching sessions."
---

## Class Session: The Live Teaching Session for a Class

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/student_portfolio.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, None yet for the class-session controller itself

`Class Session` is the educator-facing runtime record for one real teaching session with one class. It belongs to a `Class Teaching Plan`, inherits governed class context, and moves through one lifecycle from planning to taught state.

Current workspace note: `Class Session` is the only live session object for planning, teaching, and session-linked assigned work.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

- Create the governing `Class Teaching Plan` first.
- Ensure the target `Unit Plan` is already part of that class teaching plan’s governed unit backbone.
- Decide whether the session is still `Draft`, ready as `Planned`, actively being taught, or already `Taught`.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/api/student_portfolio.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

- Live session object on the staff planning surface in `ui-spa/src/pages/staff/ClassPlanning.vue`.
- Quick calendar-to-session authoring overlay in `ui-spa/src/components/calendar/ClassEventModal.vue` and `ui-spa/src/overlays/planning/QuickClassSessionOverlay.vue`.
- Student LMS session context on `ui-spa/src/pages/student/CourseDetail.vue`.
- Optional runtime anchor on [**Task Delivery**](/docs/en/task-delivery/) through `class_session`.
- Optional reflection context on `Student Reflection Entry`.
- Class Hub session context, even though the current hub persistence path is still scaffold-level.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

1. Create the session under a `Class Teaching Plan`.
2. Link it to one governed `Unit Plan`.
3. Add session-specific title, date, learning goal, teacher note, and `Class Session Activity` rows.
4. The main low-friction authoring path may start from the staff calendar class-event overlay, which prefills the clicked class and date context before save.
5. Move the session through lifecycle states such as `Draft`, `Planned`, `In Progress`, `Taught`, `Changed`, or `Canceled`.
6. Optionally link downstream assigned work or reflections to the session when the class context matters.

## Related Docs

Status: Implemented
Code refs: None
Test refs: None

- [**Class Teaching Plan**](/docs/en/class-teaching-plan/)
- [**Task Delivery**](/docs/en/task-delivery/)
- [**Unit Plan**](/docs/en/unit-plan/)
- [**Student Group**](/docs/en/student-group/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/class_session/class_session.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/class_session/class_session.py`
- **Required fields (`reqd=1`)**:
  - `title`
  - `class_teaching_plan`
  - `unit_plan`
- **Child tables**:
  - `activities` (`Class Session Activity`)
- **Lifecycle hooks in controller**:
  - `before_validate`
  - `validate`

### Current Contract

- `Class Session` is the only live planning-to-taught session object in the approved model.
- The controller enforces that every session belongs to the class teaching plan and to one governed unit already present on that plan.
- The controller stamps `student_group`, `course_plan`, `course`, and `academic_year` from the owning class teaching plan.
- `api/teaching_plans.py` is the current bounded read/write surface for staff and student session payloads.

### Current Constraints To Preserve In Review

- Do not reintroduce a second competing taught-session object.
- Do not let assessment flows auto-create `Class Session`; class sessions belong to educator planning and delivery, not to assessment side effects.
- Keep teacher-only fields such as `teacher_note` and `teacher_prompt` out of student payloads.
