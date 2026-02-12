---
title: "Course Term Result: The Frozen Record of Term Performance"
slug: course-term-result
category: Assessment
doc_order: 11
summary: "Store one immutable term-grade record per student-course-cycle, including calculated values, overrides, and audit-safe context fields."
---

# Course Term Result: The Frozen Record of Term Performance

`Course Term Result` is the durable term-level record generated from assessment outcomes. It is designed for reporting reliability, not live-grade experimentation.

<Callout type="tip" title="Audit-ready design">
Course Term Result intentionally duplicates context fields (student, course, program, year, term, grade scale) so historical reports stay reproducible even when operational structures change later.
</Callout>

## Where It Is Used Across the ERP

- Produced by [**Reporting Cycle**](/docs/en/reporting-cycle/) orchestration.
- Generated from aggregated [**Task Outcome**](/docs/en/task-outcome/) truth in `assessment/term_reporting.py`.
- Queried by `ifitwala_ed.api.term_reporting.get_course_term_results`.
- Linked into student reporting presentation:
  - `Student Term Report Course` child rows reference Course Term Result.

## Technical Notes (IT)

- **DocType**: `Course Term Result` (`ifitwala_ed/assessment/doctype/course_term_result/`)
- **Key links**:
  - `reporting_cycle`, `student`, `program_enrollment`, `course`, `program`, `academic_year`, `term`, `instructor`, `grade_scale`, `moderated_by`, `calculated_by`
- **Validation** (`course_term_result.py`):
  - `is_override` kept in sync with `override_grade_value`
- **Primary producer**:
  - `assessment/term_reporting.py` (`upsert_course_term_results`)
- **Performance indexes**:
  - (`reporting_cycle`, `student`)
  - (`reporting_cycle`, `program_enrollment`, `course`)
  - (`reporting_cycle`, `course`)
  - (`reporting_cycle`, `program`)
- **Desk client script**: stub-only (`course_term_result.js`)
- **Architecture guarantees (embedded from term-reporting notes)**:
  - one row represents one `student × course × term × reporting cycle` fact
  - values are materialized from official Task Outcome truth and are not live-recomputed by UI views
  - override paths retain original calculated values for auditability

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | Yes | Yes | Yes |
| `Counsellor` | Yes | No | No | No |

## Related Docs

- [**Reporting Cycle**](/docs/en/reporting-cycle/)
- [**Task Outcome**](/docs/en/task-outcome/)
- [**Grade Scale**](/docs/en/grade-scale/)
