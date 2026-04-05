---
title: "School: Academic Scope and Hierarchy Node"
slug: school
category: School Settings
doc_order: 1
version: "1.3.0"
last_change_date: "2026-04-05"
summary: "Define schools as NestedSet academic scope records anchored to an Organization, with hierarchy integrity, governed public media, website publication bootstrap, and explicit DocType permissions."
seo_title: "School: Academic Scope and Hierarchy Node"
seo_description: "Define schools as NestedSet academic scope records anchored to an Organization, with hierarchy integrity, governed public media, website publication bootstrap, and explicit DocType permissions."
---

## School: Academic Scope and Hierarchy Node

`School` is the canonical academic scope record used by admissions, academic calendars, school websites, and school-level policy matching.

[[fig:school-tree size=auto]]

## What It Enforces

- `School` is a tree (`NestedSet`) using `parent_school`.
- `school_name`, `abbr`, and `organization` are required.
- `abbr` is unique, trimmed, auto-derived from the school name when blank, and cannot exceed 5 characters on create.
- Parent school must be a group school (`is_group = 1`).
- Parent and child schools must belong to the same organization.
- A school with child schools cannot change `organization`.
- New child schools inherit attendance thresholds from the selected parent at create time.
- Attendance thresholds must stay within `0..100`, and warning must be greater than or equal to critical.
- Publishing requires a usable `website_slug`; when blank, save generates the next available slug automatically.
- Existing `School Website Page` rows are kept in sync with school publication state.
- First publish, or a publish-state repair path, prepares the canonical starter website pages and missing `Website SEO Profile` links without overwriting authored content.
- School logo and gallery images must resolve through governed Organization Media; direct unmanaged image values are rejected on save.
- A newly inserted school seeds its default academic load policy automatically.

## Where It Is Used Across the ERP

- [**Student Applicant**](/docs/en/student-applicant/):
  - immutable admissions anchor (`organization` + `school`)
  - academic-year scope validation and policy school matching
  - school-level approval gate `require_health_profile_for_approval`
- [**Institutional Policy**](/docs/en/institutional-policy/):
  - optional policy school scope targeting
- [**Organization**](/docs/en/organization/):
  - every school belongs to one organization
  - organization website default-school ownership points back to a school
- `School Website Page` / `Website SEO Profile`:
  - public school pages are rooted under `/schools/{website_slug}/...`
  - canonical starter pages are created from the school publication flow

## Permission and Scope Model

- `School` permissions are primarily defined by the DocType permission rows in `school.json`.
- Current runtime does **not** register `School`-specific `permission_query_conditions` or `has_permission` hooks in `ifitwala_ed/hooks.py`.
- That means the `School` controller enforces hierarchy, organization, publication, and governed-media invariants, but it does not add a custom descendant-scope visibility layer of its own.
- Effective record visibility can still be narrowed by standard Frappe permission machinery, including role permissions and configured `User Permission` / default-link constraints on a site.
- Tree endpoints `get_children` and `add_node` support the Desk tree UI; they do not establish a separate business permission model beyond the framework permission checks around the underlying DocType actions.

## Website and Governed Media Contract

- Public school routes resolve under `/schools/{website_slug}/...`.
- Published navigation comes from `School Website Page.show_in_navigation`, not `Website Settings.top_bar_items`.
- First publish auto-prepares missing defaults:
  - `website_slug`
  - canonical starter pages: `/`, `about`, `admissions`, `programs`
  - linked `Website SEO Profile` rows when missing
- If the school is published, the seeded canonical pages are published too.
- Desk uses governed upload flows for:
  - `Upload School Logo`
  - `Upload Gallery Image`
  - `Manage Organization Media`
  - `Open in Drive`
- Save-time server sync resolves `school_logo_file` and gallery `governed_file` rows into the current public `file_url` values visible to that school.
- Visibility is ancestor-aware:
  - school-owned media is visible to that school
  - ancestor-school media can be reused by descendant schools
  - organization-scoped media in the same organization lineage can be reused
  - sibling-school and sibling-organization media are not visible
- Abbreviation replacement is the only explicitly deferred mutation in this feature; `enqueue_replace_abbr` runs on the `long` queue because renaming dependent records can be expensive.

## Contract Matrix

Status: Implemented
Code refs:
- `ifitwala_ed/school_settings/doctype/school/school.py`
- `ifitwala_ed/school_settings/doctype/school/school.json`
- `ifitwala_ed/school_settings/doctype/school/school.js`
- `ifitwala_ed/website/bootstrap.py`
- `ifitwala_ed/utilities/organization_media.py`
- `ifitwala_ed/utilities/governed_uploads.py`
- `ifitwala_ed/hooks.py`

Test refs:
- `ifitwala_ed/school_settings/doctype/school/test_school.py`
- `ifitwala_ed/utilities/test_organization_media.py`

| Concern | Canonical owner | Code refs | Test refs |
|---|---|---|---|
| Schema / tree identity | `School` DocType metadata owns the canonical fields, tree parent field, and role permission rows | `school_settings/doctype/school/school.json` | None specific beyond controller tests |
| Hierarchy + organization invariants | `School.validate()` owns parent-group enforcement, same-organization enforcement, and organization-change blocking for non-leaf nodes | `school_settings/doctype/school/school.py` | `school_settings/doctype/school/test_school.py` |
| Attendance defaults and thresholds | `School.validate()` owns parent-threshold inheritance for new child schools and numeric threshold validation | `school_settings/doctype/school/school.py` | None specific in current repo |
| Website publication bootstrap | `School.after_save()` and website bootstrap utilities own slug generation, publication sync, starter page creation, and SEO profile linking | `school_settings/doctype/school/school.py`, `website/bootstrap.py` | `school_settings/doctype/school/test_school.py` |
| Governed public media | `School.validate_governed_public_media()` owns logo/gallery enforcement; governed upload and media utilities own file routing and visibility resolution | `school_settings/doctype/school/school.py`, `school_settings/doctype/school/school.js`, `utilities/governed_uploads.py`, `utilities/organization_media.py` | `utilities/test_organization_media.py` |
| Desk UX guardrails | `school.js` helps users avoid invalid parent selection and routes uploads/buttons into governed flows; server remains authoritative | `school_settings/doctype/school/school.js` | None specific in current repo |
| Background work | `enqueue_replace_abbr()` defers expensive dependent renames to the `long` queue; `replace_abbr()` only renames explicit school-scoped doctypes | `school_settings/doctype/school/school.py` | `school_settings/doctype/school/test_school.py` |

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full DocType access, including import/export/share/report/email/print/select |
| `Academic Admin` | Yes | Yes | Yes | No | Can create and maintain schools, but no delete row in the DocType |
| `Academic Assistant` | Yes | Yes | No | No | Can update existing schools; cannot create or delete |
| `Marketing User` | Yes | Yes | No | No | Can update existing school records, including website-facing fields, but cannot create or delete |
| `Curriculum Coordinator` | Yes | Yes | No | No | Can update existing schools; cannot create or delete |
| `Academic Staff` | Yes | No | No | No | Read-only |
| `Admission Manager` | Yes | No | No | No | Read-only |
| `Admission Officer` | Yes | No | No | No | Read-only |
| `Instructor` | Yes | No | No | No | Read-only |
| `HR Manager` | Yes | No | No | No | Read-only |
| `HR User` | Yes | No | No | No | Read-only |
| `Accreditation Visitor` | Yes | No | No | No | Read-only |
| `Counselor` | Yes | No | No | No | Read-only |
| `Nurse` | Yes | No | No | No | Read-only |

This matrix reflects the explicit `School` DocType permission rows only. Effective runtime visibility may still be narrowed by standard Frappe permission scoping and configured `User Permission` constraints on a site.

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
  - `default_view = Tree`
- **Required fields (`reqd=1`)**:
  - `school_name`
  - `abbr`
  - `organization`
- **Notable fields**:
  - `require_health_profile_for_approval` (`Check`, default `1`)
  - `attendance_warning_threshold` / `attendance_critical_threshold`
  - `website_slug`
  - `is_published`
  - `school_logo_file`
  - `gallery_image`
- **Controller hooks**:
  - `onload`
  - `validate`
  - `on_update`
  - `after_save`
  - `after_insert`
  - `on_trash`
  - `after_rename`
- **Permission-hook status**:
  - no `School` entry in `permission_query_conditions` in `ifitwala_ed/hooks.py`
  - no `School` entry in `has_permission` in `ifitwala_ed/hooks.py`
- **Whitelisted methods**:
  - `enqueue_replace_abbr`
  - `replace_abbr`
  - `get_children`
  - `add_node`
- **Abbreviation rename contract**:
  - `enqueue_replace_abbr` runs on the `long` queue
  - `replace_abbr` only renames explicit school-scoped doctypes whose runtime names embed `School.abbr`
  - currently covered doctypes: `Academic Year`, `School Calendar`, `School Schedule`
  - it must not perform generic table scans or interpolate arbitrary table names into SQL
- **Governed media contract**:
  - direct unmanaged image values are blocked
  - school logo/gallery media must resolve through visible Organization Media rows
  - visibility is school/organization lineage aware and sibling isolation must hold
