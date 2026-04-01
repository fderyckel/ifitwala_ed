# Educator-Centered Curriculum Replatform Plan

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/planning.py`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/api/task.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`

This note is the implementation plan for the redesign locked in `01_curriculum_task_delivery_contract.md`.

Because the product is still in development and there is no production compatibility burden, this plan assumes:

- no backward-compatibility shims
- no dual model kept alive for legacy consumers
- destructive schema replacement is allowed when it produces a cleaner educator-centered architecture
- docs, schema, APIs, and SPA surfaces will be updated as one coordinated redesign rather than a thin patch on the current lesson-centric model

This plan also assumes the canonical product-surface decision is locked:

- staff curriculum planning and class-session planning must live in `ui-spa`
- student curriculum and lesson consumption must live in the LMS/student portal
- Desk may expose underlying records for governance and administration, but not as the primary planning workflow for teachers or the primary learning workflow for students
- each SPA page mode should use one bounded bootstrap endpoint wherever practical, in line with `ifitwala_ed/docs/high_concurrency_contract.md`

## Locked Design Rules

Status: Planned
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/schedule/doctype/student_group/student_group.json`
Test refs: None yet

This plan now proceeds with the following locked design rules:

- a `Course` may have multiple `Course Plan` records, including concurrent plans in the same year or cycle
- each `Class Teaching Plan` must link to exactly one governing `Course Plan`
- co-taught classes use one shared `Class Teaching Plan`
- educator-specific planning overlays are out of scope for the first implementation
- `Class Session` is one lifecycle object from planning through taught state
- the governed subset across class teaching plans includes:
  - shared outcomes
  - mandatory `Unit Plan` backbone and sequence
  - required common assessments
  - any explicitly governed anchor resources
- pacing within a unit, session design, activity sequence, examples, and most resources remain class-owned by default
- educator-facing language takes priority in Desk labels, SPA labels, and canonical docs
- planning UX is SPA-first for staff and LMS-first for students
- no Desk-first fallback workflow should be introduced for teacher planning
- each planning or LMS page mode must bootstrap through one bounded read endpoint rather than client waterfalls

## Workstream 1: Semantics And Documentation

Status: Partial
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/docs_md/course.md`, `ifitwala_ed/docs/docs_md/learning-unit.md`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/lesson-activity.md`, `ifitwala_ed/docs/docs_md/lesson-instance.md`, `ifitwala_ed/docs/docs_md/material-placement.md`, `ifitwala_ed/docs/docs_md/task.md`, `ifitwala_ed/docs/docs_md/task-delivery.md`, `ifitwala_ed/docs/docs_md/student-group.md`
Test refs: None

Required changes:

- Lock the educator-centered vocabulary in canonical docs first.
- Rewrite the feature pages that currently describe the old lesson-centric model.
- State explicitly that staff planning lives in `ui-spa` and student lesson consumption lives in the LMS.
- Replace backend-first labels in docs with educator-facing semantics:
  - `Student Group` -> `Class` or `Teaching Group`
  - `Lesson Instance` -> `Class Session`
  - `Task Delivery` -> `Assigned Work for Class`
  - `Material Placement` -> `Resource Share` or equivalent
- Keep each rewritten doc honest about implementation status while the schema is still changing.

Follow-on docs to update during implementation:

- `ifitwala_ed/docs/docs_md/course.md`
- `ifitwala_ed/docs/docs_md/learning-unit.md`
- `ifitwala_ed/docs/docs_md/lesson.md`
- `ifitwala_ed/docs/docs_md/lesson-activity.md`
- `ifitwala_ed/docs/docs_md/lesson-instance.md`
- `ifitwala_ed/docs/docs_md/material-placement.md`
- `ifitwala_ed/docs/docs_md/task.md`
- `ifitwala_ed/docs/docs_md/task-delivery.md`
- any student-hub or class-hub SPA contracts that reference the old lesson tree

## Workstream 2: Core Curriculum Schema Reset

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/course/course.json`, `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/planning.py`
Test refs: None yet for backend curriculum controller coverage

Recommended target objects:

- keep `Course`
- add `Course Plan`
- replace or rename `Learning Unit` into `Unit Plan`
- replace the heavy shared `Lesson` concept with optional `Suggested Session Outline`
- add `Class Teaching Plan`
- replace `Lesson Instance` with `Class Session`
- replace `Lesson Activity` with `Session Activity`

Recommended stance:

- Prefer a clean schema reset over repurposing overloaded doctypes with misleading names.
- Because there is no production history to preserve, the cleaner option is to create or rename doctypes to match the target educator model directly.
- Avoid carrying `Lesson`, `Lesson Activity`, and `Lesson Instance` forward under the same semantics if they now mean different things.
- Model `Course Plan` as a distinct governed record rather than treating academic year alone as the course-versioning mechanism.
- Model `Unit Plan` inheritance as mandatory backbone data that every `Class Teaching Plan` must receive from its governing `Course Plan`.

Files likely to change or be retired:

- `ifitwala_ed/curriculum/doctype/learning_unit/*`
- `ifitwala_ed/curriculum/doctype/lesson/*`
- `ifitwala_ed/curriculum/doctype/lesson_activity/*`
- retired `ifitwala_ed/curriculum/doctype/lesson_instance/*`
- workspace/sidebar entries that expose the old curriculum stack

## Workstream 3: Class Planning And Session Lifecycle

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/schedule/doctype/student_group/student_group.json`, `ifitwala_ed/schedule/doctype/student_group/student_group.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/lib/services/staff/staffTeachingService.ts`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`

Required changes:

- Introduce `Class Teaching Plan` as the class-owned planning layer between shared curriculum and daily sessions.
- Require every `Class Teaching Plan` to inherit one governed `Course Plan` and its mandatory `Unit Plan` sequence.
- Promote `Class Session` into the primary educator-facing session object.
- Define explicit session lifecycle states and ownership rules.
- Treat co-teaching as one shared class-planning truth for the same class.
- Surface curriculum planning directly in `ui-spa` for staff instead of relying on Desk forms as the primary workflow.
- Persist real session planning behavior in the SPA instead of the current lesson-instance/demo placeholder path.
- Support class-specific pacing and substitutions without mutating the shared course plan.

Implementation progress:

- first route-based staff planning surface landed in `ui-spa/src/pages/staff/ClassPlanning.vue`
- staff bootstrap and mutations landed in `ifitwala_ed.api.teaching_plans`
- `Class Hub` now links directly into the planning surface

Key file owners likely to change:

- `ifitwala_ed/api/class_hub.py`
- `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`
- `ifitwala_ed/ui-spa/src/lib/classHubService.ts`
- `ifitwala_ed/ui-spa/src/types/classHub*`
- any future Desk or SPA planning surfaces for educators

## Workstream 4: Assessment And Work Delivery Reframe

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/task.py`, `ifitwala_ed/api/gradebook.py`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/assessment/test_task_creation_service.py`, `ifitwala_ed/assessment/test_task_delivery_service.py`, `ifitwala_ed/api/test_gradebook.py`

Required changes:

- Re-anchor reusable task definitions to the redesigned shared curriculum layer:
  - `Course`
  - `Course Plan`
  - `Unit Plan`
  - optional `Suggested Session Outline`
- Reframe `Task Delivery` as class-scoped assigned work, not as a surrogate teaching-plan object.
- Decide whether class-assigned work links to `Class Teaching Plan`, `Class Session`, or both.
- Unify the split launch path between `task_creation_service.py` and `task_delivery_service.py`.
- Update educator-facing labels in overlays and gradebook surfaces.

Implementation progress:

- `Task Delivery` now optionally links to `Class Session` instead of `Lesson Instance`.
- delivery validation now checks that a selected `Class Session` belongs to the same class, course, and academic year.
- implicit lesson-instance creation from delivery flows has been removed.

Files likely to change:

- `ifitwala_ed/assessment/doctype/task/*`
- `ifitwala_ed/assessment/doctype/task_delivery/*`
- `ifitwala_ed/assessment/task_creation_service.py`
- `ifitwala_ed/assessment/task_delivery_service.py`
- `ifitwala_ed/api/task.py`
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`

## Workstream 5: Resource And Material Model Reset

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/courses.py`
Test refs: `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`, `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/api/test_courses.py`

Required changes:

- Replace the current course-only placement model with class-aware resource sharing.
- Support anchors for the redesigned educator model:
  - `Course Plan`
  - `Unit Plan`
  - optional `Suggested Session Outline`
  - `Class Teaching Plan`
  - `Class Session`
  - `Task`
- Ensure student and teacher read paths resolve class/session resources before shared plan resources.
- Preserve governed file access through the existing file-governance boundary.

Files likely to change:

- `ifitwala_ed/curriculum/materials.py`
- `ifitwala_ed/curriculum/doctype/material_placement/*`
- `ifitwala_ed/api/materials.py`
- `ifitwala_ed/api/courses.py`
- any student or class read contracts that serialize materials

## Workstream 6: Student And Staff Read Models

Status: Partial
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/lib/services/student/studentLearningHubService.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`
Test refs: `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

Required changes:

- Make the student learning surface class-aware by default rather than course-only.
- Resolve content in this order:
  1. class teaching plan
  2. class session
  3. shared course plan fallback
- Replace the old student course-detail bootstrap with a class-aware endpoint.
- Keep a single bounded bootstrap payload for the student surface.
- Rewrite the LMS/student course page around the educator-centered class-aware learning-space payload.
- Ensure the student LMS view favors current class sessions and unit backbone context over the old lesson tree.

Implementation progress:

- the old `get_student_course_detail` lesson-tree bootstrap has been removed from `ifitwala_ed/api/courses.py`
- student home/work-board links now carry class context into the LMS route through `student_group`

Files likely to change:

- `ifitwala_ed/api/teaching_plans.py`
- `ifitwala_ed/api/class_hub.py`
- `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/lib/services/student/studentLearningHubService.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`

## Workstream 7: Permissions, Scope, And Multi-Tenant Safety

Status: Planned
Code refs: `ifitwala_ed/schedule/doctype/student_group/student_group.py`, `ifitwala_ed/api/student_groups.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`, `ifitwala_ed/api/test_gradebook.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

Required rules:

- Class planning and class sessions must be visible only to permitted educators, school leaders, and enrolled students where appropriate.
- Shared course plans must not leak class-owned materials or teacher notes.
- All class-owned reads must remain scoped through class membership and school hierarchy.
- Structural changes to the governed `Unit Plan` backbone must be blocked or warning-gated for normal teaching roles and reserved for explicit governance permission.
- Resource read permissions must be updated together with file-visibility tests.
- No client-side scope math may replace server-side permission checks.

## Workstream 8: Desk, Workspace, And Label Rewrite

Status: Planned
Code refs: `ifitwala_ed/curriculum/workspace/curriculum/curriculum.json`, `ifitwala_ed/workspace_sidebar/curriculum.json`, `ifitwala_ed/schedule/doctype/student_group/student_group.json`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`
Test refs: None yet

Required changes:

- Update workspace and Desk labels to educator-centered language.
- Remove or rename menu entries that expose obsolete technical semantics.
- Ensure the default educator mental model is:
  - Course
  - Course Plan
  - Unit Plan
  - Class Teaching Plan
  - Class Session
- Avoid leaving renamed concepts only in documentation while forms and pages still show backend-first labels.
- Keep the primary teacher workflow in `ui-spa`; workspace links should support governance/admin access, not displace the SPA planning surface.

## Workstream 9: Testing And Acceptance Criteria

Status: Planned
Code refs: current owners listed above
Test refs: current suites listed above plus new redesign-specific suites

Minimum required coverage:

- shared curriculum ownership rules
- multiple `Course Plan` records per `Course`, with each `Class Teaching Plan` bound to exactly one governing plan
- class teaching plan ownership and scope
- mandatory `Unit Plan` inheritance and guarded structural changes
- class session lifecycle
- shared class-teaching-plan behavior for co-taught classes
- class-first read resolution with shared fallback
- resource visibility by class and role
- assigned-work launch and gradebook flows under the new model
- student learning hub contract tests
- class hub contract tests
- staff planning surface contract tests
- multi-tenant sibling isolation for class-owned artifacts

New test families likely required:

- curriculum replatform controller tests
- class teaching plan permission tests
- unit backbone inheritance and exception-permission tests
- class session lifecycle tests
- co-teaching shared-plan tests
- student-hub contract tests for class-aware payloads
- resource placement/read tests for class and session anchors

## Workstream 10: Retirement Of The Old Lesson-Centric Model

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/learning_unit/*`, `ifitwala_ed/curriculum/doctype/lesson/*`, `ifitwala_ed/curriculum/doctype/lesson_activity/*`, `ifitwala_ed/curriculum/doctype/material_placement/*`
Test refs: all suites that still assume the old model

Because there is no production legacy requirement:

- do not keep long-lived compatibility shims
- do not preserve misleading doctypes purely to avoid rename work
- remove obsolete fields, APIs, docs, and SPA routes once replacements land
- prefer one clear educator-centered workflow path over dual-model coexistence

Implementation progress:

- `Lesson Instance` has been removed from the live codebase
- the old student lesson-tree API path has been removed
- published docs are being rewritten so the retired object remains documented only as a deprecation note

## Recommended Execution Order

Status: Planned
Code refs: all workstreams above
Test refs: all workstreams above

1. Translate the locked governance decisions into schema and labels first.
2. Lock semantics in docs and UI labels.
3. Replace the overloaded curriculum doctypes with the new shared curriculum and class-planning layers.
4. Re-anchor assessment and materials to the new model.
5. Rebuild student and staff read models around class-first resolution.
6. Update permissions and file visibility rules.
7. Rewrite tests to prove the new contract.
8. Remove the old lesson-centric model and stale docs in the same change set.

## Technical Notes (IT)

Status: Planned
Code refs: all workstreams above
Test refs: all workstreams above

### Delivery Principle

This redesign should be executed as a deliberate replatform, not a patch series that preserves misleading semantics.

The product should optimize for how educators actually think:

- shared course intent
- class-level planning
- class sessions
- assigned work
- resources

The implementation should not optimize for preserving current Frappe-facing names when those names no longer match the product model.
