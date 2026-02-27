---
title: "Institutional Policy: Policy Identity and Scope Anchor"
slug: institutional-policy
category: Governance
doc_order: 1
version: "1.0.1"
last_change_date: "2026-02-27"
summary: "Define policy identity, organization/school scope, and target audience so active policy versions can be resolved and acknowledged correctly."
seo_title: "Institutional Policy: Policy Identity and Scope Anchor"
seo_description: "Define policy identity, organization/school scope, and target audience so active policy versions can be resolved and acknowledged correctly."
---

## Institutional Policy: Policy Identity and Scope Anchor

## Before You Start (Prerequisites)

- Create the target [**Organization**](/docs/en/organization/) first (policy scope anchor).
- Decide `policy_key`, category, and applies-to audience model before insertion.
- Create [**Institutional Policy**](/docs/en/institutional-policy/) identity records before creating any [**Policy Version**](/docs/en/policy-version/) rows.

### What `policy_key` Is

`policy_key` is the stable machine identifier for a policy identity.

- It is not display text; `policy_title` is the human-facing label.
- It is used by server logic to resolve policy requirements by organization scope (nearest policy per key).
- It is immutable after insert.
- It must be unique within the same `organization`.

Example used in current code: `media_consent` (image publish consent flow).

### Where to Find Existing `policy_key` Values

There is no separate "policy key catalog" DocType in the current model. Existing keys are found in policy records:

1. Desk list view: [**Institutional Policy**](/docs/en/institutional-policy/) -> `policy_key` column.
2. Desk form: [**Institutional Policy**](/docs/en/institutional-policy/) -> `policy_key` field on each record.
3. Admissions readiness/policy payloads:
   - [**Student Applicant**](/docs/en/student-applicant/) readiness (`has_required_policies`) returns missing/required labels from policy key/name chain.
   - Admissions portal policy list (`get_applicant_policies`) labels policies by `policy_key` first, then title/name fallback.
4. Code-level constants for specific product behavior (example): `ifitwala_ed/governance/policy_utils.py` -> `MEDIA_CONSENT_POLICY_KEY`.

### Related Policy Doctypes

- [**Policy Version**](/docs/en/policy-version/) - legal text snapshots under an institutional policy
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) - append-only acknowledgement evidence rows

`Institutional Policy` defines what a policy is, where it applies, and who it applies to. It is the semantic root for all policy versions and acknowledgements.

## What It Enforces

- Policy identity is stable through `policy_key` + `organization`.
- `policy_key` and `organization` are immutable after insert.
- `school` is optional; blank means organization-wide scope.
- `school` can be set one time if initially blank, then becomes immutable.
- `policy_category` must be one of the locked categories in governance utilities.
- `school` must be inside policy organization scope (organization descendants allowed).
- Deletion is blocked; policy should be deactivated instead (`is_active = 0`).

## School Scope Resolution

- `school` blank (`NULL`/empty) means the policy is org-wide for the selected `organization` scope.
- When `school` is set to a parent school, the policy applies to that school and all descendant schools.
- School matching uses applicant school lineage (`self -> parent -> ...`) plus org-wide blank fallback.
- Final policy selection remains nearest-only by `policy_key` on the [**Organization**](/docs/en/organization/) ancestor chain.

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
  - policy candidates are filtered using `select_nearest_policy_rows_by_key` against [**Organization**](/docs/en/organization/) ancestor chain.

## Lifecycle and Linked Documents

1. Create policy identity (`policy_key`) and audience/scope under the correct organization.
2. Use **Create Policy Version** on the Institutional Policy form to open a prefilled draft:
   - first version: prefilled with `institutional_policy` + suggested `version_label` (`v1`)
   - subsequent versions: prefilled as amendment from current active/latest version (`amended_from`, copied `policy_text`, suggested bumped `version_label`)
3. Save and finalize the [**Policy Version**](/docs/en/policy-version/) legal text snapshot.
4. Activate/deactivate policy identity based on institutional policy lifecycle.
5. Collect acknowledgements through [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) using active versions only.

<Callout type="warning" title="Scope integrity">
Policy scope is organization-sensitive. Wrong scope setup causes downstream acknowledgement and readiness mismatches.
</Callout>

<Callout type="tip" title="Lifecycle approach">
Treat this record as long-lived identity. Version the legal text in [**Policy Version**](/docs/en/policy-version/) instead of replacing policy roots.
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
  - `organization` (`Link` -> [**Organization**](/docs/en/organization/))
  - `is_active` (`Check`)
- **Lifecycle hooks in controller**: `before_insert`, `before_save`, `before_delete`
- **Desk action**:
  - `Create Policy Version` button creates a prefilled `Policy Version` draft from policy context.

- **DocType**: `Institutional Policy` (`ifitwala_ed/governance/doctype/institutional_policy/`)
- **Autoname**: `hash`
- **Fields**:
  - `policy_key` (Data, required)
  - `policy_title` (Data, required)
  - `policy_category` (Select, required)
  - `applies_to` (MultiSelect, required): `Applicant`, `Student`, `Guardian`, `Staff`
  - `organization` (Link -> [**Organization**](/docs/en/organization/), required)
  - `school` (Link -> School, optional)
  - `description` (Small Text)
  - `is_active` (Check, required, default `1`)
- **Controller guards**:
  - `before_insert`: admin permission, category validation, unique policy key by organization, school scope validation
  - `before_save`: admin permission, school scope validation, immutability enforcement (`school` one-time set if previously blank)
  - `before_delete`: hard block
- **Scope helper**:
  - `is_school_within_policy_organization_scope` validates school organization ancestry under the policy organization.

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `Organization Admin` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `Admission Manager` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `Academic Admin` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `HR Manager` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |

Runtime controller rule:
- Policy management is restricted to policy admins (`System Manager`, `Organization Admin`, `Accounts Manager`, `Admission Manager`, `Academic Admin`, `HR Manager`), regardless of Desk form visibility.
- Controller role pass is necessary but not sufficient: user must also have DocType create/write permission for `Institutional Policy`.

## Related Docs

- [**Policy Version**](/docs/en/policy-version/) - legal text versions under this policy identity
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) - evidence rows tied to active versions
- [**Student Applicant**](/docs/en/student-applicant/) - admissions readiness and portal policy flows
