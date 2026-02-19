---
title: "Institutional Policy: Policy Identity and Scope Anchor"
slug: institutional-policy
category: Governance
doc_order: 1
summary: "Define policy identity, organization/school scope, and target audience so active policy versions can be resolved and acknowledged correctly."
seo_title: "Institutional Policy: Policy Identity and Scope Anchor"
seo_description: "Define policy identity, organization/school scope, and target audience so active policy versions can be resolved and acknowledged correctly."
---

## Institutional Policy: Policy Identity and Scope Anchor

## Before You Start (Prerequisites)

- Create the target `Organization` first (policy scope anchor).
- Decide `policy_key`, category, and applies-to audience model before insertion.
- Create policy identity records before creating any `Policy Version` rows.

`Institutional Policy` defines what a policy is, where it applies, and who it applies to. It is the semantic root for all policy versions and acknowledgements.

## What It Enforces

- Policy identity is stable through `policy_key` + `organization`.
- `policy_key`, `organization`, and `school` are immutable after insert.
- `policy_category` must be one of the locked categories in governance utilities.
- `school` must be inside policy organization scope (organization descendants allowed).
- Deletion is blocked; policy should be deactivated instead (`is_active = 0`).

## Where It Is Used Across the ERP

- [**Policy Version**](/docs/en/policy-version/): parent link (`institutional_policy`) requires active policy.
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/): scope checks resolve policy organization from parent chain.
- [**Student Applicant**](/docs/en/student-applicant/):
  - readiness policy requirements (`has_required_policies`)
  - admissions portal policy list (`get_applicant_policies`)
- Media consent publish gate:
  - `policy_key = media_consent`
  - read by `has_applicant_policy_acknowledgement` during applicant promotion image publish logic.
- Nearest-only organization override:
  - policy candidates are filtered using `select_nearest_policy_rows_by_key` against Organization ancestor chain.

## Lifecycle and Linked Documents

1. Create policy identity (`policy_key`) and audience/scope under the correct organization.
2. Create one or more `Policy Version` rows as legal text snapshots under this policy.
3. Activate/deactivate policy identity based on institutional policy lifecycle.
4. Collect acknowledgements through `Policy Acknowledgement` using active versions only.

<Callout type="warning" title="Scope integrity">
Policy scope is organization-sensitive. Wrong scope setup causes downstream acknowledgement and readiness mismatches.
</Callout>

<Callout type="tip" title="Lifecycle approach">
Treat this record as long-lived identity. Version the legal text in `Policy Version` instead of replacing policy roots.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`
- **Controller file**: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.py`
- **Required fields (`reqd=1`)**:
  - `policy_key` (`Data`)
  - `policy_title` (`Data`)
  - `policy_category` (`Select`)
  - `applies_to` (`MultiSelect`)
  - `organization` (`Link` -> `Organization`)
  - `is_active` (`Check`)
- **Lifecycle hooks in controller**: `before_insert`, `before_save`, `before_delete`
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Institutional Policy` (`ifitwala_ed/governance/doctype/institutional_policy/`)
- **Autoname**: `hash`
- **Fields**:
  - `policy_key` (Data, required)
  - `policy_title` (Data, required)
  - `policy_category` (Select, required)
  - `applies_to` (MultiSelect, required): `Applicant`, `Student`, `Guardian`, `Staff`
  - `organization` (Link -> Organization, required)
  - `school` (Link -> School, optional)
  - `description` (Small Text)
  - `is_active` (Check, required, default `1`)
- **Controller guards**:
  - `before_insert`: admin permission, category validation, unique policy key by organization, school scope validation
  - `before_save`: admin permission + immutability enforcement
  - `before_delete`: hard block
- **Scope helper**:
  - `is_school_within_policy_organization_scope` validates school organization ancestry under the policy organization.

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `Organization Admin` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |

Runtime controller rule:
- Policy management is restricted to policy admins (`System Manager` or `Organization Admin`), regardless of Desk form visibility.

## Related Docs

- [**Policy Version**](/docs/en/policy-version/) - legal text versions under this policy identity
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) - evidence rows tied to active versions
- [**Student Applicant**](/docs/en/student-applicant/) - admissions readiness and portal policy flows
