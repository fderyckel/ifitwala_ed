---
title: "Task Submission: Versioned Student Evidence with Governance"
slug: task-submission
category: Assessment
doc_order: 8
summary: "Capture append-only student evidence (files, text, links), enforce versioning, and keep outcomes and portfolio workflows synchronized."
---

# Task Submission: Versioned Student Evidence with Governance

`Task Submission` is the evidence layer. Students can submit and resubmit work over time, and every version is preserved so grading and moderation stay auditable.

<Callout type="warning" title="Append-only model">
Existing submission evidence cannot be overwritten. New evidence must be added as a new submission version.
</Callout>

## Where It Is Used Across the ERP

- Linked directly to [**Task Outcome**](/docs/en/task-outcome/) (`task_outcome`).
- Referenced by [**Task Contribution**](/docs/en/task-contribution/) for version-accurate grading.
- Student portal upload APIs:
  - `ifitwala_ed.api.task_submission.create_or_resubmit`
  - `ifitwala_ed.api.task_submission.get_latest_submission`
- Gradebook draft/submit/moderation flows auto-resolve or auto-create evidence stubs.
- Portfolio and reflection ecosystem:
  - `ifitwala_ed.api.student_portfolio.*` can ingest Task Submissions as evidence items
  - `Student Portfolio Item`, `Student Reflection Entry`, and `Evidence Tag` reference Task Submission
- Desk governed attachment flow:
  - custom upload action in `task_submission.js`
  - server endpoint `ifitwala_ed.utilities.governed_uploads.upload_task_submission_attachment`

## Technical Notes (IT)

- **DocType**: `Task Submission` (`ifitwala_ed/assessment/doctype/task_submission/`)
- **Autoname**: `TSU-{YYYY}-{#####}`
- **Child table**: `attachments` (`Attached Document`)
- **Key links**:
  - `task_outcome`, `task_delivery`, `task`, `submitted_by`, `cloned_from`, `student`, `student_group`, `school`, `course`, `academic_year`
- **Lifecycle behavior** (`task_submission.py`):
  - `before_validate`:
    - requires outcome
    - stamps denormalized context
    - sets metadata (`submitted_by`, `submitted_on`, version)
  - `validate`:
    - lock-date and late-submission checks
    - evidence presence check (file/text/link)
    - append-only guard on edits
  - `after_insert`:
    - applies outcome submission effects (`has_submission`, `has_new_submission`, statuses)
- **Service layer** (`assessment/task_submission_service.py`):
  - student submissions + file attachment handling
  - evidence stub creation for offline grading paths
  - group-clone infrastructure hooks
- **Indexing**:
  - unique (`task_outcome`, `version`)
  - secondary index (`task_delivery`, `student`)
- **Desk client script** (`task_submission.js`):
  - governed upload button
  - direct inline file edit disabled on child attachment rows
- **Architecture guarantees (embedded from assessment + portal/file governance notes)**:
  - submission evidence is append-only and versioned; no in-place overwrite of prior evidence
  - student resubmission marks prior teacher contributions as stale and raises `has_new_submission`
  - offline evidence is supported with governed evidence stubs when submission is required
  - uploads must follow governed file routing/classification patterns, including private handling for sensitive student evidence

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | Yes | Yes | Yes |

## Related Docs

- [**Task Outcome**](/docs/en/task-outcome/)
- [**Task Contribution**](/docs/en/task-contribution/)
- [**Task Delivery**](/docs/en/task-delivery/)
- [**Task**](/docs/en/task/)
