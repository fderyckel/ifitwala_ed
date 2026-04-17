---
title: "Task Submission: Versioned Student Evidence with Governance"
slug: task-submission
category: Assessment
doc_order: 8
version: "1.2.0"
last_change_date: "2026-04-17"
summary: "Capture append-only student evidence (files, text, links), enforce versioning, and keep outcomes and portfolio workflows synchronized."
seo_title: "Task Submission: Versioned Student Evidence with Governance"
seo_description: "Capture append-only student evidence (files, text, links), enforce versioning, and keep outcomes and portfolio workflows synchronized."
---

## Task Submission: Versioned Student Evidence with Governance

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_submission/task_submission.json`, `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`, `ifitwala_ed/assessment/task_submission_service.py`, `ifitwala_ed/api/task_submission.py`
Test refs: `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`, `ifitwala_ed/api/test_task_submission.py`

`Task Submission` is the governed evidence layer for task work. Students can submit and resubmit over time, and every version is preserved for grading, moderation, and audit.

## Permission Matrix

Status: Implemented
Code refs: `ifitwala_ed/api/task_submission.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/api/file_access.py`
Test refs: `ifitwala_ed/api/test_task_submission.py`, `ifitwala_ed/api/test_gradebook.py`

| Role / Surface | What they can do |
| --- | --- |
| Student portal | Create or resubmit their own evidence through the governed upload flow and read the latest permitted submission payload through the student-facing API. |
| Staff gradebook | Read version summaries and one selected submission version inside the gradebook drawer, with server-owned preview/open routes resolved per attachment. |
| Guardian portal | No direct `Task Submission` authoring surface. Visibility stays mediated through released outcome and other guardian-authorized workflows. |
| Administrators / academic staff | Access remains server-scoped and follows the same outcome, student, and school visibility checks as the owning assessment surface. |

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_submission/task_submission.json`, `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`, `ifitwala_ed/assessment/task_submission_service.py`
Test refs: `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`, `ifitwala_ed/api/test_task_submission.py`

- Create the target `Task Outcome` first.
- Ensure submitter identity is valid for the submission context.
- If attachments are used, route them through the governed upload flow backed by `ifitwala_ed.utilities.governed_uploads.upload_task_submission_attachment` -> `ifitwala_drive.api.submissions.upload_task_submission_artifact`.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/api/task_submission.py`, `ifitwala_ed/assessment/task_submission_service.py`, `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/api/student_portfolio.py`
Test refs: `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`, `ifitwala_ed/api/test_task_submission.py`

- Anchored to [**Task Outcome**](/docs/en/task-outcome/).
- Referenced by [**Task Contribution**](/docs/en/task-contribution/) for version-accurate grading.
- Student portal submission endpoints live in `ifitwala_ed/api/task_submission.py`.
- Gradebook draft, submit, and moderation flows auto-resolve the latest submission or create evidence stubs when allowed.
- Portfolio and reflection surfaces can reuse submission evidence through `ifitwala_ed/api/student_portfolio.py`.
- Desk attachment uploads delegate the binary upload/finalize path to `ifitwala_drive`, then append the finalized file URL into `Task Submission.attachments`.

## Lifecycle and Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`, `ifitwala_ed/assessment/task_submission_service.py`
Test refs: `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`, `ifitwala_ed/api/test_task_submission.py`

1. Create evidence against a valid `Task Outcome`.
2. Each resubmission creates a new `version` rather than mutating prior evidence.
3. Submission insertion updates the parent outcome state (`has_submission`, `has_new_submission`, submission status).
4. Contribution flows resolve against a real or stub submission version for grading integrity.

## Evidence Review And Preview

Status: Implemented current-state baseline
Code refs: `ifitwala_ed/api/task_submission.py`, `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/api/file_access.py`
Test refs: `ifitwala_ed/api/test_task_submission.py`, `ifitwala_ed/api/test_gradebook.py`

- The student-side latest-submission read now returns governed attachment rows with stable `preview_url` and `open_url` values instead of raw private file paths.
- The staff gradebook drawer now supports strict version selection: it returns a version list summary plus one selected submission payload for the requested version, defaulting to the latest version when no selection is provided.
- Attachment preview is still governed by the owning submission and student scope. The SPA must not guess file paths or bypass the server-owned route contract.
- Preview remains additive to open/download. When no ready derivative exists, the preview route may degrade to the canonical file while still preserving permission checks.

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
- File governance still applies: Desk attachment uploads currently run through `ifitwala_ed.utilities.governed_uploads.upload_task_submission_attachment`, which calls `ifitwala_drive.api.submissions.upload_task_submission_artifact` before the finalized file is appended to the submission row.

### Verified Coverage

- `test_task_submission.py` covers attachment-change and unique-index helper behavior.
- `api/test_task_submission.py` covers secure rewriting of private attachment links to the guarded download endpoint.
