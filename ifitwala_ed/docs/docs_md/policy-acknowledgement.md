---
title: "Policy Acknowledgement: Append-Only Consent Evidence"
slug: policy-acknowledgement
category: Governance
doc_order: 3
summary: "Record immutable who/what/when acknowledgement evidence with strict context, role, and organization-scope validation."
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
- Document is append-only:
  - edit blocked
  - delete blocked
- `acknowledged_at` is server-stamped at insert.

## Role and Context Rules

- Applicant acknowledgements require role `Admissions Applicant` and matching applicant user linkage.
- Student acknowledgements allow:
  - users with `Student` role
  - guardian role only when guardian is linked to that student.
- Guardian acknowledgements require guardian self-context.
- Staff acknowledgements require staff role (`Academic Staff`).
- `System Manager` can bypass role validation, and override inserts are comment-audited.

## Where It Is Used Across the ERP

- [**Student Applicant**](/docs/en/student-applicant/):
  - applicant policy readiness checks
  - admissions portal policy status display
- Admissions portal endpoint `ifitwala_ed.api.admissions_portal.acknowledge_policy`:
  - creates applicant acknowledgement rows with context:
    - `acknowledged_for = Applicant`
    - `context_doctype = Student Applicant`
    - `context_name = <applicant>`
  - idempotent return when same acknowledgement already exists.
- Policy-version immutability chain:
  - existence of any acknowledgement activates lock behavior in [**Policy Version**](/docs/en/policy-version/).

## Technical Notes (IT)

- **DocType**: `Policy Acknowledgement` (`ifitwala_ed/governance/doctype/policy_acknowledgement/`)
- **Autoname**: `hash`
- **Fields**:
  - `policy_version` (Link -> Policy Version, required)
  - `acknowledged_by` (Link -> User, required)
  - `acknowledged_for` (Select, required): `Applicant`, `Student`, `Guardian`, `Staff`
  - `context_doctype` (Data, required)
  - `context_name` (Data, required)
  - `acknowledged_at` (Datetime, required, read-only)
- **Controller guards**:
  - `before_insert`: policy/version, user, context, role, uniqueness, and scope validation + timestamping
  - `before_save`: block edits
  - `before_delete`: block deletes
  - `after_insert`: System Manager override comment when role matrix is bypassed

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Doctype permission allows edit/delete; controller blocks after insert/delete |
| `Guardian` | Yes | No | Yes | No | Runtime role/context checks apply |
| `Student` | Yes | No | Yes | No | Runtime role/context checks apply |
| `Academic Staff` | Yes | No | Yes | No | Runtime role/context checks apply |
| `Admission Officer` | Yes | No | No | No | Read-only |
| `Admission Manager` | Yes | No | No | No | Read-only |
| `Admissions Applicant` | Yes | No | Yes | No | Must match applicant context linkage |

## Related Docs

- [**Institutional Policy**](/docs/en/institutional-policy/) - policy scope source
- [**Policy Version**](/docs/en/policy-version/) - legal text/version owner
- [**Student Applicant**](/docs/en/student-applicant/) - admissions readiness and acknowledgement flow
