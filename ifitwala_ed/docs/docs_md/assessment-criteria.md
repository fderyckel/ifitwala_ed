---
title: "Assessment Criteria: Defining What Good Work Looks Like"
slug: assessment-criteria
category: Assessment
doc_order: 2
summary: "Create reusable criteria and performance levels that power rubric-based grading across tasks, outcomes, moderation, and reporting."
---

# Assessment Criteria: Defining What Good Work Looks Like

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

## Technical Notes (IT)

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

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | Yes | No | No |
| `Academic Admin` | Yes | Yes | Yes | Yes |

## Authoritative References

- `ifitwala_ed/docs/assessment/01_assessment_notes.md`
- `ifitwala_ed/docs/assessment/02_curriculum_relationship_notes.md`

## Related Docs

- [**Assessment Category**](/docs/en/assessment-category/)
- [**Task**](/docs/en/task/)
- [**Task Rubric Version**](/docs/en/task-rubric-version/)
- [**Task Outcome**](/docs/en/task-outcome/)
