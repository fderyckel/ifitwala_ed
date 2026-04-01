## Materials Guideline

Status: Canonical guideline
Code refs: `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`
Test refs: None

This document is the product and architecture guideline for learning materials in Ifitwala_Ed.

## Core Contract

Status: Locked
Code refs: `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/assessment/doctype/task/task.json`
Test refs: None

The learning stack is split into three distinct layers:

- `Lesson` and `Lesson Activity` are the authored teaching flow.
- `Materials` are reusable, separately openable supporting items.
- `Tasks` are student action, submission, and assessment.

This split is non-negotiable. Materials must not compete with lesson content.

## Decision Rule

Status: Locked
Code refs: `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/docs/docs_md/lesson-activity.md`, `ifitwala_ed/docs/docs_md/task.md`
Test refs: None

- If the teacher is writing or sequencing instruction, it belongs in the lesson.
- If the teacher is sharing something students open separately, it belongs in materials.
- If the teacher is assigning work, it belongs in tasks.

Examples:

- Reading text inside a lesson activity stays lesson content.
- A video URL inside a lesson activity stays lesson content unless the teacher wants it reused outside that lesson flow.
- A PDF handout, worksheet, slide deck, exemplar, or reusable reference link is a material.

## Allowed Material Types

Status: Locked for v1
Code refs: None
Test refs: None

`Materials` in v1 support:

- governed file-backed materials via `ifitwala_drive`
- reusable reference links

`Materials` do not represent:

- rich lesson text
- discussion prompts
- the primary instructional body of a lesson

## Placement Model

Status: Locked
Code refs: `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/materials.py`
Test refs: None

Materials are reusable objects that can be placed into one or more curriculum contexts.

Valid placement targets:

- `Course Plan`
- `Unit Plan`
- `Class Teaching Plan`
- `Class Session`
- `Task`

Each placement carries usage context such as:

- origin
- role in student workflow
- teacher note
- ordering

Removing a material from a plan, class, session, or task means unsharing that placement. It does not delete the underlying material.

## Class Sharing Rule

Status: Locked
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/curriculum/materials.py`
Test refs: None

Class-shared materials always persist.

Class sharing must resolve to a real curriculum anchor:

- persist to `Class Session` when the resource is specific to one planned/taught class session
- otherwise persist to the `Class Teaching Plan`

Retain `shared_in_class` as origin metadata. Do not create a session-only materials library.

## Student LMS Rule

Status: Locked
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: None

Students need one clear materials shelf inside the course LMS.

That shelf must aggregate the materials shared through:

- the current class session
- the class teaching plan
- the current unit plan
- the governing course plan
- the tasks visible in that course context

The LMS should never force students to hunt across tasks and lessons just to find supporting materials.

## Teacher Authoring Rule

Status: Locked
Code refs: `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`
Test refs: None

Teachers should add materials where they already work.

Priority entry points:

- task overlay
- class teaching plan and class session planning
- shared course plan and unit planning

The task overlay is the first required product-quality authoring surface because it already owns the teacher’s assignment creation flow.

## Permissions

Status: Locked
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/students/doctype/student_log/student_log.py`
Test refs: None

- Students only see materials shared into accessible course contexts.
- Teachers can manage materials only in contexts they teach or administratively manage.
- Curriculum coordinators always have read access to materials for courses inside their coordinated programs.
- Visibility must be enforced server-side.

## File Governance

Status: Locked
Code refs: `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`, `ifitwala_ed/integrations/drive/bridge.py`
Test refs: None

`ifitwala_ed` owns context, permissions, and placement.

`ifitwala_drive` owns:

- governed upload session creation
- finalize
- storage
- file authority

Materials must not guess storage paths or raw private URLs. Student and staff file opens must use server-resolved URLs.

## Guardrails

Status: Locked
Code refs: `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/docs/spa/classhub/class_hub_proposal.md`
Test refs: None

Do not:

- turn `Lesson Activity` into a material manager
- duplicate lesson text inside materials
- let Class Hub become a generic library
- hard-delete the underlying file when a teacher only means to unshare it
- expose raw private file paths in the LMS or SPA

## Current Delivery Expectation

Status: Partial
Code refs: `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: None

The first implemented slice should prove the contract in real workflows:

- first-class material objects and placements
- task-overlay authoring for file and link materials
- shared course-plan and unit resource authoring in the staff SPA
- class-plan and class-session resource authoring in the staff SPA
- student LMS materials shelf inside the class-aware learning space
