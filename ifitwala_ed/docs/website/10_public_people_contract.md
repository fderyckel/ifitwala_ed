<!-- ifitwala_ed/docs/website/10_public_people_contract.md -->
# Public People Contract

Status: Partial implementation in place as of April 5, 2026
Code refs: `ifitwala_ed/hr/doctype/employee/employee.json`, `ifitwala_ed/school_site/doctype/employee_website_profile/employee_website_profile.py`, `ifitwala_ed/school_site/doctype/employee_website_profile/employee_website_profile.json`, `ifitwala_ed/website/public_people.py`, `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/utilities/image_utils.py`, `ifitwala_ed/hooks.py`
Test refs: `ifitwala_ed/school_site/doctype/employee_website_profile/test_employee_website_profile.py`, `ifitwala_ed/website/tests/test_public_people.py`, `ifitwala_ed/website/tests/test_leadership_provider.py`, `ifitwala_ed/utilities/test_school_tree.py`

## 1. Purpose

This document is the canonical contract for public employee rendering on school websites.

It exists to prevent block-by-block drift.

The contract is:

1. `Employee` remains the identity and scope source of truth.
2. Website-owned presentation overrides are allowed through `Employee Website Profile`.
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

### 2.2 Website-owned presentation layer

`Employee Website Profile` is the website-owned presentation layer.

Current implemented fields:

- `display_name_override`
- `public_title_override`
- `public_bio`
- `public_email`
- `public_phone`
- `sort_order`

This profile is presentation-only.
It must not replace `Employee` ownership of school, organization, designation, or website visibility.

## 3. Publication Contract

`Employee Website Profile` uses the same workflow vocabulary as other website-owned profiles:

- `Draft`
- `In Review`
- `Approved`
- `Published`

Current runtime rule:

- profile `status` becomes `Published` only when:
  - workflow state is `Published`
  - the linked `Employee` has `show_on_website = 1`
  - the profile school matches the employee school

If the employee becomes hidden or moves schools, the public profile status falls back to `Draft`.

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
- published override merge behavior
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
- optional public email
- optional public phone
- sort order
- initials
- responsive employee photo variants

## 6. Media And Performance Contract

Public people surfaces must use governed employee image derivatives first.

Current runtime behavior:

- people payloads use `build_employee_image_variants(...)`
- website cards should prefer `thumb`, `card`, and `medium`
- original image is only a fallback

Public people surfaces must not fetch full original employee images by default when a derivative exists.

## 7. Cache Ownership

Published public-people records are cached in `ifitwala_ed/website/public_people.py`.

Current invalidation owners:

- `Employee`
- `Designation`
- `School`
- `Employee Website Profile`

Stale public-people cache without an invalidation owner is a bug.

## 8. Surface Contract

### 8.1 Implemented now

- leadership block consumes the canonical public-people service
- website-owned staff presentation overrides are live for leadership surfaces once published

### 8.2 Not implemented yet

- public faculty/staff directory route
- public employee profile pages
- organization-level people hub search

Those surfaces must reuse the same public-people service when implemented.

## 9. UX And Permission Rules

- Public staff visibility remains server-owned.
- A hidden employee must not become public through a website-profile override alone.
- A profile cannot silently cross schools.
- Public email and phone remain opt-in override fields; they do not fall back automatically to private employee contact data.

## 10. Related Docs

- `ifitwala_ed/docs/website/09_website_platform_phase_proposal.md`
- `ifitwala_ed/docs/website/10_public_people_contract_proposal.md`
- `ifitwala_ed/docs/website/03_website_pages_provider.md`
- `ifitwala_ed/docs/website/06_block_props_guide.md`
- `ifitwala_ed/docs/hr/emlpoyee.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`
