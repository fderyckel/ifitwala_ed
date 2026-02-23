---
title: "Assessment Criteria: Defining What Good Work Looks Like"
slug: assessment-criteria
category: Assessment
doc_order: 2
summary: "Create reusable criteria and performance levels that power rubric-based grading across tasks, outcomes, moderation, and reporting."
seo_title: "Assessment Criteria: Defining What Good Work Looks Like"
seo_description: "Create reusable criteria and performance levels that power rubric-based grading across tasks, outcomes, moderation, and reporting."
---

## Assessment Criteria: Defining What Good Work Looks Like

## Before You Start (Prerequisites)

- Define rubric language and criterion naming standards first.
- If you use course-group-aware naming, create `Course Group` records first.
- Create reusable criteria before building `Task` templates that reference them.

`Assessment Criteria` is where schools encode the quality standards behind grading. Instead of re-writing rubrics for every task, you define criteria once and reuse them across classes and years.

<Callout type="info" title="Design principle">
Criteria are curriculum truth, not one-off task notes. That keeps grading consistent even when teachers, terms, or delivery contexts change.
</Callout>

## Where It Is Used Across the ERP

- [**Task**](/docs/en/task/) via `Task Template Criterion` child rows (`task_criteria`).
- [**Task Rubric Version**](/docs/en/task-rubric-version/) via `Task Rubric Criterion` snapshots.
- [**Task Contribution**](/docs/en/task-contribution/) via `Task Contribution Criterion` marks.
- [**Task Outcome**](/docs/en/task-outcome/) via `Task Outcome Criterion` official criterion results.
- Curriculum models:
  - [**Course**](/docs/en/course/) via `Course Assessment Criteria`
  - `course_group` linking for framework/program organization
- Staff gradebook rendering (`/staff/gradebook`) for criteria-level inputs and feedback.
- Desk Workspaces:
  - `Curriculum` workspace
  - `Admin` workspace

## Lifecycle and Linked Documents

1. Design reusable criteria and performance levels before authoring large task sets.
2. Attach criteria to `Task` templates so classroom use is standardized.
3. When deliveries are submitted in criteria mode, criteria are snapshotted into `Task Rubric Version`.
4. Teacher contributions and official outcomes then evaluate learners against those frozen criteria.

<Callout type="warning" title="Change control">
Renaming or redefining criteria after active deliveries can create moderation confusion; treat criteria edits as controlled curriculum changes.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/assessment_criteria/assessment_criteria.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/assessment_criteria/assessment_criteria.py`
- **Required fields (`reqd=1`)**:
  - `assessment_criteria` (`Data`)
- **Lifecycle hooks in controller**: `validate`
- **Operational/public methods**: `autoname`

- **DocType**: `Assessment Criteria` (`ifitwala_ed/assessment/doctype/assessment_criteria/`)
- **Autoname logic** (`autoname` in controller):
  - with `course_group`/`abbr`: `Crit-<course_group>-<abbr>`
  - fallback: `CRIT-<derived_abbrev>`
  - `name` and hidden `title` are aligned to same stable code
- **Child table**: `Assessment Criteria Level` (`levels`)
- **Validation**:
  - blocks reserved/bad criteria names (`total`, `score`, `grade`, etc.)
- **Desk UI**:
  - currently standard form/list (no active custom client script)
- **Architecture guarantees (embedded from assessment doctrine)**:
  - criteria are curriculum artifacts reused across tasks; they are not task-local truth
  - criteria levels describe performance bands and descriptors only
  - numeric-to-grade conversion belongs to Grade Scale, not Assessment Criteria

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | Yes | No | No |
| `Academic Admin` | Yes | Yes | Yes | Yes |

## Related Docs

- [**Assessment Category**](/docs/en/assessment-category/)
- [**Task**](/docs/en/task/)
- [**Task Rubric Version**](/docs/en/task-rubric-version/)
- [**Task Outcome**](/docs/en/task-outcome/)
