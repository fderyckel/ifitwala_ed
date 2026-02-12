---
title: "Reporting Cycle: Controlling When Grades Become Official Term Truth"
slug: reporting-cycle
category: Assessment
doc_order: 10
summary: "Define reporting scope and lifecycle, then generate/freeze term results with explicit cutoffs and governance controls."
---

# Reporting Cycle: Controlling When Grades Become Official Term Truth

`Reporting Cycle` is the control point between live assessment activity and official term reporting. It determines scope, timing, and state transitions for term-grade production.

<Callout type="warning" title="Snapshot boundary">
A reporting cycle is where mutable grading activity becomes institutional record. Treat cycle transitions as governance events, not routine edits.
</Callout>

## Where It Is Used Across the ERP

- Drives creation and lifecycle of [**Course Term Result**](/docs/en/course-term-result/).
- API surfaces:
  - `ifitwala_ed.api.term_reporting.get_cycle_summary`
  - `ifitwala_ed.api.term_reporting.get_course_term_results`
- Server orchestration:
  - `ifitwala_ed.assessment.term_reporting.recalculate_course_term_results`
  - `ifitwala_ed.assessment.term_reporting.generate_student_term_reports`
- Student reporting models:
  - `Student Term Report` links to Reporting Cycle.

## Technical Notes (IT)

- **DocType**: `Reporting Cycle` (`ifitwala_ed/assessment/doctype/reporting_cycle/`)
- **Scope links**: `school`, `academic_year`, `term`, optional `program`
- **Validation rules** (`reporting_cycle.py`):
  - uniqueness guard by scope + optional name/program context
  - `teacher_edit_close` required before `Locked`/`Published`
  - `task_cutoff_date` required before opening/processing lifecycle states
- **Whitelisted document methods**:
  - `recalculate_course_results` (queued long job)
  - `generate_student_reports`
- **Indexing**:
  - index on (`school`, `academic_year`, `term`, `program`)
- **Desk client script**: stub-only (`reporting_cycle.js`)
- **Architecture guarantees (embedded from term-reporting notes)**:
  - reporting lifecycle is explicit (`Draft → Open → Calculated → Locked → Published`)
  - reporting is a controlled snapshot boundary, not a live gradebook view
  - once locked/published, recalculation and edits must follow governed override/re-open pathways only

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | No | No | No |
| `Academic Staff` | Yes | No | No | No |

## Related Docs

- [**Course Term Result**](/docs/en/course-term-result/)
- [**Task Outcome**](/docs/en/task-outcome/)
- [**Grade Scale**](/docs/en/grade-scale/)
