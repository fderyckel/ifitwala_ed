---
title: "Student Cohort: Cohort Naming and Enrollment Scope"
slug: student-cohort
category: Schedule
doc_order: 3
version: "1.0.0"
last_change_date: "2026-03-29"
summary: "Define a named cohort label that can be attached to offerings, enrollments, groups, and analytics slices."
seo_title: "Student Cohort: Cohort Naming and Enrollment Scope"
seo_description: "Define a named cohort label that can be attached to offerings, enrollments, groups, and analytics slices."
---

## Student Cohort: Cohort Naming and Enrollment Scope

`Student Cohort` is the canonical named cohort label used across the Schedule domain. In the current workspace it is intentionally thin: it provides a stable cohort identity used by offerings, enrollments, cohort-based student groups, and reporting filters.

## Before You Start (Prerequisites)

- Decide the cohort naming convention before linking it to operational records.
- Create the cohort before assigning it to `Program Offering`, `Program Enrollment`, or cohort-based `Student Group` records.

## Why It Matters

- It gives cohort-based groups a stable target instead of free-text naming.
- It lets offerings mirror cohort membership into enrollments.
- It gives analytics and dashboards a consistent cohort dimension.

## Where It Is Used Across the ERP

- `Program Offering.student_cohort`
- `Program Enrollment.cohort`
- `Student Group.cohort` for `group_based_on = Cohort`
- cohort-scoped analytics and dashboard filters

## Lifecycle and Linked Documents

1. Create the cohort with `cohort_name`.
2. Optionally add `cohort_abbreviation`.
3. Use the cohort on offerings, enrollments, and cohort-based Student Groups.

## Related Docs

<RelatedDocs
  slugs="program-offering,program-enrollment,student-group"
  title="Related Docs"
/>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/student_cohort/student_cohort.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/student_cohort/student_cohort.py`
- **Required fields (`reqd=1`)**:
  - `cohort_name` (`Data`)
- **Optional fields**:
  - `cohort_abbreviation` (`Data`)
- **Lifecycle hooks in controller**:
  - none beyond the base `Document` implementation

### Current Contract

- `Student Cohort` is currently schema-driven with no custom controller logic.
- `cohort_name` is the naming field and must remain unique.
- The doctype’s operational value comes from where other doctypes reference it, not from local workflow logic.

### Permission and Visibility Notes

- Full create/write/delete access in schema currently exists for:
  - `System Manager`
  - `Schedule Maker`
  - `Academic Admin`
  - `Academic Assistant`
  - `Admission Manager`
  - `Curriculum Coordinator`
- Read-only schema access currently exists for:
  - `Instructor`
  - `Academic Staff`
  - `Admission Officer`
  - `Accreditation Visitor`

### Current Constraints To Preserve In Review

- Keep `Student Cohort` as a stable naming contract rather than embedding workflow logic here.
- Cohort-based validation should continue to live in the parent doctypes that consume the cohort, especially `Program Enrollment` and `Student Group`.
