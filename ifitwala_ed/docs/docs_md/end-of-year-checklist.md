---
title: "End Of Year Checklist: Controlled Year-Close Actions"
slug: end-of-year-checklist
category: Schedule
doc_order: 4
version: "1.0.0"
last_change_date: "2026-03-29"
summary: "Run controlled, scope-aware year-close actions for academic years, terms, program enrollments, and student groups across a selected school branch."
seo_title: "End Of Year Checklist: Controlled Year-Close Actions"
seo_description: "Run controlled, scope-aware year-close actions for academic years, terms, program enrollments, and student groups across a selected school branch."
---

## End Of Year Checklist: Controlled Year-Close Actions

`End of Year Checklist` is the single-record year-close tool for the Schedule domain. It resolves a school scope, matches Academic Years by shared academic-year name across that scope, and then runs bounded archival or retirement actions against affected records.

## Before You Start (Prerequisites)

- Set the operator’s default school correctly unless acting as `Administrator` or `System Manager`.
- Confirm the selected `Academic Year` belongs to the selected `School`.
- Move checklist `status` to `In Progress` before running any action.

## Why It Matters

- It centralizes year-close actions in one governed place.
- It enforces school-scope and parent-school permission rules before any mutation.
- It keeps archival actions bounded to the resolved school branch and AY-name match set.

## Where It Is Used Across the ERP

- Archives `Academic Year` rows and hides them from admission visibility.
- Archives `Term` rows.
- Archives `Program Enrollment` rows.
- Retires `Student Group` rows.
- Triggers professional-development year-close cleanup when academic years are archived.

## Lifecycle and Linked Documents

1. Select `school` and `academic_year`.
2. The checklist validates that the Academic Year belongs to the selected school.
3. The operator sets `status` to `In Progress`.
4. Each action button resolves scope and then runs one bounded update path:
   - `archive_academic_year`
   - `archive_terms`
   - `archive_program_enrollment`
   - `archive_student_groups`
5. Once operationally complete, the checklist can be marked `Completed`, after which actions are locked.

## Related Docs

- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Student Group**](/docs/en/student-group/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
- **Singleton**: yes (`issingle = 1`)
- **Required fields (`reqd=1`)**:
  - `school` (`Link` -> `School`)
  - `academic_year` (`Link` -> `Academic Year`)
  - `status` (`Select`)
- **Lifecycle hooks in controller**:
  - `validate`
- **Whitelisted operational methods**:
  - `archive_academic_year()`
  - `archive_terms()`
  - `archive_program_enrollment()`
  - `archive_student_groups()`
  - `school_link_query(...)`
  - `academic_year_link_query(...)`
  - `get_scope_preview(...)`

### Current Contract

- `validate()` enforces:
  - school selection is allowed for the current operator
  - Academic Year belongs to the selected school
- `_resolve_scope()`:
  - requires `status = In Progress`
  - resolves descendant-school scope from the selected school
  - finds matching Academic Year rows by `academic_year_name` across that scope
- `archive_academic_year()`:
  - archives Academic Years
  - disables `visible_to_admission`
  - invokes professional-development cleanup
- `archive_terms()` archives Terms for the resolved AY set.
- `archive_program_enrollment()` archives Program Enrollments for the resolved AY and school scope.
- `archive_student_groups()` retires Student Groups for the resolved AY and school scope.

### Permission and Visibility Notes

- Full create/write access in schema currently exists for:
  - `System Manager`
  - `Academic Admin`
  - `Curriculum Coordinator`
  - `Counselor`
- Parent-school selection is further restricted in controller logic:
  - non-system users must stay inside their default-school branch
  - selecting a parent school requires the user’s default school to match that parent school
  - selecting a parent school also requires the `Academic Admin` role

### Current Constraints To Preserve In Review

- Actions must remain idempotent and bounded to the resolved scope.
- Scope resolution depends on shared Academic Year name across the school branch; changing that rule would alter the closure contract.
- Checklist actions must remain locked unless status is `In Progress`, and after completion they must not be rerunnable without an explicit workflow decision.
