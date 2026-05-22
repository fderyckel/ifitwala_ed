# Relationship Scope And Visibility Contract

Status: Planned target contract; no Relationship CRM ownership or permission hooks are implemented yet.
Code refs:
- Related current scope helpers: `ifitwala_ed/governance/policy_scope_utils.py`, `ifitwala_ed/school_settings/school_settings_utils.py`, `ifitwala_ed/utilities/school_tree.py`, `ifitwala_ed/utilities/tree_utils.py`
- Related current contact governance: `ifitwala_ed/contacts/contact_privacy.py`, `ifitwala_ed/contacts/contact_audit.py`, `ifitwala_ed/utilities/contact_utils.py`
- Related current admissions CRM permissions: `ifitwala_ed/admission/admissions_crm_permissions.py`
Test refs: None for planned Relationship CRM visibility; related current tests are listed in the referenced contracts.

This contract defines planned ownership, visibility, and privacy rules for Education Relationship CRM.

## 1. Core Rule

Relationship visibility is:

```text
tenant scope + relationship team + role + explicit relationship visibility
```

Role alone is insufficient.

Native Frappe `Contact` visibility is insufficient.

Creator ownership alone is insufficient for institution-owned records.

## 2. Scope Anchors

Every implemented Relationship CRM record with lifecycle meaning must carry:

- `organization`
- optional `school`
- owner user
- owner team
- visibility mode

`school` may be optional only when the relationship is genuinely organization-level. If a relationship belongs to a specific school or branch, school scope must be explicit.

Selecting a parent school in a Relationship CRM filter must include descendant schools only when the endpoint contract says the surface is tree-aware. Requested school scope must always be intersected with the caller's visible school scope.

## 3. Planned Relationship Team Model

Planned Relationship Teams:

- Admissions
- Partnerships
- Advancement
- Careers
- Activities
- Finance
- Leadership
- Student Support

Relationship Team is a product ownership boundary, not merely a UI label.

Expected behavior:

- team members can see team-owned relationship work inside their tenant scope
- owner users can see their own assigned items inside tenant scope
- leadership visibility can be wider but must still be organization/school scoped
- finance visibility should expose only finance-relevant relationship state unless a broader role and team grants more
- academic or activities users should not gain raw sponsor, family, or contact data just because a relationship touches their work

## 4. Visibility Modes

Planned visibility modes:

- Owner Only
- Team
- Cross-Functional
- Leadership

Rules:

- `Owner Only` is still tenant-scoped and auditable.
- `Team` means members of the owner team within scope.
- `Cross-Functional` requires explicit secondary teams or approved audience rules.
- `Leadership` is scoped institutional oversight, not technical administrator bypass.

Exact field names require schema approval.

## 5. Creator And Assignment Rules

Creator may seed the initial owner, but creator is not the permanent permission model.

Rules:

- every active case should have an accountable owner
- reassignment must be a named workflow action
- queue membership must be derived server-side
- stale, due, and unassigned queues must be permission filtered before counts are returned
- blocked assignment must explain the missing scope, role, team, or enabled-user condition

## 6. Contact Data Rules

Relationship CRM must obey `../security/contact_data_governance.md`.

Rules:

- no broad native `Contact` list path
- no generic relationship contact export
- raw contact values require a named workflow, purpose, permission check, and audit where the contact governance contract requires it
- masked display values are the default
- a future Contact Point layer, if approved, remains an internal routing index rather than a user-facing address book
- relationship contact data belongs to the relationship domain record or approved contact-point service, not to a global person table

Rejected patterns:

- searching all contacts to find a sponsor
- exposing all partner emails to every staff user
- client-side matching by downloading broad contact payloads
- fuzzy auto-linking an Inquiry to a current family or partner without a staff decision

## 7. Current-Family Sensitivity

Current-family relationship work is especially sensitive because it may touch:

- student support concerns
- finance hardship
- retention risk
- admissions sibling planning
- guardian communication history
- attendance or wellbeing context

Rules:

- Relationship CRM may project current-family context only through named, purpose-bound DTOs.
- Sensitive student or finance data must not appear in broad Relationship Center queues.
- Raw contact and sensitive contextual data must be resolved only after the user opens a permitted context and the endpoint verifies purpose.
- A current-family relationship must not become a shortcut around Student, Guardian, Account Holder, or support-log permissions.

## 8. Partner And Sponsor Visibility

Partner and sponsor records may be institution-wide, but not automatically all-staff visible.

Examples:

- a music store sponsorship may be visible to Partnerships and Leadership, with limited event-context visibility for Activities
- a chamber of commerce careers partnership may be visible to Careers and Leadership, with limited event or placement context for Academic Staff
- a foundation scholarship relationship may be visible to Advancement, Finance, and Leadership, but not to ordinary admissions users unless linked to an approved workflow

Visibility should reveal the smallest useful context for the user's job.

## 9. Audit Expectations

Implementation must audit:

- raw contact-value access where required by contact governance
- assignment changes
- visibility mode changes
- owner team changes
- relationship/case closure and no-further-action reasons
- exceptional access decisions

Audit rows must not store raw contact values or full payload dumps.

## 10. Test Expectations

Tests must cover:

- role alone does not grant Relationship CRM access
- owner user access remains tenant-scoped
- team access remains tenant-scoped
- parent-school filters do not leak sibling-school relationships
- cross-functional visibility is explicit
- no native `Contact` broad-list fallback
- raw contact workflow paths are purpose checked and audited
- blocked actions return actionable reasons
- Relationship Center counts and rows are filtered before aggregation
