---
title: "Task Rubric Version: Freezing Criteria at Delivery Time"
slug: task-rubric-version
category: Assessment
doc_order: 6
summary: "Snapshot rubric criteria per delivery so grading remains historically stable even if the master task rubric changes later."
seo_title: "Task Rubric Version: Freezing Criteria at Delivery Time"
seo_description: "Snapshot rubric criteria per delivery so grading remains historically stable even if the master task rubric changes later."
---

## Task Rubric Version: Freezing Criteria at Delivery Time

## Before You Start (Prerequisites)

- Prepare `Task` criteria templates first.
- Create rubric snapshots via `Task Delivery` submission flow, not ad-hoc manual entry.
- Use `Criteria` grading mode on delivery when rubric snapshot behavior is required.

`Task Rubric Version` is the historical safety net for criteria-based grading. It preserves exactly which criteria/weights applied when a delivery went live.

<Callout type="note" title="Why this exists">
Without snapshots, later edits to task criteria would silently rewrite grading history. Rubric versions prevent that.
</Callout>

## Where It Is Used Across the ERP

- Created from [**Task Delivery**](/docs/en/task-delivery/) on submit for criteria-mode deliveries.
- Stores criteria rows (`Task Rubric Criterion`) copied from [**Task**](/docs/en/task/) template criteria.
- Read by official outcome computation in `assessment/task_outcome_service.py` to apply criterion weighting correctly.
- Linked back to grade-scale policy via [**Grade Scale**](/docs/en/grade-scale/).

## Technical Notes (IT)

- **DocType**: `Task Rubric Version` (`ifitwala_ed/assessment/doctype/task_rubric_version/`)
- **Autoname**: `TRV-{YYYY}-{#####}`
- **Child table**: `criteria` (`Task Rubric Criterion`)
- **Key links**:
  - `task`
  - `task_delivery`
  - `grade_scale`
- **Controller**: thin (`pass`), with creation/orchestration handled by Task Delivery controller.
- **Creation path**:
  - `TaskDelivery._ensure_rubric_snapshot` builds rows at submit time
  - guards against empty criteria snapshots
- **Desk client script**: stub-only (`task_rubric_version.js`)
- **Architecture guarantees (embedded from assessment doctrine)**:
  - rubric version preserves criteria structure used at grading time
  - snapshot behavior protects auditability when Task criteria evolve after release
  - criterion totals remain strategy-dependent (`Sum Total` vs `Separate Criteria`)

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |

## Related Docs

- [**Task**](/docs/en/task/)
- [**Task Delivery**](/docs/en/task-delivery/)
- [**Task Contribution**](/docs/en/task-contribution/)
- [**Task Outcome**](/docs/en/task-outcome/)
