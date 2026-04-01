# Educator-Centered Curriculum, Class Planning, and Session Delivery Contract (Authoritative)

Status: Canonical migration contract for the curriculum redesign
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/curriculum/doctype/learning_unit/test_learning_unit.py`, `ifitwala_ed/curriculum/doctype/lesson/test_lesson.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`, `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/api/test_teaching_plans.py`

This note is the authoritative curriculum contract for the redesign direction discussed and approved at the documentation level.

During the reset, this note does two jobs:

1. describe the current workspace reality honestly
2. lock the approved educator-centered target architecture for implementation

The central correction is explicit:

> No single shared lesson tree may serve at the same time as shared curriculum, class-level planning, and historical record of what happened in class.

## Current Workspace Reality

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/courses.py`
Test refs: `ifitwala_ed/curriculum/doctype/learning_unit/test_learning_unit.py`, `ifitwala_ed/curriculum/doctype/lesson/test_lesson.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_courses.py`

- The educator-centered runtime now lives in `Course Plan`, `Unit Plan`, `Class Teaching Plan`, and `Class Session`.
- Legacy planned-curriculum doctypes `Learning Unit`, `Lesson`, and `Lesson Activity` still exist in the workspace, but they are no longer paired with a `Lesson Instance` runtime object.
- `Lesson Instance` has been removed from the live schema and runtime code.
- Assessed work still lives in `Task` and `Task Delivery`, but `Task Delivery` now soft-links to `Class Session` instead of `Lesson Instance`.
- `Material Placement` is still course-scoped and still needs the planned resource-model reset.
- Student LMS reads now use `ifitwala_ed.api.teaching_plans.get_student_learning_space`; the old lesson-tree bootstrap in `api/courses.py` has been retired.
- Published docs under `ifitwala_ed/docs/docs_md/` are now being rewritten to reflect the class-session model and to mark `Lesson Instance` as retired.

## Approved Design Direction

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/planning.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`

- The stable shared center of gravity must be the course plan and unit plan, not the daily lesson.
- A `Course` may own multiple `Course Plan` records, including concurrent plans in the same academic year or cycle where governance requires that.
- Educator-facing planning must distinguish:
  - shared intended curriculum
  - class-level teaching plan
  - what actually happened in a class session
- Teacher autonomy in pacing, activities, examples, and resources is normal product behavior, not an edge case.
- Student and teacher read surfaces must resolve class-owned planning and class sessions first, then shared course-plan content second.
- Staff curriculum planning and class-session planning must surface in `ui-spa`, not as a Desk-first workflow.
- Student curriculum and lesson consumption must surface in the LMS/student portal, not as a Desk-shaped curriculum reader.
- Educator-facing semantics must take precedence over technical naming. Backend names may lag temporarily during implementation, but UI and canonical docs must use educator-centered language.

## Educator-Centered Domain Model

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan_unit/class_teaching_plan_unit.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/class_session_activity/class_session_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

### Shared Curriculum Layer

- **Course**
  - stable catalog identity
  - long-lived academic identity reused across years and offerings
- **Course Plan**
  - shared intended curriculum for a cycle, year, or approved curriculum revision
  - department-owned or program-owned
  - a course may have multiple course plans; each class teaching plan must point to exactly one governing course plan
- **Unit Plan**
  - shared unit sequence inside a course plan
  - owns outcomes, standards alignment, major learning arc, non-negotiables, and common assessment anchors
  - forms the mandatory shared curricular backbone across class teaching plans linked to the same course plan
- **Suggested Session Outline**
  - optional thin shared guidance only
  - never the required operational source of truth for class-by-class teaching

### Class Teaching Layer

- **Class Teaching Plan**
  - educator-owned plan for one class or teaching group in one term/cycle
  - adapts the shared course plan for the class actually being taught
  - owns pacing, chosen resources, substitutions, adaptations, and local sequencing
  - co-taught classes should normally use one shared class teaching plan owned by the teaching team
- **Class Session**
  - educator-facing session record for one teaching event
  - one lifecycle object that moves through states such as `draft`, `planned`, `in_progress`, `taught`, `changed`, and `canceled`
- **Session Activity**
  - the operational teaching steps inside a class session
  - owns class-specific activities, timings, teacher moves, and session resources

### Shared and Class-Level Work

- **Reusable Learning Task / Common Assessment**
  - reusable work definition that may be shared across classes
  - should anchor to shared curriculum objects, not directly to one class by default
- **Assigned Work for Class**
  - runtime assignment of shared or class-authored work to one class
  - due dates, grading mode, and release policy stay class-scoped

## Ownership and Governance

Status: Planned
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.py`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/schedule/doctype/student_group/student_group.py`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`

- Department or program owners should own `Course Plan`, `Unit Plan`, and common assessment baselines.
- Teachers or teaching teams should own `Class Teaching Plan`, `Class Session`, and most teaching resources.
- School or program governance may still define non-negotiables such as:
  - required outcomes
  - mandatory unit backbone and sequence
  - required common assessments
  - required texts or anchor resources
  - mandatory reporting checkpoints
- The product must support class-level adaptation without forcing teachers to fork the shared curriculum unnecessarily.
- Teachers should be able to adapt within a unit and within class sessions, but should not be able to reorder, skip, or replace the governed unit backbone without explicit elevated governance permission.

## Resolution Rules For Read Surfaces

Status: Partial
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`

1. Student and teacher surfaces must resolve class-specific planning first.
2. Shared course-plan content is fallback context, not the default operational truth when a class-owned object exists.
3. Class resources and class session activities must never bleed into sibling classes.
4. Common assessment templates do not imply assignment; class assignment remains explicit.
5. SPA read paths should prefer one bounded bootstrap endpoint per surface rather than request waterfalls.
6. Permission checks remain server-side and class-scoped.
7. Staff planning surfaces and student LMS learning surfaces must remain route-based `ui-spa` experiences with contextual actions, actionable errors, and no silent fallback to Desk.

## Semantic Mapping During Rewrite

Status: Planned
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.json`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/schedule/doctype/student_group/student_group.json`
Test refs: None yet for the redesigned vocabulary

| Current code term | Target educator-centered term | Direction |
|---|---|---|
| `Course` | Course | Keep |
| `Learning Unit` | Unit Plan | Replace or rename during redesign |
| `Lesson` | Suggested Session Outline | Thin shared guidance only, or remove if not needed |
| `Lesson Activity` | Session Activity | Move out of shared canonical lesson ownership |
| `Lesson Instance` | Class Session | Promote into core educator-facing runtime object |
| `Student Group` | Class / Teaching Group | Prefer educator-facing UI labels |
| `Task` | Reusable Learning Task / Common Assessment | Keep concept, revise anchors and UI semantics |
| `Task Delivery` | Assigned Work for Class | Keep runtime concept, revise educator-facing naming |
| `Material Placement` | Resource Share / Teaching Resource Share | Extend to class-owned anchors |

## Guardrails

Status: Planned
Code refs: `ifitwala_ed/curriculum/doctype/class_session/class_session.py`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.py`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/courses.py`
Test refs: None yet for the redesigned model

- Do not allow a heavy shared lesson object to become the operational teaching truth again.
- Do not store class-specific pacing, activity sequence, or teacher-only materials on shared canonical curriculum objects unless they are intentionally shared as baseline guidance.
- Do not use `Task`, `Task Delivery`, or resource placement as a workaround for missing class-planning objects.
- Do not split planning truth and enacted truth across unrelated objects without an explicit lifecycle contract.
- Do not introduce educator-specific planning overlays for co-taught classes in the first implementation; one class should keep one shared planning truth.
- Keep child-table logic lightweight; class/session business logic must stay on parent doctypes or dedicated services.
- Preserve multi-tenant isolation and instructor/class visibility rules server-side.
- Preserve the high-concurrency rule: class and student surfaces must use bounded bootstrap reads, scoped caches, and no uncontrolled refresh loops.
- Preserve the product rule: curriculum planning should happen where educators already work in the SPA, and student lesson consumption should happen where students already learn in LMS.

## Confirmed Product Decisions

Status: Planned
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/schedule/doctype/student_group/student_group.json`
Test refs: None yet for the redesigned model

The redesign now proceeds with these governance rules locked:

1. A `Course` may have multiple `Course Plan` records, including concurrent plans within the same academic year or cycle where governance requires that. Each `Class Teaching Plan` must link to exactly one governing `Course Plan`.
2. A co-taught `Student Group` should normally use one shared `Class Teaching Plan` owned by the teaching team. Educator-specific overlays are out of scope for the first implementation, though lightweight private notes may be added later without creating separate planning truth.
3. `Class Session` is one educator-facing lifecycle object that moves from planning through taught state, rather than separate planned-session and taught-session core doctypes.
4. The governed subset across `Class Teaching Plan` records linked to the same `Course Plan` includes shared outcomes, the mandatory `Unit Plan` backbone and sequence, required common assessments, and any explicitly governed anchor resources. Pacing inside a unit, `Class Session` design, `Session Activity` sequence, examples, and most class-owned resources remain teacher-controlled unless stricter governance is configured.

## Related Docs

Status: Planned
Code refs: None
Test refs: None

- `ifitwala_ed/docs/curriculum/02_educator_centered_curriculum_replatform_plan.md`
- `ifitwala_ed/docs/docs_md/course.md`
- `ifitwala_ed/docs/docs_md/learning-unit.md`
- `ifitwala_ed/docs/docs_md/lesson.md`
- `ifitwala_ed/docs/docs_md/lesson-activity.md`
- `ifitwala_ed/docs/docs_md/class-session.md`
- `ifitwala_ed/docs/docs_md/lesson-instance.md`
- `ifitwala_ed/docs/docs_md/material-placement.md`
- `ifitwala_ed/docs/docs_md/task.md`
- `ifitwala_ed/docs/docs_md/task-delivery.md`

## Technical Notes (IT)

Status: Planned
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/planning.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`

### Implementation Stance

- This contract locks the target architecture for forward implementation.
- It does not claim the live schema already matches the target model.
- Until the replatform lands, current runtime docs remain implementation-accurate for the old stack.
- The implementation plan for the redesign is tracked in `ifitwala_ed/docs/curriculum/02_educator_centered_curriculum_replatform_plan.md`.

### First Slice Landed

- The educator-centered first slice now exists in code through `Course Plan`, `Unit Plan`, `Class Teaching Plan`, and `Class Session`.
- Staff planning now has a route-based `ui-spa` surface in `ui-spa/src/pages/staff/ClassPlanning.vue` backed by `ifitwala_ed.api.teaching_plans.get_staff_class_planning_surface`.
- Student course detail now reads from the class-aware LMS endpoint `ifitwala_ed.api.teaching_plans.get_student_learning_space` and no longer depends on the old lesson-tree page contract.
- `Lesson Instance` has been retired from code. `Task Delivery`, Class Hub contracts, student reflections, and student-home work items now use `Class Session` instead.
- Assessment and resource re-anchoring are still follow-on work; the current implementation covers class-session anchoring, but the resource model reset still remains.
