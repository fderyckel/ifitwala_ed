---
title: "Task Outcome: The Official Student-Level Assessment Record"
slug: task-outcome
category: Assessment
doc_order: 7
summary: "Maintain one authoritative outcome per student per delivery, with official scores/grades, criterion truth, statuses, and publication controls."
seo_title: "Task Outcome: The Official Student-Level Assessment Record"
seo_description: "Maintain one authoritative outcome per student per delivery, with official scores/grades, criterion truth, statuses, and publication controls."
---

## Task Outcome: The Official Student-Level Assessment Record

## Before You Start (Prerequisites)

- Submit the parent `Task Delivery` first; outcomes are generated from delivery + student roster.
- Ensure the student is part of the linked group at generation time.
- Lock grading policy inputs at delivery level before active grading begins.

`Task Outcome` is the institutional truth row for a student on a specific delivery. Submissions and contributions can evolve, but the outcome is where official status and released results live.

<Callout type="tip" title="Core guarantee">
Exactly one outcome exists for each `Task Delivery × Student` pair, protected by controller guards and a database unique index.
</Callout>

## Where It Is Used Across the ERP

- Generated automatically from [**Task Delivery**](/docs/en/task-delivery/) submission.
- Receives evidence from [**Task Submission**](/docs/en/task-submission/).
- Receives teacher/moderation input through [**Task Contribution**](/docs/en/task-contribution/).
- Stores official criterion truth via child table `Task Outcome Criterion`.
- Publication pipeline:
  - `ifitwala_ed.api.outcome_publish.publish_outcomes`
  - `ifitwala_ed.api.outcome_publish.unpublish_outcomes`
- Staff grading surfaces:
  - gradebook drawer/grid endpoints in `ifitwala_ed/api/gradebook.py` (`get_grid`, `get_drawer`, submit/moderate actions)
  - staff analytics trend in `ifitwala_ed/api/attendance.py` (Academic Standing from Task Outcome values)
- Guardian portal snapshots:
  - `ifitwala_ed.api.guardian_home.get_guardian_home_snapshot` uses published outcomes for recent task results.
- Term reporting source data:
  - `ifitwala_ed/assessment/term_reporting.py` aggregates outcomes into [**Course Term Result**](/docs/en/course-term-result/).

## Lifecycle and Linked Documents

1. Generate outcomes from submitted delivery (one row per student).
2. Accept submissions and contribution inputs over time while preserving grading traceability.
3. Maintain official criterion and grade truth in this doctype.
4. Publish/unpublish outcomes as part of controlled communication and reporting workflows.

<Callout type="warning" title="Identity immutability">
Outcome identity (`task_delivery`, `task`, `student`) is protected by controller and index guards to prevent duplicate truth rows.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py`
- **Required fields (`reqd=1`)**:
  - `task_delivery` (`Link` -> `Task Delivery`)
  - `task` (`Link` -> `Task`)
  - `student` (`Link` -> `Student`)
- **Lifecycle hooks in controller**: `before_validate`, `validate`, `on_update`, `on_doctype_update`
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Task Outcome` (`ifitwala_ed/assessment/doctype/task_outcome/`)
- **Autoname**: `TOU-{YYYY}-{MM}-{#####}`
- **Child table**: `official_criteria` (`Task Outcome Criterion`)
- **Key links**:
  - `task_delivery`, `task`, `student`, `student_group`, `grade_scale`, `school`, `academic_year`, `course`, `program`, `course_group`
- **Lifecycle behavior** (`task_outcome.py`):
  - `before_validate`:
    - requires `task_delivery` + `student`
    - backfills denormalized context from delivery
    - blocks identity mutation on existing rows
    - blocks duplicate outcomes
  - `validate`:
    - procedural status coherence (`Excused`, `Extension Granted`)
    - release/official-result consistency checks
    - grade symbol/value validation against grade scale
    - captures official field edits for audit
  - `on_update`:
    - writes info comments when official values are edited directly
- **Hard DB invariant**:
  - unique index on (`task_delivery`, `student`) enforced in `on_doctype_update`
- **Service orchestration**:
  - official recomputation: `assessment/task_outcome_service.py`
  - new-evidence flag handling: `mark_new_submission_seen`
- **Desk client script**: stub-only (`task_outcome.js`)
- **Architecture guarantees (embedded from assessment doctrine)**:
  - outcome is the official fact table; submissions and contributions are supporting layers
  - per-criterion official results are always preserved; task totals are strategy-dependent
  - publication status is a visibility gate and does not redefine grading truth

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | Yes | Yes | Yes |

## Related Docs

- [**Task Delivery**](/docs/en/task-delivery/)
- [**Task Submission**](/docs/en/task-submission/)
- [**Task Contribution**](/docs/en/task-contribution/)
- [**Course Term Result**](/docs/en/course-term-result/)
- [**Reporting Cycle**](/docs/en/reporting-cycle/)
