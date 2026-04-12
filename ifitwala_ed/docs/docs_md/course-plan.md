---
title: "Course Plan: Shared Curriculum Version For A Course"
slug: course-plan
category: Curriculum
doc_order: 4
version: "1.5.0"
last_change_date: "2026-04-11"
summary: "Define the governed shared curriculum version for a course, including SPA-first creation from the course-plan index, cycle labeling, publication status, shared summary context, the calendar-aware curriculum timeline, and the governed workspace used to author units, quiz banks, and assignment-ready curriculum assets."
seo_title: "Course Plan: Shared Curriculum Version For A Course"
seo_description: "Define the governed shared curriculum version for a course, including the shared summary and the unit-plan backbone inherited by linked classes."
---

## Course Plan: Shared Curriculum Version For A Course

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/course_plan/course_plan.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/quiz.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanIndex.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/components/planning/CoursePlanTimelineCard.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_quiz.py`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/CoursePlanWorkspace.test.ts`

`Course Plan` is the governed shared curriculum version for a `Course`. It defines the academic-year or cycle-level planning record that owns the `Unit Plan` backbone and the shared summary educators see before they begin class-level adaptation.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`
Test refs: None

- Link the plan to an existing `Course`.
- Decide whether the plan needs an `Academic Year` link, cycle label, or both.
- Prepare the shared summary and non-negotiables the curriculum team wants all linked classes to inherit.
- Staff can start the plan directly from the staff course-plan index in the SPA; a separate Desk-first creation step is no longer required.
- When the plan is year-bound, the staff SPA now selects `Academic Year` from real `Academic Year` records scoped to the linked course school instead of accepting free text.
- Desk `Text Editor` fields surfaced in this workspace now keep their rich formatting in the staff SPA instead of flattening content into plain text.

## Where It Is Used Across The ERP

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanIndex.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`

- Parent planning context for [**Unit Plan**](/docs/en/unit-plan/) rows.
- Governing curriculum selection for [**Class Teaching Plan**](/docs/en/class-teaching-plan/) records.
- Shared curriculum workspace in the staff SPA for editing summary, status, governed unit sequence, and course quiz banks.
- Launch point for prefilled assignment flows from published quiz banks.
- Shared course-level resource anchor through `Material Placement`.

## Lifecycle And Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

1. Create the course plan under a `Course`.
   Staff can now do this directly from the course-plan index in the SPA.
2. Set the shared title, cycle metadata, and summary that explain the plan’s shared intent.
3. Add one or more `Unit Plan` rows as the governed backbone for linked classes.
4. Staff can edit the shared course-plan fields directly from the staff course-plan workspace in the SPA.
5. The same SPA workspace also surfaces course-level quiz-bank authoring for the linked course.
6. Published quiz banks can hand off into the existing task-delivery overlay without creating a second assignment workflow.
7. Class teaching plans then inherit one selected course plan and adapt delivery without mutating the shared plan.

## Permission Matrix

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/curriculum/planning.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`

- Desk role permissions on `Course Plan` remain broad enough for administrative access (`System Manager`, `Academic Admin`, `Curriculum Coordinator`), but the staff SPA is the canonical shared authoring surface.
- Staff SPA read access is resolved server-side from curriculum scope helpers, not from route visibility alone.
- Staff SPA write access is limited to users who can manage curriculum for the linked `Course`; this includes curriculum leadership and instructors with qualifying teaching assignment access for that course.
- When the workspace is opened with optional `student_group` context to clamp the timeline to a term-scoped class, the API also enforces staff access to that `Student Group`; the timeline must not accept an arbitrary class hint from the browser.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Unit Plan**](/docs/en/unit-plan/)
- [**Class Teaching Plan**](/docs/en/class-teaching-plan/)
- [**Class Session**](/docs/en/class-session/)
- [**Quiz Question Bank**](/docs/en/quiz-question-bank/)
- [**Task**](/docs/en/task/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/course_plan/course_plan.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/quiz.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_quiz.py`

### Schema And Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.py`
- **Required fields (`reqd=1`)**:
  - `title` (`Data`)
  - `course` (`Link` -> `Course`)
- **Operational/public methods**:
  - `list_staff_course_plans()` (whitelisted)
  - `create_course_plan(...)` (whitelisted)
  - `get_staff_course_plan_surface(course_plan, unit_plan=None)` (whitelisted)
  - `save_course_plan(...)` (whitelisted)

### Current Contract

- `Course Plan` is the shared curriculum version record for a course, not a class-owned delivery record.
- Each `Class Teaching Plan` must point to exactly one governing `Course Plan`.
- Shared course-plan resources live on `Material Placement` with `anchor_doctype = Course Plan`.
- The staff course-plan index bootstraps both existing plans and create-ready course options in one bounded payload.
- New course-plan creation now starts from the staff SPA index and routes directly into the course-plan workspace.
- Course-plan `academic_year` in the staff SPA is now chosen from actual `Academic Year` docs resolved for the selected course school scope; create/update mutations reject out-of-scope changes while preserving unchanged legacy values.
- The staff course-plan workspace now edits and renders Desk `Text Editor` fields as Desk-compatible rich text, including course summary, governed unit rich-text fields, and quiz question prompt/explanation.
- The staff course-plan workspace now includes a bounded read-only curriculum timeline that lays governed unit durations across real instructional dates from the resolved `School Calendar`, shading holiday/break spans and skipping non-instructional days instead of guessing in the browser.
- When the shared course plan is opened with optional `student_group` route context and that class is term-scoped, the curriculum timeline clamps to that term window instead of the full Academic Year.
- Units without a usable numeric week duration stay unscheduled on the timeline and block later unit placement until the missing duration is fixed; the workspace must not guess those later dates.
- Shared course-plan and unit-plan save mutations now enforce optimistic concurrency with `record_modified` read tokens and `expected_modified` write tokens, and they reject stale saves with a reload-required validation message.
- Rich course-plan HTML is sanitized server-side before save so Desk/SPAs can preserve formatting without storing script-bearing markup.
- Hot course-plan index/load/save endpoints now emit bounded `ifitwala.curriculum` event logs with status and elapsed time for Cloud Logging metrics and alerting.
- The staff course-plan workspace uses one bounded bootstrap payload and explicit save mutations rather than client waterfalls.
- Long course-plan workspace cards such as Overview, Timeline, Plan Resources, Unit Content, and Quiz Banks can now collapse and persist their open/closed state per course plan so staff can reduce scroll noise without losing context.
- Quick Access on the course-plan workspace is a compact top-integrated jump strip rather than a large floating card, to preserve vertical space and reduce distraction while editing.
- Quiz banks remain course-level assessment assets in the current schema, but the staff course-plan workspace is the current SPA authoring surface for them.
- Assignment handoff from the course-plan workspace must stay prefilled into the canonical task-delivery overlay rather than creating a parallel assignment path.

### Current Constraints To Preserve In Review

- Do not mutate linked class teaching plans directly when editing course-plan summary fields.
- Keep governed curriculum ownership on the shared plan and units, not on class sessions.
- Preserve server-side permission checks for both shared plan reads and writes.
