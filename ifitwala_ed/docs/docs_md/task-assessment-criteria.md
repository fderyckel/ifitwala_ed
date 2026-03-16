---
title: "Task Assessment Criteria: Dormant Child Table in the Task Domain"
slug: task-assessment-criteria
category: Assessment
doc_order: 4.2
version: "1.0.0"
last_change_date: "2026-03-12"
summary: "Document the current non-canonical status of Task Assessment Criteria so agents do not assume it participates in the active task workflow."
seo_title: "Task Assessment Criteria: Dormant Child Table in the Task Domain"
seo_description: "Document the current non-canonical status of Task Assessment Criteria so agents do not assume it participates in the active task workflow."
---

## Task Assessment Criteria: Dormant Child Table in the Task Domain

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.json`, `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.py`
Test refs: None

`Task Assessment Criteria` exists in schema, but it is not wired into the current canonical task workflow in this workspace. The active task stack uses `Task Template Criterion`, `Task Rubric Criterion`, `Task Contribution Criterion`, and `Task Outcome Criterion` instead.

## Before You Start (Prerequisites)

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.json`
Test refs: None

- Prefer [**Task Template Criterion**](/docs/en/task-template-criterion/) for current task-definition work.
- Do not introduce new runtime dependencies on this child table without an explicit architecture decision.

## Where It Is Used Across the ERP

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.json`, `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.py`
Test refs: None

- No live server, SPA, report, or scheduler references were found in the current workspace.
- The doctype remains present as schema only.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.json`
Test refs: None

1. The row structure exists in metadata.
2. It is not currently materialized by `Task`, `Task Delivery`, `Task Rubric Version`, `Task Contribution`, or `Task Outcome`.
3. Treat it as dormant until an explicit contract replaces or reconnects it.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task Template Criterion**](/docs/en/task-template-criterion/)
- [**Task**](/docs/en/task/)
- [**Assessment Criteria**](/docs/en/assessment-criteria/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.json`, `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.py`
Test refs: None

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_assessment_criteria/task_assessment_criteria.py`
- **Field set**:
  - `assessment_criteria` (`Link` -> `Assessment Criteria`, required)
  - `criteria_name` (`Data`)
  - `criteria_weighting` (`Percent`)
  - `criteria_max_points` (`Float`)
- **Controller**: thin (`pass`)

### Current Contract

- This doctype is not part of the active canonical task path.
- Its existence must not be treated as proof of runtime support.
- If the product decides to reuse or remove it, docs and implementation must change together.
