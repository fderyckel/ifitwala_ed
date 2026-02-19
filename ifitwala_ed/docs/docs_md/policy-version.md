---
title: "Policy Version: Legal Text Snapshot and Activation Gate"
slug: policy-version
category: Governance
doc_order: 2
summary: "Store immutable policy text versions, enforce one active version per policy, and lock legal text once acknowledgements exist."
seo_title: "Policy Version: Legal Text Snapshot and Activation Gate"
seo_description: "Store immutable policy text versions, enforce one active version per policy, and lock legal text once acknowledgements exist."
---

## Policy Version: Legal Text Snapshot and Activation Gate

## Before You Start (Prerequisites)

- Create and activate the parent `Institutional Policy` first.
- Finalize legal text and version label before activation because acknowledged content is lock-protected.
- Publish an active version before collecting acknowledgements.

`Policy Version` stores the actual legal/consent text that users acknowledge. It is the legal artifact under an `Institutional Policy`.

## What It Enforces

- Parent `institutional_policy` must exist and be active.
- `version_label` must be unique per institutional policy.
- `policy_text` must be non-empty.
- Only one active version is allowed per institutional policy.
- `institutional_policy` is immutable after insert.
- Once any acknowledgement exists for a version:
  - `policy_text`, `version_label`, and `institutional_policy` are locked.
  - only `System Manager` with explicit `flags.override_reason` can override, and override is comment-audited.
- Deletion is blocked.

## Where It Is Used Across the ERP

- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/): `policy_version` must be active for acknowledgements.
- [**Student Applicant**](/docs/en/student-applicant/):
  - admissions policy requirements use active versions only
  - portal policy payload includes version text (`content_html`) from active versions
- Admissions portal endpoints:
  - `get_applicant_policies`
  - `acknowledge_policy`

## Lifecycle and Linked Documents

1. Draft legal text under the parent `Institutional Policy`.
2. Activate one version at a time for live acknowledgement collection.
3. Collect acknowledgements through portal/flows tied to this active version.
4. When acknowledgements exist, treat core legal fields as lock-protected history.

<Callout type="warning" title="Lock after adoption">
After first acknowledgement, legal text mutation is restricted by controller guards to preserve consent integrity.
</Callout>

<Callout type="tip" title="Versioning strategy">
Use a new version row for policy changes. Keep old versions for audit continuity instead of editing accepted text.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/governance/doctype/policy_version/policy_version.json`
- **Controller file**: `ifitwala_ed/governance/doctype/policy_version/policy_version.py`
- **Required fields (`reqd=1`)**:
  - `institutional_policy` (`Link` -> `Institutional Policy`)
  - `version_label` (`Data`)
  - `policy_text` (`Text Editor`)
  - `is_active` (`Check`)
- **Lifecycle hooks in controller**: `before_insert`, `before_save`, `before_delete`
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Policy Version` (`ifitwala_ed/governance/doctype/policy_version/`)
- **Autoname**: `hash`
- **Fields**:
  - `institutional_policy` (Link -> Institutional Policy, required)
  - `version_label` (Data, required)
  - `policy_text` (Text Editor, required)
  - `effective_from` (Date)
  - `effective_to` (Date)
  - `approved_by` (Link -> User)
  - `approved_on` (Datetime)
  - `is_active` (Check, required, default `0`)
- **Controller guards**:
  - `before_insert`: policy admin check + parent/uniqueness/text validation
  - `before_save`: immutability + acknowledgement lock + active-state validation
  - `before_delete`: hard block

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `Organization Admin` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |

Runtime controller rules:
- Policy version management requires policy-admin roles.
- Acknowledgement lock makes legal text effectively append-only after first acknowledgement, except explicit System Manager override flow.

## Related Docs

- [**Institutional Policy**](/docs/en/institutional-policy/) - policy identity and scope owner
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) - evidence tied to versions
- [**Student Applicant**](/docs/en/student-applicant/) - admissions readiness and portal acknowledgements
