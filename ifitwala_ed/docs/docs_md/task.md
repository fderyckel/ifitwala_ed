---
title: "Task: The Reusable Learning and Assessment Blueprint"
slug: task
category: Assessment
doc_order: 4
version: "1.8.3"
last_change_date: "2026-04-20"
summary: "Author reusable learning tasks once, then deliver them to groups with the right grading mode, evidence expectations, and task-specific supporting materials."
seo_title: "Task: The Reusable Learning and Assessment Blueprint"
seo_description: "Author reusable learning tasks once, then deliver them to groups with the right grading mode, evidence expectations, and rubric strategy."
---

## Task: The Reusable Learning and Assessment Blueprint

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/api/task.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task/test_task.py`)

`Task` is the reusable definition layer for learning work. It holds author intent, instructions, default assessment behavior, and default comment policy, but it is not itself assigned to a class.

Current workspace note: the task definition model is in place, the overlay now supports both create-new and assign-existing flows, and task materials live in the separate `Supporting Material` plus `Material Placement` domain instead of competing with planning content.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task/task.js`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task/test_task.py`)

- Create the default `Course` first because `default_course` is required.
- Prepare supporting assessment masters first: `Assessment Category`, `Grade Scale`, and reusable `Assessment Criteria`.
- Stabilize task design before creating downstream `Task Delivery` records.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/api/task.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/api/student_overview_dashboard.py`, `ifitwala_ed/api/morning_brief.py`
Test refs: None

- [**Task Delivery**](/docs/en/task-delivery/) references `Task` as the assignable source.
- [**Unit Plan**](/docs/en/unit-plan/) is the deepest current curriculum anchor available on the task definition.
- [**Task Rubric Version**](/docs/en/task-rubric-version/) snapshots `Task Template Criterion` rows at delivery launch.
- [**Task Outcome**](/docs/en/task-outcome/), [**Task Submission**](/docs/en/task-submission/), and [**Task Contribution**](/docs/en/task-contribution/) inherit delivery/task context.
- Staff portal planning uses the create-task overlay at `ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`.
- Task-specific reusable materials are shared through [**Supporting Material**](/docs/en/supporting-material/) and [**Material Placement**](/docs/en/material-placement/).
- `ifitwala_ed/api/task.py` exposes `search_reusable_tasks`, `search_tasks`, `get_task_for_delivery`, and `create_task_delivery`.
- Student Overview now reads the current `Task Delivery` plus `Task Outcome` model for learner analytics.
- Some briefing readers still reference legacy `Task` plus `Task Student` style paths:
  - `ifitwala_ed/api/morning_brief.py`

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/task.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task/test_task.py`)

1. Author the reusable task definition with required curriculum anchor (`default_course`) and optional deeper planned-curriculum anchor (`unit_plan`).
2. Configure default delivery, grading, and comment behavior, including optional `task_criteria` rows.
3. Create a `Task Delivery` as the execution instance for a specific `Student Group`.
4. Downstream outcomes, submissions, contributions, and rubric snapshots should inherit delivery/task context.

Current workspace note: there are now two intentional launch paths. New work uses `assessment/task_creation_service.py`; reusing an existing task uses `api/task.py::create_task_delivery()` plus `assessment/task_delivery_service.py`. Both create class-scoped deliveries without rewriting shared reusable task definitions.

## Permission Matrix

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/api/task.py`, `ifitwala_ed/assessment/task_creation_service.py`
Test refs: None

- `System Manager`, `Academic Admin`, `Curriculum Coordinator`, and `Instructor` currently manage `Task` through the live schema/API contract.
- The current `Task` schema does not yet distinguish shared-baseline tasks from class-originated tasks through a dedicated ownership field.
- Shared-plan governance and class-plan scope are therefore enforced by the surrounding planning and delivery flows, not by a `Task`-only ownership model.
- Teachers can always reuse their own course tasks again across their classes and later school years.
- Other teachers on the same course can reuse a task only when the author explicitly marks it for the course task library through `is_template`.
- Students and guardians do not manage raw `Task` records directly; they consume assigned work through `Task Delivery`-driven LMS payloads.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task Delivery**](/docs/en/task-delivery/)
- [**Unit Plan**](/docs/en/unit-plan/)
- [**Class Session**](/docs/en/class-session/)
- [**Task Template Criterion**](/docs/en/task-template-criterion/)
- [**Task Rubric Version**](/docs/en/task-rubric-version/)
- [**Task Outcome**](/docs/en/task-outcome/)
- [**Assessment Criteria**](/docs/en/assessment-criteria/)
- [**Grade Scale**](/docs/en/grade-scale/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task/task.js`, `ifitwala_ed/assessment/task_creation_service.py`
Test refs: `ifitwala_ed/utilities/test_governed_uploads_task_flows.py`

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task/task.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task/task.py`
- **Desk client script**: `ifitwala_ed/assessment/doctype/task/task.js`
- **Required fields (`reqd=1`)**:
  - `title` (`Data`)
  - `default_course` (`Link` -> `Course`)
- **Child tables**:
  - `attachments` (`Attached Document`)
  - `task_criteria` (`Task Template Criterion`)
- **Lifecycle hooks in controller**:
  - `before_validate`
  - `validate`
  - `on_trash`

### Current Contract

- `Task` is the reusable definition artifact. It is not the grading fact table.
- A task may be authored directly for shared reuse or originate from one class workflow, but the current schema does not yet persist that distinction as a dedicated governance field.
- `task.py` enforces curriculum alignment, duplicate criterion guards, and coherent default grading configuration.
- `Task` also carries `default_allow_feedback`, which decides whether downstream deliveries should expose a comment box by default.
- `task.js` filters `unit_plan` and quiz-bank choices by course context, clears stale curriculum links when course changes, and replaces generic Task resource uploads with the governed Task-resource action.
- `task.py` now treats `attachments` as a legacy compatibility surface only: new reusable task materials live in `Supporting Material` and are shared onto the task through `Material Placement`.
- The current task schema stops at `unit_plan`; it does not expose `class_session`.
- `is_template` now controls whether the task is intentionally shared with the course team for reuse. It still does not promote the task into governed curriculum or common-assessment baseline space.
- `assessment/task_creation_service.py` supports the overlay path that creates both `Task` and `Task Delivery` in one transaction.
- `api/task.py::search_reusable_tasks()` resolves one course-scoped task library at a time and returns only the current user's own tasks plus tasks explicitly shared with that course team.
- `api/task.py::create_task_delivery()` now owns the assign-existing-task flow and validates that private tasks stay private until shared.
- The task overlay now treats create-and-assign as the first step of one continuous workflow, then transitions into a governed task-attachment step before the teacher closes the overlay.
- That attachment step supports governed PDF and image uploads only, uses the shared SPA attachment preview card, and keeps the class-planning page refresh deferred until the teacher finishes and closes the overlay once.
- The task overlay does not expose task-material editing after reusing an existing task, because class-local delivery work must not silently mutate a shared reusable definition.
- No current workflow may treat a task created from one class/session flow as silently promoted shared curriculum just because it is reusable later.

### Current Drift To Preserve In Review

- The definition layer is stable, but downstream launch remains split across two services.
- Student Overview now reads the current `Task Delivery` plus `Task Outcome` contract, but some older briefing readers still reference legacy structures; those reads must not be mistaken for the canonical gradebook contract.
- Any implementation change that alters task-launch behavior must update this page and the linked delivery/outcome docs in the same change.
