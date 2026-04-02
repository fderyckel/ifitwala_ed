# Educator-Centered Curriculum Replatform Plan

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

This plan tracks the remaining cleanup needed to finish the curriculum replatform without inventing a second architecture.

The live contract is already the educator-centered spine documented in `01_curriculum_task_delivery_contract.md`. This file exists only to track what is still not fully aligned.

## What Is Already Landed

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

- Shared curriculum now runs through `Course Plan` and `Unit Plan`.
- Class planning now runs through `Class Teaching Plan` and `Class Session`.
- Student LMS reads now bootstrap from `ifitwala_ed.api.teaching_plans.get_student_learning_space`.
- Staff planning already has route-based SPA surfaces for both shared planning and class planning, including SPA-first `Course Plan` creation from the course-plan index.
- `Task Delivery` already enforces `Class Teaching Plan` ownership, with optional `Class Session` context.
- Resource sharing already resolves across `Course Plan`, `Unit Plan`, `Class Teaching Plan`, `Class Session`, and `Task`.

## Remaining Canonicalization Work

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/lesson-activity.md`, `ifitwala_ed/docs/docs_md/task-delivery.md`, `ifitwala_ed/workspace_sidebar/curriculum.json`, `ifitwala_ed/curriculum/workspace/curriculum/curriculum.json`
Test refs: None

The remaining work is documentation and semantic cleanup, not a fresh architecture design:

- rewrite `docs_md` pages that still describe the old lesson-centric runtime as current reality
- finish removing lesson-instance language from remaining docs, labels, and workspace copy
- decide whether `Lesson` and `Lesson Activity` stay as thin shared-guidance objects or are retired entirely
- align educator-facing naming where current labels still expose backend-first semantics

## Locked Constraints For Remaining Work

Status: Locked
Code refs: `ifitwala_ed/docs/high_concurrency_contract.md`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/assessment/task_delivery_service.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/assessment/test_task_delivery_service.py`

The rest of the replatform must keep these constraints:

- no compatibility shims that preserve the lesson-instance runtime as a second truth
- no Desk-first replacement for teacher planning
- no student LMS rollback to lesson-tree waterfalls
- no weakening of class scope, sibling isolation, or server-side permission checks
- no doc rewrite that describes hoped-for behavior as already implemented

## Planned Cleanup Order

Status: Planned
Code refs: `ifitwala_ed/docs/docs_md/course.md`, `ifitwala_ed/docs/docs_md/unit-plan.md`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/lesson-activity.md`, `ifitwala_ed/docs/docs_md/class-session.md`, `ifitwala_ed/docs/docs_md/material-placement.md`, `ifitwala_ed/docs/docs_md/task.md`, `ifitwala_ed/docs/docs_md/task-delivery.md`
Test refs: None

1. Keep the canonical curriculum contracts in `docs/curriculum` accurate first.
2. Rewrite downstream `docs_md` pages so they match the live educator-centered model.
3. Remove or rename legacy teacher-facing labels that still imply the old runtime.
4. Retire thin legacy objects only when docs, schema, and SPA behavior are ready together.

## Not Yet Canonical

Status: Explicitly not locked
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`
Test refs: None

These are not current source-of-truth claims:

- direct `Lesson Activity` ownership of the live student runtime
- a second LMS tree beside the class-aware learning space
- educator-specific planning overlays for co-taught classes
- any separate assigned-work model outside `Task` plus `Task Delivery`

## Related Docs

Status: Canonical map
Code refs: None
Test refs: None

- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
- `ifitwala_ed/docs/curriculum/03_curriculum_materials_and_resource_contract.md`
- `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`

## Technical Notes (IT)

Status: Canonical
Code refs: `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/lesson-activity.md`
Test refs: None

- The main remaining drift risk is semantic, not structural: legacy names still exist in code and downstream docs.
- Do not "fix" that drift by documenting old semantics as live truth.
- If `Lesson` and `Lesson Activity` remain, their future role must be documented as thin shared guidance only.
- If they are retired, docs and schema must move together in one approved change.
