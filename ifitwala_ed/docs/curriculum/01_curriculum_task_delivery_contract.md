# Educator-Centered Curriculum, Planning, and Assigned Work Contract

Status: Canonical current-state contract
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/class_session_activity/class_session_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanIndex.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/components/planning/course-plan-workspace/CoursePlanUnitEditor.vue`, `ifitwala_ed/ui-spa/src/components/planning/course-plan-workspace/CoursePlanQuizBanksSection.vue`, `ifitwala_ed/ui-spa/src/lib/planning/coursePlanWorkspace.ts`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/curriculum/doctype/unit_plan/test_unit_plan.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

This is the live source of truth for how curriculum planning, class delivery, and class-assigned work fit together in Ifitwala_Ed.

This document governs the curriculum spine itself. Resource sharing is governed by `03_curriculum_materials_and_resource_contract.md`. Student LMS and quiz runtime behavior are governed by `04_curriculum_lms_and_quiz_contract.md`.

## Product Boundary

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/api/test_teaching_plans.py`

The live curriculum model is split into three layers:

- Shared curriculum:
  `Course Plan` and `Unit Plan`
- Class planning and enacted teaching:
  `Class Teaching Plan`, `Class Session`, and `Class Session Activity`
- Assigned work:
  reusable `Task` plus class-scoped `Task Delivery`

This split is locked.

- Shared curriculum defines the governed backbone.
- Class planning adapts that backbone for one real class.
- Assigned work remains explicit runtime work for a class; it is not the planning model.

## Live Runtime Reality

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/curriculum/doctype/unit_plan/test_unit_plan.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/api/test_teaching_plans.py`

- `Learning Unit` is no longer part of the live runtime; `Unit Plan` owns the shared unit backbone.
- `Lesson`, `Lesson Activity`, and `Lesson Instance` are not part of the live curriculum runtime.
- The student learning surface no longer depends on the old lesson-instance tree.
- `Task Delivery` now requires `Class Teaching Plan` and may also link to `Class Session`.
- `Task` now anchors at `default_course` with optional `unit_plan`; it does not carry a lesson link.

## Shared Curriculum Layer

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course_plan/course_plan.json`, `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`
Test refs: `ifitwala_ed/curriculum/doctype/unit_plan/test_unit_plan.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`

- `Course Plan` is the governed version of the intended curriculum for a course.
- A `Course` may have multiple `Course Plan` records.
- `Unit Plan` is the mandatory shared unit backbone inside a course plan.
- Shared planning is created and edited in the staff SPA course-plan index and workspace, not as a Desk-first teacher workflow.

Governance rule:

- shared outcomes
- shared unit sequence
- governed standards alignment
- shared reflections and shared curricular metadata

belong to the shared plan layer unless an explicit design says otherwise.

Ownership rule:

- instructors attached to at least one `Student Group` for a course may create and edit the shared `Course Plan`, `Unit Plan`, quiz banks, and shared curriculum resources for that course
- curriculum coordinators and academic administrators may also manage shared curriculum for the courses they govern
- shared curriculum is course-team owned; it is not limited to a coordinator-only workflow
- rollover-generated draft next-year `Course Plan` rows stay visible on the staff course-plan index only to `Curriculum Coordinator`; that visibility carve-out is for handover control, not a general restriction on shared curriculum authoring

## Class Planning Layer

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/class_teaching_plan/class_teaching_plan.json`, `ifitwala_ed/curriculum/doctype/class_teaching_plan_unit/class_teaching_plan_unit.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`, `ifitwala_ed/curriculum/doctype/class_session_activity/class_session_activity.json`, `ifitwala_ed/curriculum/planning.py`, `ifitwala_ed/schedule/doctype/student_group/student_group.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`
Test refs: `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`

- `Class Teaching Plan` is the class-owned planning layer for one teaching group.
- Every class teaching plan must point to exactly one governing `Course Plan`.
- Creating an active course-based `Student Group` auto-provisions one active `Class Teaching Plan` when exactly one active governing `Course Plan` can be resolved for that course and academic-year context. Draft rollover plans must not become governing class truth before activation. If course-plan resolution is missing or ambiguous, class-plan creation remains an explicit Class Planning step, and that manual Class Planning create-plan action also initializes the plan as `Active`.
- `Class Session` is the educator-facing lifecycle object for a real teaching event.
- `Class Session Activity` is the ordered session flow inside one class session.

Class-planning rule:

- teachers adapt pacing, activity sequence, examples, and class-owned resources in the class layer
- they do not mutate the shared backbone just to teach one class
- sibling classes must not see each other's class-owned planning or resources

## Assigned Work Contract

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/task.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`
Test refs: `ifitwala_ed/assessment/test_task_creation_service.py`, `ifitwala_ed/assessment/test_task_delivery_service.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

- `Task` is the reusable work definition.
- `Task Delivery` is the class-scoped runtime assignment.
- A task may be authored directly for shared reuse or originate from one class flow; ownership semantics are governed by the persistence rules below, not guessed from the doctype name alone.
- A task may be shared or reused; assignment is still explicit per class.
- A task delivery must belong to one `Student Group` and one `Class Teaching Plan`.
- A task delivery may also point at a `Class Session` when the assignment is session-specific.

Product rule:

- assigned work is a teaching outcome of the curriculum flow
- assigned work is not a substitute for missing planning objects
- common work definitions do not imply that a class has actually received that work
- draft or archived class teaching plans are not valid substitutes for the active class-planning anchor required by assigned work

## Shared Versus Local Work Persistence

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/api/task.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`
Test refs: `ifitwala_ed/assessment/test_task_creation_service.py`, `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

Locked product rule:

- work created from one class-planning or class-session flow is class-originated by default
- a shared reusable task or common-assessment baseline must be authored intentionally in shared planning or promoted explicitly from class-originated work
- reusing a shared task in one class does not authorize that class to rewrite the shared baseline
- local edits to dates, release policy, scaffolds, instructions, or class-owned resources must remain local to that class assignment unless an explicit promotion or update workflow is run
- no implicit upstream sync is allowed from one class back into shared curriculum

Current workspace reality:

- the current `Task` schema stores `default_course`, optional `unit_plan`, and `is_template`; it does not yet store a first-class ownership state such as `shared_baseline` versus `class_authored`
- the current create flow already captures class context through required `Task Delivery.class_teaching_plan` and optional `Task Delivery.class_session`
- `is_template` now marks whether a reusable task is intentionally shared with the course team. It does not promote the task into governed curriculum or common-assessment baseline space
- `api/task.py::search_reusable_tasks()` and `api/task.py::search_tasks()` now expose a course-scoped reusable-task library, not a broad unscoped task read. The current user sees their own tasks for that course plus tasks the course team explicitly shared
- same-teacher reuse across multiple groups or later school years works through task ownership; cross-teacher reuse on the same course requires explicit course-library sharing
- `api/task.py::create_task_delivery()` now covers the assign-existing workflow. Delivery edits remain class-local and do not rewrite the reusable task definition
- explicit promotion from class-originated work into shared reusable or common-assessment baseline space is still not a dedicated governance workflow; treat that as an implementation gap, not permission to blur ownership

## Resolution Rules For Read Surfaces

Status: Implemented
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/teaching_plans_timeline.py`, `ifitwala_ed/api/class_hub.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_class_hub.py`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/CoursePlanWorkspace.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/ClassPlanning.test.ts`

Read surfaces must resolve in this order:

1. explicit class truth:
   in-progress `Class Session`, or exactly one class unit marked `In Progress`
2. calendar truth:
   shared unit sequence resolved from `Unit Plan.duration`, the academic-year window, and the resolved school calendar with weekends and holidays applied
3. dated class truth:
   exact-date session, then nearest dated or undated session inside the resolved unit context
4. shared course-plan and unit-plan fallback when no class teaching plan is available
5. explicit blocked or unavailable state when neither current class truth nor calendar truth can resolve a unit

Non-negotiable rules:

- no sibling class bleed
- no client-side reconstruction of curriculum ownership
- one bounded bootstrap per page mode where practical
- no silent fallback to Desk when the SPA or LMS owns the workflow
- the current-unit resolver is server-owned and must be reused across student, guardian, staff course-plan, staff class-planning, and Class Hub surfaces
- between two scheduled units, weekends and holiday gaps keep the previous scheduled unit current until the next scheduled unit actually starts
- route or query overrides may change what the user is viewing, but default opening context must come from the shared resolver rather than a first-unit guess

## Permissions And Scope

Status: Implemented
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/curriculum/planning.py`, `ifitwala_ed/assessment/task_delivery_service.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/assessment/test_task_delivery_service.py`

- Instructors manage class planning for the classes they teach.
- Instructors listed on at least one `Student Group` for a course may also create and edit that course's shared curriculum.
- Shared curriculum authority is resolved from the `Student Group Instructor` relationship to `Student Group.course`, with administrative curriculum roles layered on top.
- Students read only the curriculum resolved for their own class context.
- Shared curriculum does not imply permission to read class-owned notes or class-owned resources.
- All scope enforcement stays server-side.

## Guardrails

Status: Locked
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/curriculum/planning.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/assessment/test_task_delivery_service.py`

Do not:

- reintroduce one shared lesson tree as the runtime truth for planning, delivery, and history
- store class-specific pacing or teacher-only execution detail on shared curriculum by default
- use assigned work or resource placement as a workaround for missing class-planning data
- build lesson-tree client waterfalls on student or staff hot paths
- reintroduce retired lesson doctypes as a shadow planning layer

## Related Docs

Status: Canonical map
Code refs: None
Test refs: None

- `ifitwala_ed/docs/curriculum/02_educator_centered_curriculum_replatform_plan.md`
- `ifitwala_ed/docs/curriculum/03_curriculum_materials_and_resource_contract.md`
- `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`

## Technical Notes (IT)

Status: Canonical
Code refs: `ifitwala_ed/curriculum/planning.py`, `ifitwala_ed/schedule/doctype/student_group/student_group.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`
Test refs: `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/assessment/test_task_creation_service.py`, `ifitwala_ed/assessment/test_task_delivery_service.py`

- `get_student_learning_space` is the student bootstrap. Do not rebuild the student curriculum reader on `api/courses.py` lesson-tree payloads.
- `get_staff_class_planning_surface`, `list_staff_course_plans`, and `get_staff_course_plan_surface` are the staff read-model owners for curriculum planning.
- The staff course-plan workspace may be split into reusable section components and shared planning helpers, but `CoursePlanWorkspace.vue` plus `get_staff_course_plan_surface` remain the sole route/bootstrap/read-model owners. Future analytics or adjunct panels must compose onto that bounded surface instead of adding independent curriculum waterfalls.
- `create_course_plan` is the canonical mutation for starting a new governed course plan from the SPA index.
- Desk `Course Plan` also owns the year-handover action for creating the next academic-year governed plan. That Desk flow creates a draft target plan, duplicates governed units, reuses shared material placements on the new anchors, and may schedule activation for the linked academic-year start date.
- `StudentGroup.after_insert()` calls `planning.bootstrap_student_group_class_teaching_plan(...)` so course-based class setup can create the default class-plan anchor in one save when course-plan resolution is unambiguous.
- Shared course-plan editing rights are not derived from static DocType role writes; they are resolved from active teaching assignments on `Student Group`.
- `Task Delivery` remains the live doctype name. Educator-facing language can evolve, but workflow invariants and schema claims must be grounded in the current files.
- Any future change that alters plan ownership, read-order, or class-scoped assignment rules must update this document and the LMS/resource contracts in the same change.
