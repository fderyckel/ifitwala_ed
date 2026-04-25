---
title: "Task Rubric Criterion: Frozen Criteria Rows per Delivery"
slug: task-rubric-criterion
category: Assessment
doc_order: 6.1
version: "1.0.1"
last_change_date: "2026-04-25"
summary: "Store the frozen criteria rows copied onto Task Rubric Version so criteria-mode grading remains historically stable."
seo_title: "Task Rubric Criterion: Frozen Criteria Rows per Delivery"
seo_description: "Store the frozen criteria rows copied onto Task Rubric Version so criteria-mode grading remains historically stable."
---

## Task Rubric Criterion: Frozen Criteria Rows per Delivery

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_rubric_criterion/task_rubric_criterion.json`, `ifitwala_ed/assessment/doctype/task_rubric_criterion/task_rubric_criterion.py`, `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: None

`Task Rubric Criterion` is the child row stored on `Task Rubric Version.criteria`. It freezes the criteria structure that applied to a specific delivery.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/doctype/task_rubric_version/task_rubric_version.json`
Test refs: None

- Use criteria-mode delivery.
- Ensure the parent delivery reaches the rubric snapshot path.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: None

- Stored under `Task Rubric Version.criteria`.
- Read by `task_outcome_service.py` when applying weighted criteria totals.
- Read by `api/gradebook.py` to build criteria payload for gradebook.

## Lifecycle and Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
Test refs: None

1. Copy rows from `Task Template Criterion` during rubric snapshot creation.
2. Persist the frozen criteria structure on the delivery-specific rubric version.
3. Use these rows for later outcome computation and gradebook rendering.

## Related Docs

<RelatedDocs
  slugs="task-rubric-version,task-template-criterion,task-outcome"
  title="Related Documentation"
/>

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_rubric_criterion/task_rubric_criterion.json`, `ifitwala_ed/assessment/doctype/task_rubric_criterion/task_rubric_criterion.py`
Test refs: None

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_rubric_criterion/task_rubric_criterion.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_rubric_criterion/task_rubric_criterion.py`
- **Field set**:
  - `assessment_criteria` (`Link` -> `Assessment Criteria`)
  - `criteria_name` (`Data`)
  - `criteria_weighting` (`Float`)
  - `criteria_max_points` (`Float`)
- **Controller**: thin (`pass`)

### Current Contract

- This child table is a frozen snapshot layer.
- It is not the official grading fact table; outcome truth still belongs to `Task Outcome Criterion`.
