---
title: "Course Term Result: The Frozen Record of Term Performance"
slug: course-term-result
category: Assessment
doc_order: 11
version: "1.0.0"
last_change_date: "2026-02-25"
summary: "Store one immutable term-grade record per student-course-cycle, including calculated values, overrides, and audit-safe context fields."
seo_title: "Course Term Result: The Frozen Record of Term Performance"
seo_description: "Store one immutable term-grade record per student-course-cycle, including calculated values, overrides, and audit-safe context fields."
---

## Course Term Result: The Frozen Record of Term Performance

## Before You Start (Prerequisites)

- Create and configure the relevant `Reporting Cycle` first.
- Ensure source grading truth exists (`Task Outcome` data in scope) before generation.
- Generate/update results through reporting-cycle services; do not treat this as a hand-entered source doctype.

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

## Lifecycle and Linked Documents

1. Create and prepare a `Reporting Cycle` for the exact school/year/term scope.
2. Run cycle recalculation so results are generated from official `Task Outcome` truth.
3. Apply approved overrides only where policy requires human adjustment.
4. Publish/consume results in student term-reporting artifacts and downstream analytics.

<Callout type="warning" title="Source of truth boundary">
`Course Term Result` is a generated/frozen reporting record. Do not use it as a substitute for day-to-day grading workflows.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/course_term_result/course_term_result.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/course_term_result/course_term_result.py`
- **Required fields (`reqd=1`)**: none at schema level; controller/workflow rules enforce operational completeness where applicable.
- **Lifecycle hooks in controller**: `validate`, `on_doctype_update`
- **Operational/public methods**: none beyond standard document behavior.

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
