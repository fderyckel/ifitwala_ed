---
title: "Task Contribution: Teacher and Moderator Judgment Inputs"
slug: task-contribution
category: Assessment
doc_order: 9
summary: "Store non-destructive grading contributions per submission version, then derive official outcomes through policy-aware services."
---

# Task Contribution: Teacher and Moderator Judgment Inputs

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

## Technical Notes (IT)

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
