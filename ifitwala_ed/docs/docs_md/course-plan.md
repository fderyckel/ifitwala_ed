---
title: "Course Plan: Shared Curriculum Version For A Course"
slug: course-plan
category: Curriculum
doc_order: 4
version: "1.0.0"
last_change_date: "2026-04-01"
summary: "Define the governed shared curriculum version for a course, including cycle labeling, publication status, and shared summary context that unit plans inherit."
seo_title: "Course Plan: Shared Curriculum Version For A Course"
seo_description: "Define the governed shared curriculum version for a course, including the shared summary and the unit-plan backbone inherited by linked classes."
---

## Course Plan: Shared Curriculum Version For A Course

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/course_plan/course_plan.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

`Course Plan` is the governed shared curriculum version for a `Course`. It defines the academic-year or cycle-level planning record that owns the `Unit Plan` backbone and the shared summary educators see before they begin class-level adaptation.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`
Test refs: None

- Link the plan to an existing `Course`.
- Decide whether the plan needs an academic-year label, cycle label, or both.
- Prepare the shared summary and non-negotiables the curriculum team wants all linked classes to inherit.

## Where It Is Used Across The ERP

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

- Parent planning context for [**Unit Plan**](/docs/en/unit-plan/) rows.
- Governing curriculum selection for [**Class Teaching Plan**](/docs/en/class-teaching-plan/) records.
- Shared curriculum workspace in the staff SPA for editing summary, status, and governed unit sequence.
- Shared course-level resource anchor through `Material Placement`.

## Lifecycle And Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

1. Create the course plan under a `Course`.
2. Set the shared title, cycle metadata, and summary that explain the plan’s shared intent.
3. Add one or more `Unit Plan` rows as the governed backbone for linked classes.
4. Staff can edit the shared course-plan fields directly from the staff course-plan workspace in the SPA.
5. Class teaching plans then inherit one selected course plan and adapt delivery without mutating the shared plan.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Unit Plan**](/docs/en/unit-plan/)
- [**Class Teaching Plan**](/docs/en/class-teaching-plan/)
- [**Class Session**](/docs/en/class-session/)
- [**Task**](/docs/en/task/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/course_plan/course_plan.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

### Schema And Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.py`
- **Required fields (`reqd=1`)**:
  - `title` (`Data`)
  - `course` (`Link` -> `Course`)
- **Operational/public methods**:
  - `list_staff_course_plans()` (whitelisted)
  - `get_staff_course_plan_surface(course_plan, unit_plan=None)` (whitelisted)
  - `save_course_plan(...)` (whitelisted)

### Current Contract

- `Course Plan` is the shared curriculum version record for a course, not a class-owned delivery record.
- Each `Class Teaching Plan` must point to exactly one governing `Course Plan`.
- Shared course-plan resources live on `Material Placement` with `anchor_doctype = Course Plan`.
- The staff course-plan workspace uses one bounded bootstrap payload and explicit save mutations rather than client waterfalls.

### Current Constraints To Preserve In Review

- Do not mutate linked class teaching plans directly when editing course-plan summary fields.
- Keep governed curriculum ownership on the shared plan and units, not on class sessions.
- Preserve server-side permission checks for both shared plan reads and writes.
