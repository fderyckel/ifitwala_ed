<!-- ifitwala_ed/docs/website/10_public_people_contract.md -->
# Public People Contract

Status: Implemented baseline as of April 22, 2026
Code refs: `ifitwala_ed/hr/doctype/employee/employee.json`, `ifitwala_ed/hr/doctype/employee/employee.py`, `ifitwala_ed/website/public_people.py`, `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/website/providers/staff_directory.py`, `ifitwala_ed/website/renderer.py`, `ifitwala_ed/utilities/image_utils.py`, `ifitwala_ed/api/file_access.py`, `ifitwala_ed/hooks.py`
Test refs: `ifitwala_ed/website/tests/test_public_people.py`, `ifitwala_ed/website/tests/test_leadership_provider.py`, `ifitwala_ed/website/tests/test_staff_directory_provider.py`, `ifitwala_ed/website/tests/test_website_route_context.py`, `ifitwala_ed/api/test_file_access_unit.py`, `ifitwala_ed/utilities/test_school_tree.py`

## 1. Purpose

This document is the canonical contract for public employee rendering on school websites.

It exists to prevent block-by-block drift.

The contract is:

1. `Employee` remains the identity and scope source of truth.
2. Public website surfaces read directly from `Employee` and related designation metadata.
3. Public website surfaces must read through one canonical people service: `ifitwala_ed/website/public_people.py`.
4. Exact-school scope remains the default public behavior unless a specific surface contract explicitly allows bounded descendant inclusion.

For the original product rationale and top-tier CMS market anchor, see `ifitwala_ed/docs/website/10_public_people_contract_proposal.md`.

## 2. Source Of Truth

### 2.1 Employee-owned truth

`Employee` remains authoritative for:

- employee identity
- school
- organization
- designation
- website visibility anchor via `show_on_website`
- governed image anchor via `employee_image`

Public website code must not invent a second identity source for staff.

### 2.2 Current presentation ownership

Current public people rendering reads directly from `Employee` fields already present in the HR schema:

- `employee_full_name`
- `employee_preferred_name`
- `designation`
- `small_bio`
- `show_on_website`
- `employee_image`
- `show_public_profile_page`
- `public_profile_slug`
- `featured_on_website`
- `website_sort_order`

If future public website needs require additional fields, they should be added to `Employee` only after an explicit schema decision.

## 3. Publication Contract

Current runtime rule:

- an employee is eligible for public people surfaces only when:
  - `show_on_website = 1`
  - the employee belongs to the relevant school scope
- the website consumes approved governed derivatives through a guest-safe public employee-image route
- the internal `employee_profile_image` upload workflow remains private; public website display is a separate read contract, not a public upload contract

There is no separate website publication workflow for employees in the current implementation.

Implemented public-profile rule:

- profile pages are optional and employee-owned
- a public profile route exists only when `show_public_profile_page = 1`
- `public_profile_slug` is generated and validated on `Employee`
- profile routes remain school-scoped under `/schools/{school_slug}/people/{profile_slug}`

## 4. Scope Contract

### 4.1 Default scope

Public people scope is exact current school by default.

### 4.2 Allowed widening

A public surface may widen to descendants only when that surface contract explicitly allows it.

Current implemented widening:

- `leadership` block supports per-role or per-role-profile descendant inclusion
- widening remains opt-in
- widening may be bounded by `descendant_depth`

The secondary staff carousel in the leadership block remains exact-school.

## 5. Canonical Service Ownership

`ifitwala_ed/website/public_people.py` owns:

- public employee filtering
- designation role-profile enrichment
- people-card payload shape
- public image variant payload shape
- cache ownership for published public-people records

This logic must not be reimplemented separately in each website block.

Current public payload includes:

- employee id
- school
- organization
- designation
- role profile
- resolved display name
- resolved public title
- resolved public bio
- optional public email placeholder, currently `None`
- optional public phone placeholder, currently `None`
- full bio currently falls back to `Employee.small_bio`, because the current `Employee` schema does not provide a separate persisted long-form public bio field
- `featured`
- `sort_order`
- `profile_slug`
- `has_profile_page`
- `profile_url`
- initials
- responsive employee photo variants

## 6. Media And Performance Contract

Public people surfaces must use governed employee image derivatives first.

Current runtime behavior:

- people payloads use `build_public_employee_image_variants(...)`
- website cards should prefer `thumb`, `card`, and `medium`
- guest delivery goes through `open_public_employee_image(...)`, which validates publication scope and resolves a short-lived Drive preview grant for the approved derivative only
- public website people surfaces do not fall back to the original full-size employee image

Public people surfaces must not fetch full original employee images by default when a derivative exists.
If no governed derivative is available yet, website people surfaces should render the non-image fallback state instead of downloading the original.

## 7. Cache Ownership

Published public-people records are cached in `ifitwala_ed/website/public_people.py`.

Current invalidation owners:

- `Employee`
- `Designation`
- `School`

Stale public-people cache without an invalidation owner is a bug.

## 8. Surface Contract

### 8.1 Implemented now

- leadership block consumes the canonical public-people service
- staff directory block consumes the canonical public-people service
- optional public person profile pages resolve through the canonical public-people service
- public people payloads resolve from `Employee` and `Designation`

### 8.2 Not implemented yet

- organization-level people hub search

Those surfaces must reuse the same public-people service when implemented.

## 9. UX And Permission Rules

- Public staff visibility remains server-owned.
- A hidden employee must not appear on public people surfaces.
- Public staff scope cannot silently cross schools.
- Public email and phone are not exposed in the current implementation.

## 10. Related Docs

- `ifitwala_ed/docs/website/09_website_platform_phase_proposal.md`
- `ifitwala_ed/docs/website/10_public_people_contract_proposal.md`
- `ifitwala_ed/docs/website/03_website_pages_provider.md`
- `ifitwala_ed/docs/website/06_block_props_guide.md`
- `ifitwala_ed/docs/hr/emlpoyee.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`
