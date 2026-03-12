---
title: "Task Delivery: Turning a Task into a Real Teaching Event"
slug: task-delivery
category: Assessment
doc_order: 5
version: "1.1.0"
last_change_date: "2026-03-12"
summary: "Assign a task to a specific student group with dates, grading mode, and evidence rules, then generate student outcomes at scale."
seo_title: "Task Delivery: Turning a Task into a Real Teaching Event"
seo_description: "Assign a task to a specific student group with dates, grading mode, and evidence rules, then generate student outcomes at scale."
---

## Task Delivery: Turning a Task into a Real Teaching Event

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`)

`Task Delivery` is where a reusable task becomes real for a specific student group, within a specific time window and grading/evidence policy.

Current workspace note: the canonical lifecycle is submit-driven, but the live creation paths are split. `task_delivery.py` defines `on_submit()` behavior, `task_delivery_service.py` tries to use `doc.submit()`, and `task_creation_service.py` currently inserts a draft delivery without submitting it.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`)

- Create the parent `Task` first.
- Create the `Student Group` first, with roster and context aligned to the teaching situation.
- Prepare grading setup first (`Grade Scale`, and task criteria readiness if using criteria grading mode).

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`
Test refs: None

- Parent context for [**Task Outcome**](/docs/en/task-outcome/) rows.
- Referenced by [**Task Submission**](/docs/en/task-submission/) and [**Task Contribution**](/docs/en/task-contribution/).
- Criteria-mode deliveries feed [**Task Rubric Version**](/docs/en/task-rubric-version/).
- `/staff/gradebook` reads delivery rows through `ifitwala_ed/api/gradebook.py`.
- Guardian home chips read due-task and upcoming-assessment context from `ifitwala_ed/api/guardian_home.py`.
- The staff overlay `ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue` creates deliveries through `assessment/task_creation_service.py`.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`)

1. Create the delivery from a reusable `Task` plus target `Student Group`.
2. Canonical contract: submit the delivery to generate student-level `Task Outcome` rows and, for criteria mode, a `Task Rubric Version`.
3. Collect submissions and contributions under this delivery context during teaching and grading.
4. Protect historical integrity by locking grading configuration once outcomes or evidence exist.

Current workspace drift:

- `task_delivery.py` puts outcome generation and rubric snapshotting in `on_submit()`.
- `task_delivery_service.py::create_delivery()` calls `doc.submit()` even though the current DocType schema is not marked `is_submittable`.
- `task_creation_service.py::create_task_and_delivery()` inserts the delivery and returns immediately, which leaves deliveries without outcomes on that path.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task**](/docs/en/task/)
- [**Task Outcome**](/docs/en/task-outcome/)
- [**Task Submission**](/docs/en/task-submission/)
- [**Task Contribution**](/docs/en/task-contribution/)
- [**Task Rubric Version**](/docs/en/task-rubric-version/)
- [**Task Rubric Criterion**](/docs/en/task-rubric-criterion/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
- **Required fields (`reqd=1`)**:
  - `task` (`Link` -> `Task`)
  - `student_group` (`Link` -> `Student Group`)
  - `delivery_mode` (`Select`)
- **Lifecycle hooks in controller**:
  - `before_validate`
  - `validate`
  - `on_submit`
  - `on_cancel`
- **Key links**:
  - `task`
  - `student_group`
  - `grade_scale`
  - `rubric_version`
  - `course`
  - `academic_year`
  - `school`
  - `lesson_instance`

### Current Contract

- `before_validate()` stamps denormalized context from `Student Group`, checks task/course alignment, and optionally resolves lesson instance context.
- `validate()` enforces delivery-mode coherence, date rules, criteria requirements, and the current hard block on `group_submission`.
- `on_submit()` is the canonical place for:
  - criteria snapshot creation
  - bulk `Task Outcome` creation for eligible students
- `on_cancel()` removes linked outcomes only when no evidence exists.

### Current Drift To Preserve In Review

- The DocType schema currently lacks `is_submittable: 1`, so the submit-driven contract is not fully represented in metadata.
- Not every creation path reaches `on_submit()`, which is the direct cause of draft deliveries with no generated outcomes.
- Any code fix in this area must update:
  - this page
  - [**Task Outcome**](/docs/en/task-outcome/)
  - [**Task Rubric Version**](/docs/en/task-rubric-version/)
