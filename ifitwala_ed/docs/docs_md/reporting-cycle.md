---
title: "Reporting Cycle: Controlling When Grades Become Official Term Truth"
slug: reporting-cycle
category: Assessment
doc_order: 10
version: "1.0.4"
last_change_date: "2026-04-25"
summary: "Define reporting scope and lifecycle, then generate/freeze term results with explicit cutoffs and governance controls."
seo_title: "Reporting Cycle: Controlling When Grades Become Official Term Truth"
seo_description: "Define reporting scope and lifecycle, then generate/freeze term results with explicit cutoffs and governance controls."
---

## Reporting Cycle: Controlling When Grades Become Official Term Truth

## Before You Start (Prerequisites)

- Create `School`, `Academic Year`, and `Term` records first for cycle scope.
- Configure an `Assessment Scheme` if the term should use explicit category, task-weight, total-points, criteria, or manual-final calculation policy.
- Ensure grading activity exists in that scope (`Task Outcome` data) before recalculation/report generation.
- Set cutoff and instructor-edit-close dates before locking or publishing a cycle.

`Reporting Cycle` is the control point between live assessment activity and official term reporting. It determines scope, timing, and state transitions for term-grade production.

<Callout type="warning" title="Snapshot boundary">
A reporting cycle is where mutable grading activity becomes institutional record. Treat cycle transitions as governance events, not routine edits.
</Callout>

## Where It Is Used Across the ERP

- Drives creation and lifecycle of [**Course Term Result**](/docs/en/course-term-result/).
- Snapshots the resolved [**Assessment Scheme**](/docs/en/assessment-scheme/) policy used for calculation.
- API surfaces:
  - `ifitwala_ed.api.term_reporting.get_cycle_summary`
  - `ifitwala_ed.api.term_reporting.get_course_term_results`
  - `ifitwala_ed.api.term_reporting.get_review_surface`
  - `ifitwala_ed.api.term_reporting.queue_review_action`
- Server orchestration:
  - `ifitwala_ed.assessment.term_reporting.recalculate_course_term_results`
  - `ifitwala_ed.assessment.term_reporting.generate_student_term_reports`
- Student reporting models:
  - `Student Term Report` links to Reporting Cycle.

## Lifecycle and Linked Documents

1. Define cycle scope (`school`, `academic_year`, `term`, optional `program`) first.
2. Optionally select a default assessment scheme; active course/program-scoped schemes can still override by specificity during calculation.
3. Set cutoff and teacher edit-close windows before opening operational reporting steps.
4. Run course-result recalculation and generate student reports through named cycle actions.
5. Lock/publish when governance sign-off is complete and term outcomes are final.

<Callout type="info" title="Governance checkpoint">
Treat status changes in reporting cycles as governance events with clear owners, not routine UI clicks.
</Callout>

## Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | Yes | Yes |
| `Instructor` | Yes | No | No | No |
| `Academic Staff` | Yes | No | No | No |

## Related Docs

<RelatedDocs
  slugs="assessment-scheme,course-term-result,task-outcome,grade-scale"
  title="Related Docs"
/>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/assessment/doctype/reporting_cycle/reporting_cycle.json`
- **Controller file**: `ifitwala_ed/assessment/doctype/reporting_cycle/reporting_cycle.py`
- **Required fields (`reqd=1`)**: none at schema level; controller/workflow rules enforce operational completeness where applicable.
- **Lifecycle hooks in controller**: `validate`, `on_doctype_update`
- **Operational/public methods**: `recalculate_course_results`, `generate_student_reports`

- **DocType**: `Reporting Cycle` (`ifitwala_ed/assessment/doctype/reporting_cycle/`)
- **Scope links**: `school`, `academic_year`, `term`, optional `program`
- **Assessment policy fields**: `assessment_scheme`, `assessment_calculation_method`, `assessment_scheme_snapshot`
- **Validation rules** (`reporting_cycle.py`):
  - uniqueness guard by scope + optional name/program context
  - `teacher_edit_close` required before `Locked`/`Published`
  - `task_cutoff_date` required before opening/processing lifecycle states
  - retired schemes are blocked; program-specific schemes require program-specific cycles; course-specific schemes are resolved during calculation rather than selected directly on the cycle
- **Whitelisted document methods**:
  - `recalculate_course_results` (queued long job)
  - `generate_student_reports`
- **Staff SPA review surface**:
  - `/staff/term-reporting` loads a bounded, school-scoped review payload from `api/term_reporting.py::get_review_surface()`
  - the review surface displays frozen result rows, readiness checks, and calculation components
  - approved actions queue long jobs for recalculation or term-report generation; they do not run heavy generation in the request path
  - recalculation is blocked from this surface once a cycle is `Locked` or `Published`
- **Indexing**:
  - index on (`school`, `academic_year`, `term`, `program`)
- **Desk client script**: stub-only (`reporting_cycle.js`)
- **Architecture guarantees (embedded from term-reporting notes)**:
  - reporting lifecycle is explicit (`Draft → Open → Calculated → Locked → Published`)
  - reporting is a controlled snapshot boundary, not a live gradebook view
  - once locked/published, recalculation and edits must follow governed override/re-open pathways only
