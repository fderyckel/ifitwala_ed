---
title: "Task Contribution: Teacher and Moderator Judgment Inputs"
slug: task-contribution
category: Assessment
doc_order: 9
version: "1.2.1"
last_change_date: "2026-04-25"
summary: "Store non-destructive grading contributions per submission version, including assessed boolean judgments and comment-only feedback, then derive official outcomes through policy-aware services."
seo_title: "Task Contribution: Teacher and Moderator Judgment Inputs"
seo_description: "Store non-destructive grading contributions per submission version, then derive official outcomes through policy-aware services."
---

## Task Contribution: Teacher and Moderator Judgment Inputs

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`, `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.py`, `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_contribution/test_task_contribution.py`)

`Task Contribution` stores teacher, reviewer, and moderator grading inputs without overwriting history. Official student truth is derived from these rows into `Task Outcome`.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`, `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.py`, `ifitwala_ed/assessment/task_contribution_service.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_contribution/test_task_contribution.py`)

- Create the target `Task Outcome` first.
- Ensure contributor identity and grading permissions are valid for the delivery context.
- If evidence-based grading is required, resolve a valid `Task Submission` first.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/assessment/task_outcome_service.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_contribution/test_task_contribution.py`)

- Anchored to [**Task Outcome**](/docs/en/task-outcome/) and usually to [**Task Submission**](/docs/en/task-submission/).
- Gradebook mutations run through:
  - `save_draft`
  - `submit_contribution`
  - `moderator_action`
  - `save_contribution_draft`
- Criteria-mode grading stores row-level marks in [**Task Contribution Criterion**](/docs/en/task-contribution-criterion/).
- `task_outcome_service.py` reads contribution rows to recompute official outcome truth.

## Lifecycle and Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.py`, `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/assessment/task_outcome_service.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_contribution/test_task_contribution.py`)

1. Start from an existing `Task Outcome` and, where required, a linked `Task Submission`.
2. Create draft, submitted, moderator, or override contribution rows as additive records.
3. Recompute official outcome fields from contribution services without deleting grading history.
4. Mark older contributions stale when student evidence changes.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task Outcome**](/docs/en/task-outcome/)
- [**Task Submission**](/docs/en/task-submission/)
- [**Task Contribution Criterion**](/docs/en/task-contribution-criterion/)
- [**Task Delivery**](/docs/en/task-delivery/)
- [**Task Rubric Version**](/docs/en/task-rubric-version/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`, `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.py`, `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/assessment/task_outcome_service.py`
Test refs: None (scaffold only: `ifitwala_ed/assessment/doctype/task_contribution/test_task_contribution.py`)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.py`
- **Required fields (`reqd=1`)**:
  - `task_outcome` (`Link` -> `Task Outcome`)
  - `contributor` (`Link` -> `User`)
  - `contribution_type` (`Select`)
  - `submitted_on` (`Datetime`)
- **Child table**:
  - `rubric_scores` (`Task Contribution Criterion`)
- **Lifecycle hooks in controller**:
  - `before_validate`
  - `validate`
  - `after_insert`
  - `on_doctype_update`

### Current Contract

- `before_validate()` stamps context from outcome and ensures any linked submission belongs to the outcome.
- `validate()` enforces grading-mode coherence and grade-scale consistency.
- `after_insert()` triggers official outcome recomputation for non-draft rows.
- `task_contribution_service.py` owns the named workflow actions used by gradebook.
- Assessed `Completion` and `Binary` grading use `judgment_code` on the contribution row; the outcome service derives `Task Outcome.is_complete` from the selected contribution and does not write scalar official score fields.
- Comment-only contributions write feedback/status only; they do not create, require, or clear `Task Outcome.official_score`.

### Verified Gap

- The controller/service contract exists, but meaningful regression coverage is still missing; the current test file is scaffold-only.
- Any implementation change to contribution semantics should land with real tests, not with more documentation alone.
