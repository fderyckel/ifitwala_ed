---
title: "Task Outcome: The Official Student-Level Assessment Record"
slug: task-outcome
category: Assessment
doc_order: 7
version: "1.1.0"
last_change_date: "2026-03-12"
summary: "Maintain one authoritative outcome per student per delivery, with official scores, criterion truth, statuses, and publication controls."
seo_title: "Task Outcome: The Official Student-Level Assessment Record"
seo_description: "Maintain one authoritative outcome per student per delivery, with official scores, criterion truth, statuses, and publication controls."
---

## Task Outcome: The Official Student-Level Assessment Record

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`, `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py`, `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: `ifitwala_ed/assessment/doctype/task_outcome/test_task_outcome.py`

`Task Outcome` is the institutional truth row for a student on a specific delivery. Submissions and contributions can evolve over time, but official grading and publication state live here.

Current workspace note: the outcome model itself is implemented, but generation is only as reliable as the delivery path that actually reaches delivery submission semantics.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`, `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py`
Test refs: `ifitwala_ed/assessment/doctype/task_outcome/test_task_outcome.py`

- Create the parent `Task Delivery` first.
- Ensure the target student belongs to the linked group at generation time.
- Lock grading policy inputs at delivery level before active grading begins.

## Where It Is Used Across the ERP

Status: Implemented
Code refs: `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/api/outcome_publish.py`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/assessment/term_reporting.py`
Test refs: `ifitwala_ed/assessment/doctype/task_outcome/test_task_outcome.py`

- Receives evidence from [**Task Submission**](/docs/en/task-submission/).
- Receives grading and moderation input through [**Task Contribution**](/docs/en/task-contribution/).
- Stores official criterion truth via [**Task Outcome Criterion**](/docs/en/task-outcome-criterion/).
- Gradebook reads outcomes through `ifitwala_ed/api/gradebook.py`.
- Publication controls run through `ifitwala_ed/api/outcome_publish.py`.
- Guardian snapshots read published outcomes via `ifitwala_ed/api/guardian_home.py`.
- Term reporting aggregates outcomes in `ifitwala_ed/assessment/term_reporting.py`.

## Lifecycle and Linked Documents

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/assessment/task_delivery_service.py`, `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: `ifitwala_ed/assessment/doctype/task_outcome/test_task_outcome.py`

1. Generate outcomes from a launched delivery, one row per `Task Delivery x Student`.
2. Accept submissions and contributions over time while preserving auditability.
3. Recompute official truth from contribution services, not from client-side gradebook math.
4. Publish and unpublish outcomes as a controlled visibility action.

Current workspace drift:

- Outcomes are supposed to appear when the parent delivery is launched.
- The current overlay creation path can leave draft deliveries with no generated outcomes.
- When that happens, gradebook shows an empty roster because it correctly reads `Task Outcome` rows only.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: None

- [**Task Delivery**](/docs/en/task-delivery/)
- [**Task Outcome Criterion**](/docs/en/task-outcome-criterion/)
- [**Task Submission**](/docs/en/task-submission/)
- [**Task Contribution**](/docs/en/task-contribution/)
- [**Course Term Result**](/docs/en/course-term-result/)
- [**Reporting Cycle**](/docs/en/reporting-cycle/)

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`, `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py`, `ifitwala_ed/assessment/task_outcome_service.py`, `ifitwala_ed/api/gradebook.py`
Test refs: `ifitwala_ed/assessment/doctype/task_outcome/test_task_outcome.py`

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py`
- **Required fields (`reqd=1`)**:
  - `task_delivery` (`Link` -> `Task Delivery`)
  - `task` (`Link` -> `Task`)
  - `student` (`Link` -> `Student`)
- **Child table**:
  - `official_criteria` (`Task Outcome Criterion`)
- **Lifecycle hooks in controller**:
  - `before_validate`
  - `validate`
  - `on_update`
  - `on_doctype_update`

### Current Contract

- `before_validate()` backfills delivery context, blocks identity mutation, and guards against duplicate outcomes.
- `validate()` enforces procedural-status coherence, release consistency, and grade symbol/value checks against grade scale.
- `on_update()` records info comments when official values are edited directly.
- `task_outcome_service.py` is the canonical official-truth recompute layer.
- `api/gradebook.py` and reporting readers consume outcome truth and outcome criterion truth rather than computing totals client-side.

### Current Drift To Preserve In Review

- The outcome table is canonical, but delivery launch drift can prevent rows from being created.
- That generation gap must be fixed at the delivery layer, not by teaching gradebook to invent roster rows client-side.
- Any implementation change here must keep the outcome fact-table rule intact: correctness belongs on the server.
