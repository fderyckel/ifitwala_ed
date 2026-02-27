---
title: "Policy Version: Legal Text Snapshot and Activation Gate"
slug: policy-version
category: Governance
doc_order: 2
version: "1.2.8"
last_change_date: "2026-02-27"
summary: "Store immutable policy text versions, enforce amendment chains with stored diffs, and lock legal text once a version becomes active or acknowledged."
seo_title: "Policy Version: Legal Text Snapshot and Activation Gate"
seo_description: "Store immutable policy text versions, enforce amendment chains with stored diffs, and lock legal text once a version is active or acknowledged."
---

## Policy Version: Legal Text Snapshot and Activation Gate

## Before You Start (Prerequisites)

- Create and activate the parent `Institutional Policy` first.
- Finalize legal text and version label before activation because active/acknowledged text is lock-protected.
- Publish an active version before collecting acknowledgements.

`Policy Version` stores the actual legal/consent text that users acknowledge. It is the legal artifact under an `Institutional Policy`.

## What It Enforces

- Parent `institutional_policy` must exist and be active.
- `version_label` must be unique per institutional policy.
- `policy_text` must be non-empty.
- For every new version after the first, `amended_from` is required.
- `amended_from` must point to a version under the same `institutional_policy`.
- `change_summary` is required when `amended_from` is set.
- `diff_html` and `change_stats` are generated server-side from `amended_from` -> current text.
- Only one active version is allowed per institutional policy.
- `institutional_policy` is immutable after insert.
- `approved_by` (when set) must be an enabled system user with `Policy Version` write access and in policy scope:
  - school-scoped policy: approver must belong to the same school or an ancestor/parent school
  - organization-scoped policy: approver must belong to the same organization or an ancestor/parent organization
- Runtime visibility is scope-enforced server-side through parent policy scope:
  - parent policy organization must be in user organization lineage (`self + parents`)
  - if parent policy is school-scoped, policy school must be in user school lineage (`self + parents`)
- `policy_text` is editable only while Draft (`is_active = 0`) and no acknowledgements exist.
- Lifecycle is controlled by `is_active` (not DocType submit/cancel workflow).
- Once a version is activated, `policy_text` is permanently lock-protected (`text_locked = 1`) even if later deactivated.
- Once any acknowledgement exists for a version:
  - legal/core fields are lock-protected (`policy_text`, `version_label`, `institutional_policy`, amendment/diff metadata).
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
2. For amendments, open an existing version in Desk and use **Create Amendment** to prefill:
   - `institutional_policy`
   - `amended_from`
   - copied `policy_text`
   - suggested next `version_label`
3. Update `change_summary` and amended text in the new draft version.
4. Use **Share Policy** on the version form to open a communication modal that:
   - creates a draft `Org Communication`
   - defaults to one-week Morning Brief window
   - reuses policy scope (school or organization-all-schools)
   - for organization-all-schools, writes explicit audience rows for all schools in that organization
   - preselects recipients from `Institutional Policy.applies_to` with staff checked by default (editable before submit)
   - supports recipient toggles (staff/students/guardians/community)
   - can optionally trigger a staff signature campaign (off by default; staff policies only)
   - embeds a policy link that opens the SPA `staff-policy-inform` overlay (read-only, close-only) from Morning Brief and Org Communication surfaces
5. Activate one version at a time for live acknowledgement collection.
6. Collect acknowledgements through portal/flows tied to this active version.
7. When acknowledgements exist, treat core legal fields as lock-protected history.

<Callout type="warning" title="Lock after adoption">
After first activation or acknowledgement, legal text mutation is restricted by controller guards to preserve consent integrity.
</Callout>

<Callout type="tip" title="Versioning strategy">
Use a new version row for policy changes. Keep old versions for audit continuity instead of editing accepted text.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/governance/doctype/policy_version/policy_version.json`
- **Controller file**: `ifitwala_ed/governance/doctype/policy_version/policy_version.py`
- **Workflow API**: `ifitwala_ed.api.policy_communication.create_policy_amendment_communication`
- **Required fields (`reqd=1`)**:
  - `institutional_policy` (`Link` -> `Institutional Policy`)
  - `version_label` (`Data`)
  - `policy_text` (`Text Editor`)
  - `is_active` (`Check`)
- **Lifecycle hooks in controller**: `before_insert`, `before_save`, `before_delete`
- **Operational/public methods**:
  - `create_policy_amendment_communication` (named workflow action for communication + optional signature campaign launch)

- **DocType**: `Policy Version` (`ifitwala_ed/governance/doctype/policy_version/`)
- **Autoname**: `hash`
- **Fields**:
  - `institutional_policy` (Link -> Institutional Policy, required)
  - `version_label` (Data, required)
  - `amended_from` (Link -> Policy Version)
  - `change_summary` (Small Text; required when amended)
  - `policy_text` (Text Editor, required)
  - `diff_html` (Text Editor; server-generated, read-only)
  - `change_stats` (Small Text JSON; server-generated, read-only)
  - `text_locked` (Check; hidden server lock flag)
  - `effective_from` (Date)
  - `effective_to` (Date)
  - `approved_by` (Link -> User)
  - `approved_on` (Datetime)
  - `is_active` (Check, required, default `0`)
- **Controller guards**:
  - `before_insert`: policy admin check + parent/uniqueness/text validation + amendment chain validation + diff generation
  - `before_save`: draft/active text lock enforcement + acknowledgement lock + amendment/diff synchronization + approved-by write/scope validation + active-state validation
  - `before_delete`: hard block

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `Organization Admin` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `Accounts Manager` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `Admission Manager` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `Academic Admin` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |
| `HR Manager` | Yes | Yes | Yes | Yes | Doctype permission allows delete; controller blocks delete |

Runtime controller rules:
- Policy version management requires policy-admin roles (`System Manager`, `Organization Admin`, `Accounts Manager`, `Admission Manager`, `Academic Admin`, `HR Manager`).
- `approved_by` options are filtered by a server link query so only write-capable users in valid policy scope are selectable.
- `policy_text` becomes append-only once version is active or acknowledged; edits then require creating a new version.
- Amended versions are first-class artifacts with human `change_summary` and stored paragraph diff (`diff_html` + `change_stats`).
- Read/list visibility is enforced by `permission_query_conditions` + `has_permission` hooks via parent institutional policy scope.

## Related Docs

- [**Institutional Policy**](/docs/en/institutional-policy/) - policy identity and scope owner
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) - evidence tied to versions
- [**Student Applicant**](/docs/en/student-applicant/) - admissions readiness and portal acknowledgements
