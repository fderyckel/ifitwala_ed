---
title: "Task Contribution: Teacher and Moderator Judgment Inputs"
slug: task-contribution
category: Assessment
doc_order: 9
version: "1.0.0"
last_change_date: "2026-02-25"
summary: "Store non-destructive grading contributions per submission version, then derive official outcomes through policy-aware services."
seo_title: "Task Contribution: Teacher and Moderator Judgment Inputs"
seo_description: "Store non-destructive grading contributions per submission version, then derive official outcomes through policy-aware services."
---

## Task Contribution: Teacher and Moderator Judgment Inputs

## Before You Start (Prerequisites)

- Create the target `Task Outcome` first.
- Ensure contributor users and grading permissions are set for the delivery context.
- If evidence-based grading is used, ensure at least one `Task Submission` version exists.

`Task Contribution` captures who graded what, when, and against which submission version. It preserves collaboration history (self, review, moderation) without overwriting prior judgments.

<Callout type="info" title="Separation of concerns">
Contributions are professional inputs. Official student truth is still written to [Task Outcome](/docs/en/task-outcome/) through service logic.
</Callout>

## Where It Is Used Across the ERP

- Anchored to [**Task Outcome**](/docs/en/task-outcome/) and usually to [**Task Submission**](/docs/en/task-submission/).
- Gradebook endpoints (`ifitwala_ed/api/gradebook.py`):
  - `save_draft`
  - `submit_contribution`
  - `moderator_action`
  - `save_contribution_draft`
- Feeds official outcome recomputation via `assessment/task_outcome_service.py`.
- Staleness updates triggered when student evidence changes (`mark_contributions_stale`).
- Criteria-mode grading stores row-level marks in child table `Task Contribution Criterion`.

## Lifecycle and Linked Documents

1. Start from an existing `Task Outcome` and, where required, linked `Task Submission` evidence.
2. Teachers/reviewers create contribution entries (draft, submit, moderate, or override flows).
3. Contribution services recompute official outcome data without destroying historical contribution rows.
4. Use moderation and staleness flags to keep official outcomes aligned with latest evidence.

<Callout type="warning" title="Do not bypass outcome services">
Directly editing official outcome fields without contribution/service flow can break moderation traceability.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.py`
- **Required fields (`reqd=1`)**:
  - `task_outcome` (`Link` -> `Task Outcome`)
  - `contributor` (`Link` -> `User`)
  - `contribution_type` (`Select`)
  - `submitted_on` (`Datetime`)
- **Lifecycle hooks in controller**: `before_validate`, `validate`, `after_insert`, `on_doctype_update`
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Task Contribution` (`ifitwala_ed/assessment/doctype/task_contribution/`)
- **Autoname**: `TCO-{YYYY}-{#####}`
- **Child table**: `rubric_scores` (`Task Contribution Criterion`)
- **Key links**:
  - `task_outcome`, `task_submission`, `contributor`, `grade_scale`, `task_delivery`, `task`, `student`, `student_group`, `course`, `academic_year`, `school`
- **Lifecycle behavior** (`task_contribution.py`):
  - `before_validate`:
    - stamps context from outcome
    - enforces submission belongs to selected outcome
    - enforces latest submission version usage
  - `validate`:
    - submission requirement based on delivery rules and draft/submit status
    - grade symbol/value consistency against grade scale
    - payload coherence by grading mode (points/criteria/ungraded)
  - `after_insert`:
    - non-draft contributions trigger official outcome recomputation
- **Indexing**:
  - (`task_outcome`, `is_stale`, `modified`)
  - (`task_submission`)
  - (`contributor`, `modified`)
- **Desk client script**: stub-only (`task_contribution.js`)
- **Architecture guarantees (embedded from gradebook/task notes)**:
  - contributions are non-destructive, additive records (no overwrite model)
  - contribution rows represent professional judgment inputs; official fields are derived server-side into Task Outcome
  - moderation and peer-review decisions stay in contribution history for audit trail continuity

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | Yes | Yes | Yes |

## Related Docs

- [**Task Outcome**](/docs/en/task-outcome/)
- [**Task Submission**](/docs/en/task-submission/)
- [**Task Delivery**](/docs/en/task-delivery/)
- [**Task Rubric Version**](/docs/en/task-rubric-version/)
