---
title: "Unit Plan: Governed Curriculum Backbone Inside a Course Plan"
slug: unit-plan
category: Curriculum
doc_order: 5
version: "1.3.3"
last_change_date: "2026-04-03"
summary: "Define the shared unit backbone for a course plan, including standards alignment, pedagogy, reflections, and thin lesson outlines that class teaching plans inherit and can assign from."
seo_title: "Unit Plan: Governed Curriculum Backbone Inside a Course Plan"
seo_description: "Define the shared unit backbone for a course plan, including standards alignment, pedagogy, and reflections that class teaching plans inherit."
---

## Unit Plan: Governed Curriculum Backbone Inside a Course Plan

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.py`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.js`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: `ifitwala_ed/curriculum/doctype/unit_plan/test_unit_plan.py`, `ifitwala_ed/api/test_teaching_plans.py`

`Unit Plan` is the governed curriculum unit inside a `Course Plan`. It carries the shared sequence, pedagogy, standards alignment, and reflection context that all linked class teaching plans inherit.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`
Test refs: None

- Create the parent `Course Plan` first because `course_plan` is required.
- Decide whether the unit also needs a linked `Program`, `unit_code`, versioning, and publication state.
- Prepare any inline standards rows and shared planning reflections you want to capture on the unit.
- Unit pedagogy and reflection fields marked as Desk `Text Editor` now use the same rich-text editing and display model in the staff SPA, preserving formatting across surfaces.

## Where It Is Used Across The ERP

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

- Mandatory backbone for [**Class Teaching Plan**](/docs/en/class-teaching-plan/) rows.
- Parent curriculum context for [**Lesson**](/docs/en/lesson/) rows.
- Optional curriculum anchor for [**Task**](/docs/en/task/) through `Task.unit_plan`.
- Shared curriculum context that the staff planning SPA and student LMS learning space both surface.
- Editable governed unit authoring surface inside the shared staff course-plan workspace.
- Source of class-reflection rollups: class-owned reflections live on `Class Teaching Plan Unit` rows and hydrate the wider unit view in staff planning.

## Lifecycle And Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.py`, `ifitwala_ed/curriculum/planning.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

1. Create the unit under a `Course Plan` with required `title`.
2. Capture the shared pedagogy, durations, misconceptions, content, skills, concepts, and inline standards alignment.
3. Add shared `Curriculum Planning Reflection` rows when the curriculum team wants unit-level planning history.
4. Add thin shared `Lesson` outlines when the department wants common lesson guidance without turning delivery into one rigid runtime tree.
5. Published lesson outlines can prefill the canonical task-delivery overlay so teachers can assign from shared guidance without re-entering the lesson anchor.
6. Staff can edit and save the governed unit directly from the shared `ui-spa` course-plan workspace.
7. Class teaching plans inherit the governed unit sequence automatically.
8. Teachers then adapt pacing, sessions, and class-owned reflections without changing the shared unit backbone.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Course Plan**](/docs/en/course-plan/)
- [**Class Teaching Plan**](/docs/en/class-teaching-plan/)
- [**Lesson**](/docs/en/lesson/)
- [**Learning Standards**](/docs/en/learning-standards/)
- [**Learning Unit Standard Alignment**](/docs/en/learning-unit-standard-alignment/)
- [**Task**](/docs/en/task/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.py`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.js`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan_list.js`
Test refs: `ifitwala_ed/curriculum/doctype/unit_plan/test_unit_plan.py`

### Schema And Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.py`
- **Desk client script**: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.js`
- **Desk list script**: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan_list.js`
- **Required fields (`reqd=1`)**:
  - `title` (`Data`)
  - `course_plan` (`Link` -> `Course Plan`)
- **Child tables**:
  - `standards` (`Learning Unit Standard Alignment`)
  - `reflections` (`Curriculum Planning Reflection`)
- **Lifecycle hooks in controller**:
  - `before_validate`
  - `before_insert`
  - `validate`
  - `after_insert`
  - `on_update`
- **Operational/public methods**:
  - `get_program_subtree_scope(program)` (whitelisted)

### Current Contract

- `Unit Plan` owns ordering within a `Course Plan` through `unit_order`.
- `unit_plan.py` normalizes the carried curriculum fields and repairs `unit_order` collisions in steps of 10.
- `ifitwala_ed.api.teaching_plans.save_unit_plan` now owns SPA-side governed unit mutations, including inline standards and shared reflection rows.
- In the staff course-plan workspace, `program` is now selected from actual `Program` docs already linked to the unit course; save mutations reject changed program values that are not linked to that course while preserving unchanged legacy values.
- Shared reflection `academic_year` and `school` remain parent-derived from the selected `Course Plan` in the SPA instead of being hand-entered in the governed unit overlay.
- The staff course-plan workspace now edits and renders unit `Text Editor` fields (`overview`, `essential_understanding`, `misconceptions`, `content`, `skills`, `concepts`) and reflection `Text Editor` fields with Desk-compatible rich text instead of plain textareas/plain interpolation.
- `ifitwala_ed.api.teaching_plans.save_lesson_outline` now owns SPA-side lesson-outline mutations for the selected unit.
- Unit and lesson rich-text fields are sanitized server-side before save, and existing unit/lesson saves now reject stale `expected_modified` tokens instead of silently overwriting another staff member's newer edit.
- Course-plan unit and lesson save endpoints now emit bounded `ifitwala.curriculum` timing/status logs for production observability.
- Published lesson outlines in the course-plan workspace can prefill the existing task-delivery overlay with both `unit_plan` and `lesson` context.
- Desk List View expands parent-program filters to the full descendant program subtree before fetching rows.
- `unit_plan.js` still exposes Desk lesson helpers, but the staff course-plan workspace is now the primary SPA lesson authoring surface.
- `Task.unit_plan` and `Lesson.unit_plan` now point to this doctype directly.

### Current Constraints To Preserve In Review

- `Unit Plan` is a shared curriculum object, not a class-owned teaching event and not a grading fact table.
- Class-specific pacing, activities, and reflections still belong on `Class Teaching Plan` and `Class Session`.
- Inline standards rows remain snapshots owned by the unit; they do not hard-link back to `Learning Standards`.
