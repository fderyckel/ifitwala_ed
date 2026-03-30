---
title: "School: Academic Scope and Hierarchy Node"
slug: school
category: School Settings
doc_order: 1
version: "1.2.1"
last_change_date: "2026-03-28"
summary: "Define schools as a NestedSet hierarchy anchored to an Organization for admissions, academics, calendars, policy scope, and admissions health-readiness policy."
seo_title: "School: Academic Scope and Hierarchy Node"
seo_description: "Define schools as a NestedSet hierarchy anchored to an Organization for admissions, academics, calendars, policy scope, and admissions health-readiness policy."
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
- Public school website routes are served under `/schools/{website_slug}/...` via `School Website Page` records.
- First-time school publication now auto-prepares missing website defaults:
  - generates `website_slug` when blank
  - seeds canonical school pages (`/`, `about`, `admissions`, `programs`) when missing
  - publishes those canonical starter pages when the school itself is public
  - links default `Website SEO Profile` records on school pages when missing

## Where It Is Used Across the ERP

- [**Student Applicant**](/docs/en/student-applicant/):
  - immutable admissions anchor (`organization` + `school`)
  - academic-year scope validation and policy school matching
  - school-level approval gate toggle `require_health_profile_for_approval`
- [**Institutional Policy**](/docs/en/institutional-policy/):
  - optional policy school scope targeting
- [**Organization**](/docs/en/organization/):
  - every school belongs to one organization

## Related Docs

- [**Organization**](/docs/en/organization/) - legal entity root and hierarchy container
- [**Student Applicant**](/docs/en/student-applicant/) - admissions anchor and readiness pipeline
- [**Institutional Policy**](/docs/en/institutional-policy/) - organization/school policy scope source

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
- **Admissions readiness policy field**:
  - `require_health_profile_for_approval` (`Check`, default `1`) controls whether health clearance is required for applicant approval readiness at this school.
- **Website publication contract**:
  - `website_slug` identifies the school under `/schools/{website_slug}/...`
  - published navigation comes from `School Website Page.show_in_navigation`, not `Website Settings.top_bar_items`
  - first publish fills missing website slug and ensures default school website pages + SEO profiles without overwriting existing authored content
- **Controller hooks**:
  - `validate`, `on_update`, `after_save`, `on_trash`, `after_rename`
- **Whitelisted methods**:
  - `get_children`
  - `add_node`
  - `enqueue_replace_abbr`
  - `replace_abbr`
- **Abbreviation rename contract**:
  - `enqueue_replace_abbr` runs on the long queue because dependent record renames can be expensive.
  - `replace_abbr` only renames explicit school-scoped doctypes whose runtime names embed `School.abbr`: `Academic Year`, `School Calendar`, and `School Schedule`.
  - It must not perform generic table scans or interpolate arbitrary table names into SQL.
  - Surfaces that only read `School.abbr` dynamically are not renamed; they pick up the new abbreviation from the `School` record directly.
