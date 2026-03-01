---
title: "Policy Acknowledgement: Append-Only Consent Evidence"
slug: policy-acknowledgement
category: Governance
doc_order: 3
version: "1.5.0"
last_change_date: "2026-03-01"
summary: "Record immutable who/what/when acknowledgement evidence with strict context, role, organization-scope validation, and staff policy-signature workflows that present amendment diffs first."
seo_title: "Policy Acknowledgement: Append-Only Consent Evidence"
seo_description: "Record immutable who/what/when acknowledgement evidence with strict context, role, and organization-scope validation."
---

## Policy Acknowledgement: Append-Only Consent Evidence

## Before You Start (Prerequisites)

- Create and activate the target `Policy Version` first.
- Ensure the context record exists first (`Student Applicant`, `Student`, `Guardian`, or `Employee`).
- Ensure the acknowledging user is correctly linked to that context with required role visibility.

`Policy Acknowledgement` is the evidence row proving a user acknowledged an active policy version for a specific business context.

## What It Enforces

- `policy_version` is required and must be active.
- `acknowledged_by` must equal the current session user.
- Context must be explicit (`context_doctype`, `context_name`) and must exist.
- `acknowledged_for` must match allowed context doctypes:
  - `Applicant` -> `Student Applicant`
  - `Student` -> `Student`
  - `Guardian` -> `Guardian`
  - `Staff` -> `Employee`
- Policy organization scope must apply to context organization.
- Duplicate acknowledgements for same tuple are blocked:
  - `policy_version`, `acknowledged_by`, `context_doctype`, `context_name`
- Document is append-only and ledger-submitted:
  - auto-submitted on insert (`docstatus = 1`)
  - edit blocked
  - cancel blocked
  - delete blocked
- `acknowledged_at` is server-stamped at insert.

## Role and Context Rules

- Applicant acknowledgements require role `Admissions Applicant` and matching applicant user linkage.
- Student acknowledgements allow:
  - users with `Student` role
  - guardian role only when guardian is linked to that student.
- Guardian acknowledgements require guardian self-context.
- Staff acknowledgements require staff role (`Academic Staff` or `Employee`).
- `System Manager` can bypass role validation, and override inserts are comment-audited.

## Staff Signature Campaign Workflow (Internal Tools)

The internal workflow for staff policy signatures is campaign-based and scope-driven:

1. Select a `Policy Version` plus target scope:
   - `organization` (required)
   - `school` (optional)
   - `employee_group` (optional)
2. Preview scope impact before launch:
   - target employees
   - eligible users
   - already signed
   - already open
   - to create
3. Launch creates `ToDo` rows linked to `Policy Version` for staff not already signed and not already open.
4. Staff complete acknowledgement from Focus action `policy_acknowledgement.staff.sign` using formal e-sign controls:
   - type full signer name exactly as employee record
   - confirm electronic-signature attestation
5. On acknowledgement:
   - one immutable `Policy Acknowledgement` row is inserted (`acknowledged_for=Staff`, `context_doctype=Employee`)
   - open policy ToDos for that staff/policy version are closed
   - Focus invalidation is published.

### New Policy vs Updated Policy (Best-Practice Trigger Rules)

- New policy (`Policy Version` first active release):
  - launch campaign for full intended scope.
- Updated policy (new active `Policy Version` replacing prior version):
  - launch a fresh campaign for the new version; do not reuse prior acknowledgements.
  - prior acknowledgements remain immutable evidence for the old version.
  - staff review flow defaults to amendment changes (`change_summary` + `diff_html`) before full text.
- Scope changes (organization/school/group changes):
  - apply to future campaign launches only; existing acknowledgements are not recomputed.

### Electronic Signature Controls (Staff)

- Signature is server-validated, not UI-only:
  - typed signature name must match employee identity context
  - legal attestation confirmation is required
- One-click acknowledgement without attestation is rejected.

### Electronic Signature Controls (Applicant Portal)

- Admissions policy acknowledgement requires explicit e-sign payload:
  - `typed_signature_name`
  - `attestation_confirmed`
- Signature is server-validated against the applicant identity context (expected signer name shown in portal UI).
- One-click acknowledgement without typed signature + attestation is rejected.

## Where It Is Used Across the ERP

- [**Student Applicant**](/docs/en/student-applicant/):
  - applicant policy readiness checks
  - admissions portal policy status display
- Admissions portal endpoint `ifitwala_ed.api.admissions_portal.acknowledge_policy`:
  - creates applicant acknowledgement rows with context:
    - `acknowledged_for = Applicant`
    - `context_doctype = Student Applicant`
    - `context_name = <applicant>`
  - requires applicant electronic-signature fields:
    - `typed_signature_name` (must match expected applicant signer name)
    - `attestation_confirmed` (required true/1)
  - idempotent return when same acknowledgement already exists.
- Policy-version immutability chain:
  - existence of any acknowledgement activates lock behavior in [**Policy Version**](/docs/en/policy-version/).
- Internal staff policy workflow APIs:
  - `ifitwala_ed.api.policy_signature.get_staff_policy_campaign_options`
  - `ifitwala_ed.api.policy_signature.launch_staff_policy_campaign`
  - `ifitwala_ed.api.policy_signature.get_staff_policy_signature_dashboard`
  - `ifitwala_ed.api.focus.acknowledge_staff_policy`

## Lifecycle and Linked Documents

1. Resolve the active policy version for the user and business context.
2. Insert acknowledgement for the current session user against explicit context fields.
3. Prevent duplicates for the same version/user/context tuple (controller validation + database unique index).
4. Keep the record append-only as durable consent evidence.

<Callout type="warning" title="Identity rule">
`acknowledged_by` must match the current user session; proxy acknowledgements are blocked except governed override paths.
</Callout>

<Callout type="info" title="Evidence model">
Acknowledgements are immutable records. Corrections should be handled by new policy versions or governance-approved flows.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.json`
- **Controller file**: `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`
- **Required fields (`reqd=1`)**:
  - `policy_version` (`Link` -> `Policy Version`)
  - `acknowledged_by` (`Link` -> `User`)
  - `acknowledged_for` (`Select`)
  - `context_doctype` (`Data`)
  - `context_name` (`Data`)
  - `acknowledged_at` (`Datetime`)
- **Lifecycle hooks in controller**: `before_insert`, `before_save`, `before_submit`, `before_update_after_submit`, `before_cancel`, `before_delete`, `after_insert`, `on_submit`
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Policy Acknowledgement` (`ifitwala_ed/governance/doctype/policy_acknowledgement/`)
- **Autoname**: `hash`
- **Is Submittable**: `Yes` (auto-submit on insert)
- **Fields**:
  - `policy_version` (Link -> Policy Version, required)
  - `acknowledged_by` (Link -> User, required)
  - `acknowledged_for` (Select, required): `Applicant`, `Student`, `Guardian`, `Staff`
  - `context_doctype` (Data, required)
  - `context_name` (Data, required)
  - `acknowledged_at` (Datetime, required, read-only)
- **Controller guards**:
  - `before_insert`: policy/version, user, context, role, uniqueness, and scope validation + timestamping
  - `before_save`: block edits except the draft->submitted transition
  - `before_submit`: enforce draft->submitted transition only
  - `before_update_after_submit`: block all post-submit edits
  - `before_cancel`: block cancel
  - `before_delete`: block deletes
  - `after_insert`: auto-submit to submitted evidence state
  - `on_submit`: System Manager override comment when role matrix is bypassed

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | No | Controller still blocks edit/cancel/delete lifecycle transitions |
| `Guardian` | Yes | No | Yes | No | Runtime role/context checks apply |
| `Student` | Yes | No | Yes | No | Runtime role/context checks apply |
| `Academic Staff` | Yes | No | Yes | No | Runtime visibility is self staff context only |
| `Admission Officer` | Yes | No | No | No | Read-only |
| `Admission Manager` | Yes | No | No | No | Read-only |
| `Admissions Applicant` | Yes | No | Yes | No | Must match applicant context linkage |

Runtime visibility is enforced server-side via `permission_query_conditions` + `has_permission` hooks by role and context (organization/school scope, applicant linkage, guardian linkage, student self, staff self).

## Related Docs

- [**Institutional Policy**](/docs/en/institutional-policy/) - policy scope source
- [**Policy Version**](/docs/en/policy-version/) - legal text/version owner
- [**Student Applicant**](/docs/en/student-applicant/) - admissions readiness and acknowledgement flow
