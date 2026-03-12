---
title: "Task Rubric Version: Freezing Criteria at Delivery Time"
slug: task-rubric-version
category: Assessment
doc_order: 6
version: "1.1.0"
last_change_date: "2026-03-12"
summary: "Snapshot rubric criteria per delivery so grading remains historically stable even if the master task rubric changes later."
seo_title: "Task Rubric Version: Freezing Criteria at Delivery Time"
seo_description: "Snapshot rubric criteria per delivery so grading remains historically stable even if the master task rubric changes later."
---

## Task Rubric Version: Freezing Criteria at Delivery Time

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_rubric_version/task_rubric_version.json`, `ifitwala_ed/assessment/doctype/task_rubric_version/task_rubric_version.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_outcome_service.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_rubric_version/test_task_rubric_version.py`)

`Task Rubric Version` is the historical snapshot of criteria used by a criteria-mode delivery. It prevents later edits to task criteria from silently rewriting grading meaning.

Current workspace note: the snapshot model is defined, but it depends on the delivery path actually reaching the delivery launch hook.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_rubric_version/test_task_rubric_version.py`)

- Prepare `Task` criteria templates first.
- Use `Criteria` grading mode on the target delivery.
- Launch the delivery through a path that actually executes rubric snapshot creation.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_rubric_version/test_task_rubric_version.py`)

- Created from [**Task Delivery**](/docs/en/task-delivery/) for criteria-mode deliveries.
- Stores [**Task Rubric Criterion**](/docs/en/task-rubric-criterion/) rows copied from [**Task Template Criterion**](/docs/en/task-template-criterion/).
- Read by `assessment/task_outcome_service.py` to apply criterion weighting.
- Read by `ifitwala_ed/api/gradebook.py` when building criteria payload for gradebook.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_creation_service.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_rubric_version/test_task_rubric_version.py`)

1. Define criteria on the parent `Task`.
2. Canonical contract: on delivery launch, create one rubric snapshot for the delivery.
3. Use the frozen rubric for contribution validation and outcome recomputation.
4. Preserve historical grading meaning even when the base task rubric changes later.

Current workspace drift: deliveries created through `task_creation_service.create_task_and_delivery()` do not currently execute the documented launch step, so criteria snapshots are not guaranteed on that path.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task**](/docs/en/task/)
- [**Task Template Criterion**](/docs/en/task-template-criterion/)
- [**Task Delivery**](/docs/en/task-delivery/)
- [**Task Rubric Criterion**](/docs/en/task-rubric-criterion/)
- [**Task Contribution**](/docs/en/task-contribution/)
- [**Task Outcome**](/docs/en/task-outcome/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_rubric_version/task_rubric_version.json`, `ifitwala_ed/assessment/doctype/task_rubric_version/task_rubric_version.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_rubric_version/test_task_rubric_version.py`)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_rubric_version/task_rubric_version.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_rubric_version/task_rubric_version.py`
- **Required fields (`reqd=1`)**:
  - `task` (`Link` -> `Task`)
  - `task_delivery` (`Link` -> `Task Delivery`)
  - `grading_mode` (`Select`)
- **Child table**:
  - `criteria` (`Task Rubric Criterion`)
- **Controller**: thin (`pass`); orchestration lives in the delivery layer.

### Current Contract

- `TaskDelivery._ensure_rubric_snapshot()` is the canonical snapshot builder.
- Criteria rows are copied from `Task.task_criteria`.
- `task_outcome_service.py` reads rubric criteria weighting when computing criteria-mode official totals.

### Current Drift To Preserve In Review

- Snapshot semantics are correct only when delivery launch semantics are correct.
- Fixing delivery launch without updating this doc would reintroduce drift immediately.
