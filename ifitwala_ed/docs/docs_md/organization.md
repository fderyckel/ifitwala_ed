---
title: "Organization: Legal Entity and Hierarchy Root"
slug: organization
category: Setup
doc_order: 1
version: "1.0.3"
last_change_date: "2026-02-27"
summary: "Define legal entities as a NestedSet hierarchy and anchor schools, policy scope, and website-school ownership."
seo_title: "Organization: Legal Entity and Hierarchy Root"
seo_description: "Define legal entities as a NestedSet hierarchy and anchor schools, policy scope, and website-school ownership."
---

## Organization: Legal Entity and Hierarchy Root

`Organization` is the legal entity root used across Ifitwala Ed for governance, scope, and hierarchy.

## What It Enforces

- Organization is a tree (`NestedSet`) using `parent_organization`.
- Parent organization must be a group (`is_group = 1`).
- `default_website_school`, when set, must belong to the same organization.
- `organization_logo` is the website shell organization mark (top-right utility area and organization landing brand).
- Virtual root (`All Organizations`) cannot have a parent.
- HR scope on Organization is descendant-based:
  - base org from user default `organization` (fallback `Global Defaults.default_organization`)
  - plus explicit `User Permission` grants on `Organization` and descendants.

## Where It Is Used Across the ERP

- [**Institutional Policy**](/docs/en/institutional-policy/):
  - policy scope anchor
  - nearest-ancestor policy resolution
- [**Student Applicant**](/docs/en/student-applicant/):
  - immutable admissions anchor with school
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/):
  - context scope validation resolves organization alignment
- `Org Communication`:
  - when a staff user has no default school, issuing-school selection is constrained to schools under authorized organization descendants (including explicit organization user-permission grants)

## Technical Notes (IT)

- **DocType**: `Organization` (`ifitwala_ed/setup/doctype/organization/`)
- **Autoname**: `field:organization_name`
- **Tree config**:
  - `is_tree = 1`
  - `nsm_parent_field = parent_organization`
- **Key required fields (`reqd=1`)**:
  - `organization_name` (Data)
  - `abbr` (Data, unique)
- **Controller class**: `Organization(NestedSet)`
- **Whitelisted methods**:
  - `get_children`
  - `get_parents`
  - `add_node`

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full access |
| `HR Manager` | Yes | Yes | Yes | No | No delete permission in doctype |
| `HR User` | Yes | No | No | No | Descendant-scoped read access (self + children) |
| `Accounts Manager` | Yes | Yes | Yes | Yes | Full access |
| `Academic Admin` | Yes | Yes | No | No | Read/write existing |
| `Employee` | Yes | No | No | No | Read-only |
| `Academic Assistant` | Yes | No | No | No | Read-only |

## Related Docs

- [**Institutional Policy**](/docs/en/institutional-policy/) - organization-scoped policy identity
- [**Policy Version**](/docs/en/policy-version/) - active legal versions under policy identities
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) - context evidence constrained by organization scope
- [**Student Applicant**](/docs/en/student-applicant/) - admissions anchor and readiness flow
