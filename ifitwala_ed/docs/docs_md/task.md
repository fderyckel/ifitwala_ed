---
title: "Task: The Reusable Learning and Assessment Blueprint"
slug: task
category: Assessment
doc_order: 4
version: "1.4.0"
last_change_date: "2026-04-01"
summary: "Author reusable learning tasks once, then deliver them to groups with the right grading mode, evidence expectations, and task-specific supporting materials."
seo_title: "Task: The Reusable Learning and Assessment Blueprint"
seo_description: "Author reusable learning tasks once, then deliver them to groups with the right grading mode, evidence expectations, and rubric strategy."
---

## Task: The Reusable Learning and Assessment Blueprint

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/api/task.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task/test_task.py`)

`Task` is the reusable definition layer for learning work. It holds author intent, instructions, and default assessment behavior, but it is not itself assigned to a class.

Current workspace note: the task definition model is in place, downstream launch paths are still split between the direct delivery service and the create-task overlay transaction, and task materials now live in the separate `Supporting Material` plus `Material Placement` domain instead of competing with lesson content.

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
- [**Learning Unit**](/docs/en/learning-unit/) and [**Lesson**](/docs/en/lesson/) are the deepest current curriculum anchors available on the task definition.
- [**Task Rubric Version**](/docs/en/task-rubric-version/) snapshots `Task Template Criterion` rows at delivery launch.
- [**Task Outcome**](/docs/en/task-outcome/), [**Task Submission**](/docs/en/task-submission/), and [**Task Contribution**](/docs/en/task-contribution/) inherit delivery/task context.
- Staff portal planning uses the create-task overlay at `ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`.
- Task-specific reusable materials are shared through [**Supporting Material**](/docs/en/supporting-material/) and [**Material Placement**](/docs/en/material-placement/).
- `ifitwala_ed/api/task.py` exposes `search_tasks`, `get_task_for_delivery`, and `create_task_delivery`.
- Some analytics and briefing readers still reference legacy `Task` plus `Task Student` style paths:
  - `ifitwala_ed/api/student_overview_dashboard.py`
  - `ifitwala_ed/api/morning_brief.py`

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/task.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task/test_task.py`)

1. Author the reusable task definition with required curriculum anchor (`default_course`) and optional deeper planned-curriculum anchors (`learning_unit`, `lesson`).
2. Configure default delivery and grading behavior, including optional `task_criteria` rows.
3. Create a `Task Delivery` as the execution instance for a specific `Student Group`.
4. Downstream outcomes, submissions, contributions, and rubric snapshots should inherit delivery/task context.

Current workspace note: delivery launch semantics are not yet unified. The direct API path delegates to `assessment/task_delivery_service.py`, while the overlay path uses `assessment/task_creation_service.py`. That split is the main task-stack drift currently documented in the task feature.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task Delivery**](/docs/en/task-delivery/)
- [**Learning Unit**](/docs/en/learning-unit/)
- [**Lesson**](/docs/en/lesson/)
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
- `task.py` enforces curriculum alignment, duplicate criterion guards, and coherent default grading configuration.
- `task.js` filters `learning_unit` and `lesson` choices by course context, clears stale curriculum links when course changes, and replaces generic Task resource uploads with the governed Task-resource action.
- `task.py` now treats `attachments` as a legacy compatibility surface only: new reusable task materials live in `Supporting Material` and are shared onto the task through `Material Placement`.
- The current task schema stops at `lesson`; it does not currently expose `lesson_activity` or `class_session`.
- `assessment/task_creation_service.py` supports the overlay path that creates both `Task` and `Task Delivery` in one transaction.
- The task overlay keeps teachers in-context after task creation so they can add task materials without leaving the workflow.

### Current Drift To Preserve In Review

- The definition layer is stable, but downstream launch remains split across two services.
- Legacy analytics readers still reference older structures; those reads must not be mistaken for the canonical gradebook contract.
- Any implementation change that alters task-launch behavior must update this page and the linked delivery/outcome docs in the same change.
