---
title: "Task Template Criterion: Criteria Rows on the Task Definition"
slug: task-template-criterion
category: Assessment
doc_order: 4.1
version: "1.0.0"
last_change_date: "2026-03-12"
summary: "Store reusable assessment criteria rows on Task so criteria-mode deliveries can snapshot stable rubric context later."
seo_title: "Task Template Criterion: Criteria Rows on the Task Definition"
seo_description: "Store reusable assessment criteria rows on Task so criteria-mode deliveries can snapshot stable rubric context later."
---

## Task Template Criterion: Criteria Rows on the Task Definition

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_template_criterion/task_template_criterion.json`, `ifitwala_ed/assessment/doctype/task_template_criterion/task_template_criterion.py`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
Test refs: None

`Task Template Criterion` is the child table used on `Task.task_criteria`. It defines which assessment criteria belong to the reusable task and what weighting or max-points metadata travels downstream.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: None

- Create the parent `Task` first.
- Create reusable `Assessment Criteria` first.
- Use this child table only for definition-layer task design, not for official grading facts.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
Test refs: None

- Lives under `Task.task_criteria`.
- `task.py` enforces duplicate-criterion guards across these child rows.
- `task_delivery.py` reads these rows when validating criteria-mode deliveries and when building rubric snapshots.
- Criteria-mode `Task Rubric Version` rows inherit this structure.

## Lifecycle and Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
Test refs: None

1. Add criterion rows while authoring the parent `Task`.
2. Keep one row per `Assessment Criteria` entry; duplicates are blocked at the parent controller.
3. When a criteria-mode delivery launches, copy these rows into a `Task Rubric Version`.
4. Do not use these rows as grading truth after delivery launch; downstream rubric, contribution, and outcome rows own that.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task**](/docs/en/task/)
- [**Assessment Criteria**](/docs/en/assessment-criteria/)
- [**Task Rubric Version**](/docs/en/task-rubric-version/)
- [**Task Rubric Criterion**](/docs/en/task-rubric-criterion/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_template_criterion/task_template_criterion.json`, `ifitwala_ed/assessment/doctype/task_template_criterion/task_template_criterion.py`, `ifitwala_ed/assessment/doctype/task/task.py`
Test refs: None

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_template_criterion/task_template_criterion.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_template_criterion/task_template_criterion.py`
- **Field set**:
  - `assessment_criteria` (`Link` -> `Assessment Criteria`, required)
  - `criteria_weighting` (`Float`)
  - `criteria_max_points` (`Float`)
- **Controller**: thin (`pass`); parent `Task` owns validation and workflow.

### Current Contract

- This child table is definition-layer only.
- Business logic stays in the parent `Task` and downstream delivery services.
- Weighting and max-points values are snapshot inputs, not official results.
