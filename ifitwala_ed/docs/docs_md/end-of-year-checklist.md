---
title: "End Of Year Checklist: Controlled Year-Close And Curriculum Handover"
slug: end-of-year-checklist
category: Schedule
doc_order: 4
version: "1.1.0"
last_change_date: "2026-04-22"
summary: "Prepare next-year curriculum handover and run controlled, scope-aware year-close actions for academic years, terms, program enrollments, and student groups across a selected school branch."
seo_title: "End Of Year Checklist: Controlled Year-Close And Curriculum Handover"
seo_description: "Prepare next-year curriculum handover and run controlled, scope-aware closure actions across a selected school branch."
---

## End Of Year Checklist: Controlled Year-Close And Curriculum Handover

`End of Year Checklist` is the single-record year-close tool for the Schedule domain, and it now also provides a bounded curriculum handover helper for the next academic year. It resolves a school scope, matches Academic Years by shared academic-year name across that scope, and then lets staff prepare next-year `Course Plan` drafts before they run destructive closure actions.

## Before You Start (Prerequisites)

- Set the operator’s default school correctly unless acting as `Administrator` or `System Manager`.
- Confirm the selected `Academic Year` belongs to the selected `School`.
- Choose `Target Academic Year` before previewing or preparing curriculum handover.
- Move checklist `status` to `In Progress` before running destructive archive actions.

## Why It Matters

- It centralizes year-close actions in one governed place while also giving curriculum teams a low-friction handover step for the next year.
- It enforces school-scope and parent-school permission rules before any mutation.
- It keeps curriculum handover separate from destructive closure, so teams can prepare next-year planning before they archive the outgoing year.
- It keeps archival actions bounded to the resolved school branch and AY-name match set.

## Where It Is Used Across the ERP

- Previews and prepares next-year `Course Plan` drafts for the selected scope through `curriculum_target_academic_year`, `curriculum_preview`, and `Prepare Curriculum Handover`.
- Archives `Academic Year` rows and hides them from admission visibility.
- Archives `Term` rows.
- Archives `Program Enrollment` rows.
- Retires `Student Group` rows.
- Triggers professional-development year-close cleanup when academic years are archived.

## Lifecycle and Linked Documents

1. Select `school` and `academic_year`.
2. The checklist validates that the Academic Year belongs to the selected school.
3. If the school is preparing next year’s shared curriculum, select `curriculum_target_academic_year`.
4. `curriculum_preview` summarizes how many active source plans are ready, already prepared, blocked by missing target-year scope, or blocked by permission.
5. `Prepare Curriculum Handover` creates draft next-year `Course Plan` rows and draft `Unit Plan` copies for the ready source plans in scope. This action is non-destructive and does not require `status = In Progress`, but it is locked once the checklist is marked `Completed`.
6. The operator sets `status` to `In Progress` before running destructive year-close actions.
7. Each archive action button resolves scope and then runs one bounded update path:
   - `archive_academic_year`
   - `archive_terms`
   - `archive_program_enrollment`
   - `archive_student_groups`
8. Once operationally complete, the checklist can be marked `Completed`, after which both curriculum handover and closure actions are locked.

## Permission Matrix

Status: Implemented
Code refs: `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.json`, `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
Test refs: `ifitwala_ed/schedule/doctype/end_of_year_checklist/test_end_of_year_checklist.py`

- `System Manager`: full access across scopes, including parent-school cascade and curriculum handover.
- `Academic Admin`: full checklist use inside the allowed default-school branch, including parent-school cascade and curriculum handover.
- `Curriculum Coordinator`: may use the checklist and curriculum handover where school selection is allowed, but parent-school cascade still requires the `Academic Admin` role unless the user is `System Manager`.
- `Counselor`: schema write access exists, but the same server-side school-scope and parent-school restrictions still apply.

## Related Docs

- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Student Group**](/docs/en/student-group/)
- [**Course Plan**](/docs/en/course-plan/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
- **Singleton**: yes (`issingle = 1`)
- **Required fields (`reqd=1`)**:
  - `school` (`Link` -> `School`)
  - `academic_year` (`Link` -> `Academic Year`)
  - `status` (`Select`)
- **Operational fields added for adjacent curriculum prep**:
  - `curriculum_target_academic_year` (`Link` -> `Academic Year`)
  - `curriculum_preview` (`HTML`)
  - `prepare_curriculum_handover` (`Button`)
- **Lifecycle hooks in controller**:
  - `validate`
- **Whitelisted operational methods**:
  - `get_curriculum_handover_preview()`
  - `prepare_curriculum_handover()`
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
  - `curriculum_target_academic_year`, when provided, belongs to the selected school
- `_resolve_scope()`:
  - resolves descendant-school scope from the selected school
  - finds matching Academic Year rows by `academic_year_name` across that scope
- `get_curriculum_handover_preview()`:
  - does not require `status = In Progress`
  - resolves active source `Course Plan` rows in scope
  - matches the selected target academic-year name across the school branch
  - reports ready, existing-target, missing-target-year, and no-permission counts
- `prepare_curriculum_handover()`:
  - requires `curriculum_target_academic_year`
  - stays available until the checklist is marked `Completed`
  - creates draft next-year `Course Plan` rows scheduled for academic-year-start activation
  - duplicates governed `Unit Plan` rows and shared material placements without copying class-owned runtime
- destructive archive actions:
  - still require `status = In Progress`
  - still operate only on the resolved scope
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
- Curriculum handover must stay non-destructive and must not be documented as if it also handles enrollment rollover or class-runtime reuse.
- Destructive archive actions must remain locked unless status is `In Progress`.
- Once status is `Completed`, both curriculum handover and closure actions must stay locked unless an explicit workflow decision changes that contract.
