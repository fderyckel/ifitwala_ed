---
title: "Task Contribution Criterion: Per-Criterion Grading Input Rows"
slug: task-contribution-criterion
category: Assessment
doc_order: 9.1
version: "1.0.1"
last_change_date: "2026-04-25"
summary: "Store the criterion-level grading inputs attached to a Task Contribution so official outcome truth can be recomputed server-side."
seo_title: "Task Contribution Criterion: Per-Criterion Grading Input Rows"
seo_description: "Store the criterion-level grading inputs attached to a Task Contribution so official outcome truth can be recomputed server-side."
---

## Task Contribution Criterion: Per-Criterion Grading Input Rows

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_contribution_criterion/task_contribution_criterion.json`, `ifitwala_ed/assessment/doctype/task_contribution_criterion/task_contribution_criterion.py`, `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: None

`Task Contribution Criterion` is the per-criterion grading input row stored on `Task Contribution.rubric_scores`. It captures what a contributor judged at criterion level before official truth is recomputed.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`, `ifitwala_ed/assessment/task_contribution_service.py`
Test refs: None

- Create the parent `Task Contribution` first.
- Use criteria-mode grading when populating these rows.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: None

- Stored under `Task Contribution.rubric_scores`.
- Gradebook writes and reads these rows through `api/gradebook.py`.
- `task_outcome_service.py` reads these rows when recomputing official criterion truth.

## Lifecycle and Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/assessment/task_outcome_service.py`
Test refs: None

1. Capture criterion-level grading inputs on a contribution row.
2. Keep these rows attached to contributor history rather than writing directly into `Task Outcome`.
3. Let official recomputation choose the winning contribution and copy the winning criterion rows into `Task Outcome Criterion`.

## Related Docs

<RelatedDocs
  slugs="task-contribution,task-outcome-criterion,task-outcome,assessment-criteria"
  title="Related Documentation"
/>

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_contribution_criterion/task_contribution_criterion.json`, `ifitwala_ed/assessment/doctype/task_contribution_criterion/task_contribution_criterion.py`
Test refs: None

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_contribution_criterion/task_contribution_criterion.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_contribution_criterion/task_contribution_criterion.py`
- **Field set**:
  - `assessment_criteria` (`Link` -> `Assessment Criteria`, required)
  - `level` (`Data`, required)
  - `level_points` (`Float`)
  - `feedback` (`Small Text`)
- **Controller**: thin (`pass`)

### Current Contract

- These rows are contributor input, not official truth.
- They exist to preserve grading history and support server-owned official recomputation.
- Client code must not skip the parent contribution workflow and write official fields directly.
