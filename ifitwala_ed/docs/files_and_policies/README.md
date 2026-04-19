# Files And Policies Documentation Index

Status: Canonical index
Code refs: None
Test refs: None
Last reset: 2026-04-19

`ifitwala_ed/docs/files_and_policies/` is the canonical home for governed file architecture, GDPR-erasure policy, public-media governance, and institutional policy contracts.

Governed-file read order:

1. `files_01_architecture_notes.md`
   locked target architecture for governed file/media execution
2. `files_03_implementation.md`
   current runtime behavior, boundary leaks, and remediation order
3. `files_07_education_file_semantics_and_cross_app_contract.md`
   locked workflow/spec contract between Ed and Drive
4. `files_02_GDPR.md`
   canonical erasure and retention contract
5. `files_05_organization_media_governance.md`
   surface-specific governed organization media rules
6. `files_06_org_communication_attachment_contract.md`
   surface-specific governed attachment rules

Rules after the Phase 1 docs reset:

- `ifitwala_drive` is the sole governance and execution authority for governed files.
- `ifitwala_ed` remains the workflow, permission, and tenant-scope authority.
- `File Classification` is not part of the long-term architecture and must be removed during the refactor.
- if current code still reads or writes `File Classification`, treat that as transitional compatibility only.
- no new work may extend the old `File Classification` architecture or add new logic that depends on it.

Companion notes:

- `files_05_organization_media_governance.md`
- `files_06_org_communication_attachment_contract.md`

Those surface-specific notes must not weaken `files_01`, `files_03`, or `files_07`.

Policy-system read order:

- `policy_01_design_notes.md`
- `policy_02_controllers.md`
- `policy_03_taxinomy.md`
- `policy_06_enrolled_student_policy_acknowledgement_contract.md`

Planned future-policy docs:

- `policy_04_family_signature_and_consent_contract.md`
- `policy_05_phase2a_guardian_first_implementation_plan.md`

Non-authoritative notes:

- `files_08_cross_portal_governed_attachment_preview_contract.md`
- `audit_policy.md`
