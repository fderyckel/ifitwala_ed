---
title: "Grade Scale: Converting Scores into Institutional Meaning"
slug: grade-scale
category: Assessment
doc_order: 3
summary: "Define grade boundaries once and apply them consistently across tasks, outcomes, moderation, and term reporting."
---

# Grade Scale: Converting Scores into Institutional Meaning

A score by itself is not policy. `Grade Scale` turns raw numbers into grade symbols and descriptors your institution stands behind.

<Callout type="tip" title="Consistency win">
When grade boundaries live in one master place, teachers can grade quickly while school leadership still gets coherent, auditable results.
</Callout>

## Where It Is Used Across the ERP

- [**Task**](/docs/en/task/) defaults (`default_grade_scale`).
- [**Task Delivery**](/docs/en/task-delivery/) grading context (`grade_scale`).
- [**Task Contribution**](/docs/en/task-contribution/) value validation (`grade` ↔ `grade_value`).
- [**Task Outcome**](/docs/en/task-outcome/) official grade/grade value validation.
- [**Task Rubric Version**](/docs/en/task-rubric-version/) rubric snapshot policy context.
- [**Course Term Result**](/docs/en/course-term-result/) stored term-grade context.
- Term reporting services:
  - `ifitwala_ed/assessment/task_outcome_service.py`
  - `ifitwala_ed/assessment/term_reporting.py`
  - `ifitwala_ed/assessment/grade_scale_utils.py`
- Curriculum and scheduling defaults:
  - [**Program**](/docs/en/program/)
  - [**Course**](/docs/en/course/)
  - `Program Offering` and `Program Offering Course`

## Technical Notes (IT)

- **DocType**: `Grade Scale` (`ifitwala_ed/assessment/doctype/grade_scale/`)
- **Autoname**: `field:grade_scale_name`
- **Child table**: `Grade Scale Interval` (`boundaries`)
- **Controller**: thin (`pass`) with core behavior handled by service utilities.
- **Utility contracts**:
  - `grade_scale_utils.grade_label_to_numeric`
  - `task_outcome_service.resolve_grade_symbol`
  - term reporting grade-symbol resolution during snapshot generation
- **Desk UI**: standard form/list (client script stub only)
- **Workspace surfaces**:
  - `Curriculum` workspace
  - `Admin` workspace

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Staff` | Yes | No | No | No |
| `Instructor` | Yes | No | No | No |

## Authoritative References

- `ifitwala_ed/docs/assessment/01_assessment_notes.md`
- `ifitwala_ed/docs/assessment/05_term_reporting_notes.md`

## Related Docs

- [**Assessment Criteria**](/docs/en/assessment-criteria/)
- [**Task Outcome**](/docs/en/task-outcome/)
- [**Course Term Result**](/docs/en/course-term-result/)
- [**Reporting Cycle**](/docs/en/reporting-cycle/)
