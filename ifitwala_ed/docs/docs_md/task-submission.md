---
title: "Task Submission: Versioned Student Evidence with Governance"
slug: task-submission
category: Assessment
doc_order: 8
version: "1.1.0"
last_change_date: "2026-03-12"
summary: "Capture append-only student evidence (files, text, links), enforce versioning, and keep outcomes and portfolio workflows synchronized."
seo_title: "Task Submission: Versioned Student Evidence with Governance"
seo_description: "Capture append-only student evidence (files, text, links), enforce versioning, and keep outcomes and portfolio workflows synchronized."
---

## Task Submission: Versioned Student Evidence with Governance

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_submission/task_submission.json`, `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`, `ifitwala_ed/assessment/task_submission_service.py`, `ifitwala_ed/api/task_submission.py`
Test refs: `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`, `ifitwala_ed/api/test_task_submission.py`

`Task Submission` is the governed evidence layer for task work. Students can submit and resubmit over time, and every version is preserved for grading, moderation, and audit.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_submission/task_submission.json`, `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`, `ifitwala_ed/assessment/task_submission_service.py`
Test refs: `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`, `ifitwala_ed/api/test_task_submission.py`

- Create the target `Task Outcome` first.
- Ensure submitter identity is valid for the submission context.
- If attachments are used, route them through the governed upload flow.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/api/task_submission.py`, `ifitwala_ed/assessment/task_submission_service.py`, `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/api/student_portfolio.py`
Test refs: `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`, `ifitwala_ed/api/test_task_submission.py`

- Anchored to [**Task Outcome**](/docs/en/task-outcome/).
- Referenced by [**Task Contribution**](/docs/en/task-contribution/) for version-accurate grading.
- Student portal submission endpoints live in `ifitwala_ed/api/task_submission.py`.
- Gradebook draft, submit, and moderation flows auto-resolve the latest submission or create evidence stubs when allowed.
- Portfolio and reflection surfaces can reuse submission evidence through `ifitwala_ed/api/student_portfolio.py`.

## Lifecycle and Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`, `ifitwala_ed/assessment/task_submission_service.py`
Test refs: `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`, `ifitwala_ed/api/test_task_submission.py`

1. Create evidence against a valid `Task Outcome`.
2. Each resubmission creates a new `version` rather than mutating prior evidence.
3. Submission insertion updates the parent outcome state (`has_submission`, `has_new_submission`, submission status).
4. Contribution flows resolve against a real or stub submission version for grading integrity.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task Outcome**](/docs/en/task-outcome/)
- [**Task Contribution**](/docs/en/task-contribution/)
- [**Task Delivery**](/docs/en/task-delivery/)
- [**Task**](/docs/en/task/)

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_submission/task_submission.json`, `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`, `ifitwala_ed/assessment/task_submission_service.py`, `ifitwala_ed/api/task_submission.py`
Test refs: `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`, `ifitwala_ed/api/test_task_submission.py`

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_submission/task_submission.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`
- **Required fields (`reqd=1`)**:
  - `task_outcome` (`Link` -> `Task Outcome`)
  - `version` (`Int`)
  - `submitted_by` (`Link` -> `User`)
  - `submitted_on` (`Datetime`)
- **Child table**:
  - `attachments` (`Attached Document`)
- **Lifecycle hooks in controller**:
  - `before_validate`
  - `validate`
  - `after_insert`
  - `on_doctype_update`

### Current Contract

- `before_validate()` stamps denormalized context and default submission metadata.
- `validate()` enforces append-only behavior, evidence presence, and lock-date / late-submission policy.
- `after_insert()` applies outcome submission effects.
- `task_submission_service.py` owns student submission orchestration, file handling, and evidence stub creation.
- File governance still applies: uploads must follow governed routing and classification rules.

### Verified Coverage

- `test_task_submission.py` covers attachment-change and unique-index helper behavior.
- `api/test_task_submission.py` covers secure rewriting of private attachment links to the guarded download endpoint.
