---
title: "School: Academic Scope and Hierarchy Node"
slug: school
category: School Settings
doc_order: 1
summary: "Define schools as a NestedSet hierarchy anchored to an Organization for admissions, academics, calendars, and policy scope."
seo_title: "School: Academic Scope and Hierarchy Node"
seo_description: "Define schools as a NestedSet hierarchy anchored to an Organization for admissions, academics, calendars, and policy scope."
---

## School: Academic Scope and Hierarchy Node

`School` is the academic scope record used by admissions, scheduling, academic year visibility, and governance policy matching.

## What It Enforces

- School is a tree (`NestedSet`) using `parent_school`.
- `organization` is required and parent/child schools must share the same organization.
- Parent school must be a group school (`is_group = 1`).
- Organization change is blocked for schools that already have child schools.
- Attendance thresholds are validated and parent defaults can be inherited on new child schools.
- Publishing requires a `website_slug`.

## Where It Is Used Across the ERP

- [**Student Applicant**](/docs/en/student-applicant/):
  - immutable admissions anchor (`organization` + `school`)
  - academic-year scope validation and policy school matching
- [**Institutional Policy**](/docs/en/institutional-policy/):
  - optional policy school scope targeting
- [**Organization**](/docs/en/organization/):
  - every school belongs to one organization

## Technical Notes (IT)

- **DocType**: `School` (`ifitwala_ed/school_settings/doctype/school/`)
- **Autoname**: `field:school_name`
- **Tree config**:
  - class `School(NestedSet)`
  - `nsm_parent_field = parent_school`
- **Required fields (`reqd=1`)**:
  - `school_name`
  - `abbr`
  - `organization`
- **Controller hooks**:
  - `validate`, `on_update`, `after_save`, `on_trash`, `after_rename`
- **Whitelisted methods**:
  - `get_children`
  - `add_node`
  - `enqueue_replace_abbr`
  - `replace_abbr`
  - `add_school_to_navbar`

## Related Docs

- [**Organization**](/docs/en/organization/) - legal entity root and hierarchy container
- [**Student Applicant**](/docs/en/student-applicant/) - admissions anchor and readiness pipeline
- [**Institutional Policy**](/docs/en/institutional-policy/) - organization/school policy scope source
