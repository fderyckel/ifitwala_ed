---
title: "Institutional Policy: Policy Identity and Scope Anchor"
slug: institutional-policy
category: Governance
doc_order: 1
version: "1.5.0"
last_change_date: "2026-03-25"
summary: "Define policy identity, organization/school scope, target audience, and lifecycle rules so admissions, guardian, staff, and governance workflows resolve the correct active policy versions and acknowledgements."
seo_title: "Institutional Policy: Policy Identity and Scope Anchor"
seo_description: "Define policy identity, organization/school scope, and target audience so admissions, guardian, staff, and governance workflows resolve the correct active policy versions and acknowledgements."
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
4. Internal staff policy payloads:
   - staff policy library and analytics payloads return `policy_key` for active staff-scope policies.
   - policy inform payloads keep policy identity attached to the active version shown in the overlay.
5. Code-level constants for specific product behavior (example): `ifitwala_ed/governance/policy_utils.py` -> `MEDIA_CONSENT_POLICY_KEY`.

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
- `applies_to` is a required multi-audience field and must include one or more of:
  - `Applicant`
  - `Student`
  - `Guardian`
  - `Staff`
- `applies_to` is stored as a Frappe-native `Table MultiSelect` backed by `Institutional Policy Audience` child rows linked to `Policy Audience`.
- `applies_to` rows are normalized server-side before save. Runtime checks use audience inclusion, not exact string equality.
- `admissions_acknowledgement_mode` controls how admissions portal acknowledgement is written:
  - `Child Acknowledgement`
  - `Family Acknowledgement`
  - `Child Optional Consent`
- `admissions_acknowledgement_mode` affects admissions-stage acknowledgement routing only; guardian and staff self-service use their own context-specific acknowledgement paths.
- `school` must be inside policy organization scope (organization descendants allowed).
- Deletion is blocked; policy should be deactivated instead (`is_active = 0`).
- Policy admin management scope is descendant-owned:
  - policy admins may create, read, and edit policies for their base organization and descendant organizations
  - management scope for policy admins is broader than end-user applicability visibility
- Runtime visibility is scope-enforced server-side:
  - `organization` must be in user organization lineage (`self + parents`)
  - if policy is school-scoped, `school` must be in user school lineage (`self + parents`)

## Audience and Product Reach

`Institutional Policy` is the scope and identity root for policy behavior across the ERP, not just admissions.

- `Applicant` policies drive admissions readiness, portal display, and applicant-stage acknowledgements.
- `Guardian` policies drive guardian self-service visibility and acknowledgement for linked children in scope.
- `Staff` policies drive internal policy communication, staff policy library visibility, signature campaigns, focus actions, acknowledgements, and analytics.
- `Student` is a valid canonical audience in the data model and acknowledgement model. The current workspace does not expose a dedicated student policy library surface in this note set, so any future student-facing delivery should be documented under its owning product surface.

## Audience Scope vs Signer Authority

- `applies_to` answers which audiences a policy targets.
- `applies_to` does not grant signer authority by itself.
- Guardian signer authority is owned by relationship rows:
  - admissions-stage: `Student Applicant Guardian.can_consent`
  - enrolled-student stage: `Student Guardian.can_consent`
- Admissions-stage acknowledgements still use `admissions_acknowledgement_mode` to choose applicant or guardian context.
- Staff acknowledgements are always self-context on `Employee`; policy audience does not let one staff member sign for another.
- Current guardian portal policy visibility uses both rules together:
  - the policy audience must include `Guardian`
  - the guardian must have signer authority for at least one linked child in scope

## School Scope Resolution

- `school` blank (`NULL`/empty) means the policy is org-wide for the selected `organization` scope.
- When `school` is set to a parent school, the policy applies to that school and all descendant schools.
- School matching uses the active business context school lineage (`self -> parent -> ...`) plus org-wide blank fallback:
  - applicant school for admissions flows
  - linked child school for guardian flows
  - employee school for staff flows
- Final policy selection remains nearest-only by `policy_key` on the [**Organization**](/docs/en/organization/) ancestor chain.

## Where It Is Used Across the ERP

- Governance and authoring:
  - [**Policy Version**](/docs/en/policy-version/) requires an active parent policy identity.
  - the Institutional Policy Desk form is the long-lived root where policy identity, scope, and audience are maintained before creating versions.
  - [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) resolves parent organization scope from the policy chain.
- Admissions and applicant readiness:
  - [**Student Applicant**](/docs/en/student-applicant/) readiness uses active applicant-audience policies (`has_required_policies`).
  - admissions portal policy lists (`get_applicant_policies`) resolve active versions through organization/school scope and nearest `policy_key`.
  - `admissions_acknowledgement_mode` decides whether applicant-stage acknowledgement lands on `Student Applicant` or `Guardian` context.
- Guardian self-service:
  - guardian policy overview and acknowledgement resolve guardian-audience active policies across linked child scope.
  - guardian visibility still requires signer-authorized child relationships; audience match alone is not enough.
- Internal staff workflows:
  - staff policy library (`get_staff_policy_library`, `/staff/policies`) shows active staff-audience policy versions in employee scope.
  - policy inform payloads and overlays expose current policy text, change summary, diff stats, and version history for in-scope staff readers.
  - policy signature campaigns (`get_staff_policy_campaign_options`, `launch_staff_policy_campaign`) use policy scope to target employees by organization, school, and employee group.
  - focus acknowledgement actions write immutable staff acknowledgements on `Employee` context and close related policy ToDos.
  - policy signature analytics aggregate completion by organization, school, and employee group for active staff policies.
- Internal communication defaults:
  - policy communication/share flows derive default recipients from `Institutional Policy.applies_to`.
  - the same policy scope (`organization`, optional `school`) is reused to build communication audiences before optional staff-signature campaign launch.
- Downstream operational gates:
  - `policy_key = media_consent` is used by applicant/student image publish gating through acknowledgement checks.
  - nearest-only policy override remains keyed by `policy_key` across [**Organization**](/docs/en/organization/) ancestor scope via `select_nearest_policy_rows_by_key`.

## Lifecycle and Linked Documents

1. Create policy identity (`policy_key`) and audience/scope under the correct organization.
2. Use **Create Policy Version** on the Institutional Policy form to open a prefilled draft:
   - first version: prefilled with `institutional_policy` + suggested `version_label` (`v1`)
   - subsequent versions: prefilled as amendment from current active/latest version (`based_on_version`, copied `policy_text`, suggested bumped `version_label`)
3. Save and finalize the [**Policy Version**](/docs/en/policy-version/) legal text snapshot.
4. Activate the policy version and keep the identity active while it should remain selectable by scope resolution.
5. Optionally share or distribute the active version through internal communication flows; recipient defaults come from `applies_to`, while staff-signature campaigns remain staff-only.
6. Collect acknowledgements through [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) using active versions only:
   - applicant-stage flows use admissions context rules
   - guardian flows use guardian self-context
   - staff flows use employee self-context
7. Use acknowledgement evidence downstream for readiness, pending signature state, analytics, and publish/consent gates.
8. Deactivate the policy identity when it should stop participating in future resolution. Do not delete historical roots.

<Callout type="warning" title="Scope integrity">
Policy scope is organization-sensitive. Wrong scope setup causes downstream acknowledgement and readiness mismatches.
</Callout>

<Callout type="tip" title="Lifecycle approach">
Treat this record as long-lived identity. Version the legal text in [**Policy Version**](/docs/en/policy-version/) instead of replacing policy roots.
</Callout>

## Related Docs

- [**Organization**](/docs/en/organization/) - ancestor scope and nearest-match resolution root
- [**School**](/docs/en/school/) - school lineage and descendant applicability
- [**Policy Version**](/docs/en/policy-version/) - legal text versions, communication/share flow, and activation rules
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) - immutable acknowledgement evidence across applicant, guardian, student, and staff contexts
- [**Student Applicant**](/docs/en/student-applicant/) - admissions readiness, portal policy display, and applicant-stage acknowledgement behavior

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`
- **Controller file**: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.py`
- **Required fields (`reqd=1`)**:
  - `policy_key` (`Data`)
  - `policy_title` (`Data`)
  - `policy_category` (`Select`)
  - `applies_to` (`Table MultiSelect` -> `Institutional Policy Audience`)
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
  - `applies_to` (Table MultiSelect, required): child rows of `Institutional Policy Audience`
  - `policy_audience` (Link -> `Policy Audience`, required on each child row): `Applicant`, `Student`, `Guardian`, `Staff`
  - `admissions_acknowledgement_mode` (Select, default `Child Acknowledgement`): `Child Acknowledgement`, `Family Acknowledgement`, `Child Optional Consent`
  - `organization` (Link -> [**Organization**](/docs/en/organization/), required)
  - `school` (Link -> School, optional)
  - `description` (Small Text)
  - `is_active` (Check, required, default `1`)
- **Controller guards**:
  - `before_insert`: admin permission, category validation, applies-to normalization/validation, unique policy key by organization, school scope validation
  - `before_save`: admin permission, applies-to normalization/validation, school scope validation, immutability enforcement (`school` one-time set if previously blank)
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
- Policy admins may manage policies rooted in their organization or descendant organizations; this is the authoring scope used for create/write and management list visibility.
- Read/list visibility for non-admin readers is enforced by `permission_query_conditions` + `has_permission` hooks, not client filtering.
