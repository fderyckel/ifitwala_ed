---
title: "Task Outcome Criterion: Official Criterion-Level Truth"
slug: task-outcome-criterion
category: Assessment
doc_order: 7.1
version: "1.0.0"
last_change_date: "2026-03-12"
summary: "Store per-criterion official results on Task Outcome so analytics and gradebook can trust criterion truth without recomputing client-side."
seo_title: "Task Outcome Criterion: Official Criterion-Level Truth"
seo_description: "Store per-criterion official results on Task Outcome so analytics and gradebook can trust criterion truth without recomputing client-side."
---

## Task Outcome Criterion: Official Criterion-Level Truth

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_outcome_criterion/task_outcome_criterion.json`, `ifitwala_ed/assessment/doctype/task_outcome_criterion/task_outcome_criterion.py`, `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/assessment/term_reporting.py`
Test refs: None

`Task Outcome Criterion` is the per-criterion official fact table stored under `Task Outcome.official_criteria`. Gradebook, analytics, and reporting should trust these rows rather than recomputing official criterion truth on the client.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`, `ifitwala_ed/assessment/task_outcome_service.py`
Test refs: None

- Create the parent `Task Outcome` first.
- Use a criteria-mode grading path that materializes official criterion truth.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/assessment/term_reporting.py`
Test refs: None

- Stored under `Task Outcome.official_criteria`.
- Written by `task_outcome_service.py` from winning contribution rows.
- Read by `api/gradebook.py` for gradebook criteria payloads.
- Read by `term_reporting.py` for criteria-based reporting.

## Lifecycle and Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/assessment/task_outcome_service.py`
Test refs: None

1. Start from `Task Contribution Criterion` rows on the winning contribution.
2. Replace the entire `official_criteria` child table during official outcome recomputation.
3. Preserve criterion-level official truth even when task-level totals are strategy-dependent.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task Outcome**](/docs/en/task-outcome/)
- [**Task Contribution Criterion**](/docs/en/task-contribution-criterion/)
- [**Task Rubric Criterion**](/docs/en/task-rubric-criterion/)
- [**Task Contribution**](/docs/en/task-contribution/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_outcome_criterion/task_outcome_criterion.json`, `ifitwala_ed/assessment/doctype/task_outcome_criterion/task_outcome_criterion.py`, `ifitwala_ed/assessment/task_outcome_service.py`
Test refs: None

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_outcome_criterion/task_outcome_criterion.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_outcome_criterion/task_outcome_criterion.py`
- **Field set**:
  - `assessment_criteria` (`Link` -> `Assessment Criteria`, required)
  - `level` (`Data`)
  - `level_points` (`Float`)
  - `feedback` (`Small Text`)
- **Controller**: thin (`pass`)

### Current Contract

- This child table is official truth, not draft grading input.
- Rows are replaced from winning `Task Contribution Criterion` input during recomputation.
- Reporting and gradebook must read these rows, not infer official criterion results from contributor rows directly.
