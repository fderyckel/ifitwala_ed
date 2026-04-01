---
title: "Task Delivery: Assigning Work to a Real Class"
slug: task-delivery
category: Assessment
doc_order: 5
version: "1.5.0"
last_change_date: "2026-04-01"
summary: "Assign a reusable task to a specific class through its class teaching plan, with dates, grading mode, optional class-session context, and scalable outcome generation."
seo_title: "Task Delivery: Assigning Work to a Real Class"
seo_description: "Assign a reusable task to a class through its teaching plan with dates, grading mode, evidence rules, and optional class-session context."
---

## Task Delivery: Assigning Work to a Real Class

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/assessment/test_task_creation_service.py`, `ifitwala_ed/assessment/test_task_delivery_service.py`, `ifitwala_ed/api/test_gradebook.py`

`Task Delivery` is where a reusable task becomes real for a specific student group, within a specific time window and grading/evidence policy.

Current workspace note: delivery launch is now submit-driven across both creation services, the live schema requires `class_teaching_plan`, and the taught-context link is optional `class_session` instead of `lesson_instance`.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`)

- Create the parent `Task` first.
- Create the `Student Group` first, with roster and context aligned to the teaching situation.
- Ensure the class has an active `Class Teaching Plan`.
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
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/assessment/test_task_creation_service.py`, `ifitwala_ed/assessment/test_task_delivery_service.py`, `ifitwala_ed/api/test_gradebook.py`

1. Create the delivery from a reusable `Task`, target `Student Group`, and target `Class Teaching Plan`.
2. Canonical contract: submit the delivery to generate student-level `Task Outcome` rows and, for criteria mode, a `Task Rubric Version`.
3. Collect submissions and contributions under this delivery context during teaching and grading.
4. Protect historical integrity by locking grading configuration once outcomes or evidence exist.

Current workspace constraints:

- `task_delivery.py` keeps outcome generation and rubric snapshotting behind delivery launch semantics.
- `task_creation_service.py::create_task_and_delivery()` and `task_delivery_service.py::create_delivery()` both submit the delivery and then enforce roster materialization idempotently.
- `api/gradebook.py::repair_task_roster()` exists to backfill outcomes for deliveries created before the launch contract was restored, and to catch up later roster additions safely.
- The current schema exposes required `class_teaching_plan` plus optional `class_session`. It does not expose `lesson` or `lesson_activity` fields on `Task Delivery`.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task**](/docs/en/task/)
- [**Class Session**](/docs/en/class-session/)
- [**Task Outcome**](/docs/en/task-outcome/)
- [**Task Submission**](/docs/en/task-submission/)
- [**Task Contribution**](/docs/en/task-contribution/)
- [**Task Rubric Version**](/docs/en/task-rubric-version/)
- [**Task Rubric Criterion**](/docs/en/task-rubric-criterion/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/task_delivery_service.py`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/assessment/test_task_creation_service.py`, `ifitwala_ed/assessment/test_task_delivery_service.py`, `ifitwala_ed/api/test_gradebook.py`

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
  - `class_teaching_plan`
  - `grade_scale`
  - `rubric_version`
  - `course`
  - `academic_year`
  - `school`
  - `class_session`

### Current Contract

- `before_validate()` stamps denormalized context from `Student Group`, checks task/course alignment, validates the required `class_teaching_plan` anchor, and then validates any optional `class_session` anchor.
- `validate()` enforces delivery-mode coherence, date rules, criteria requirements, and the current hard block on `group_submission`.
- `on_submit()` is the canonical place for:
  - criteria snapshot creation
  - bulk `Task Outcome` creation for eligible students
- `materialize_roster()` is the idempotent parent-controller helper used by submit flows and the gradebook repair endpoint.
- `on_cancel()` removes linked outcomes only when no evidence exists.
- Delivery services no longer auto-create taught-session records. If a delivery needs live class-session context, it must link to an existing `Class Session`.

### Current Constraints To Preserve In Review

- `group_submission` remains intentionally blocked until the subgroup model exists.
- Legacy deliveries created before the fixed launch path may still need `api/gradebook.py::repair_task_roster()` to generate their outcomes.
- Current delivery payloads must resolve a `class_teaching_plan` first, then may link to taught curriculum through `class_session` when that context is explicitly supplied.
- Any future change in delivery launch semantics must update:
  - this page
  - [**Class Session**](/docs/en/class-session/)
  - [**Task Outcome**](/docs/en/task-outcome/)
  - [**Task Rubric Version**](/docs/en/task-rubric-version/)
