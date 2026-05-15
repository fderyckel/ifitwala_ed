# Files And Policies Documentation Index

Status: Canonical index
Code refs: None
Test refs: None
Last reset: 2026-04-25

`ifitwala_ed/docs/files_and_policies/` is the canonical home for governed file architecture, attachment display contracts, privacy/erasure principles, public-media governance, and institutional policy contracts.

## Governed File Read Order

1. `files_01_architecture_notes.md`
   locked target architecture for governed file/media execution
2. `files_03_implementation.md`
   current runtime behavior, remaining compatibility baggage, and remediation order
3. `files_07_education_file_semantics_and_cross_app_contract.md`
   locked `GovernedUploadSpec` and Ed/Drive workflow contract
4. `files_08_cross_portal_governed_attachment_preview_contract.md`
   canonical open/preview/thumbnail DTO and route contract
5. `files_02_GDPR.md`
   privacy, retention, and erasure principles plus explicit implementation gaps

For Drive-side boundary details, also read:

- `../ifitwala_drive/ifitwala_drive/docs/14_drive_north_star_v1.md`
- `../ifitwala_drive/ifitwala_drive/docs/02_system_architecture.md`
- `../ifitwala_drive/ifitwala_drive/docs/04_coupling_with_ifiwala_ed.md`
- `../ifitwala_drive/ifitwala_drive/docs/06_api_contracts.md`

## Surface-Specific Companions

- `files_04_workflow_examples.md`
  current examples only; it does not override the canonical docs above
- `files_05_organization_media_governance.md`
  organization and school media rules
- `files_06_org_communication_attachment_contract.md`
  org communication attachment rules

Surface-specific notes must not weaken `files_01`, `files_03`, `files_07`, or `files_08`.

## Current Rules

- `ifitwala_drive` is the sole governed-file execution, metadata, derivative, grant, audit, and erasure authority.
- `ifitwala_ed` remains the workflow, permission, tenant-scope, and surface-visibility authority.
- New governed upload work uses `workflow_id + workflow_payload`.
- Wrapper-specific Drive APIs are transitional facades, not a second place to author workflow semantics.
- `File Classification` is retired and must not be used for new runtime behavior.
- Compatibility `File` rows are projections only.
- Folders are UX/navigation only, never permission, retention, ownership, or erasure truth.
- SPA/API contracts must expose server-owned actions such as `open_url`, `preview_url`, and `thumbnail_url`, not raw private storage paths.

## Do Not Do

- Do not add new wrapper-specific governance contracts.
- Do not hand-author owner, subject, slot, purpose, retention, organization, or school semantics inside Drive wrappers.
- Do not turn folders into permission, retention, ownership, or erasure truth.
- Do not expose Drive derivative roles as product API or SPA DTO fields.
- Do not add schema changes until wrapper-thinning and seam tests prove they are required.
- Do not reintroduce `File Classification`, raw `File.file_url`, or raw `/private/...` paths as authority for new governed flows.
- Do not restore finalize-time workflow detection for sessions missing persisted `workflow_id`.
- Do not put migration/backfill repair logic on the normal runtime path.
- Do not add new post-upload reads that depend on native `File` compatibility projections when Drive identity is available.

## Policy-System Read Order

- `policy_01_design_notes.md`
- `policy_02_controllers.md`
- `policy_03_taxinomy.md`
- `policy_06_enrolled_student_policy_acknowledgement_contract.md`

Planned future-policy docs:

- `policy_04_family_signature_and_consent_contract.md`
- `policy_05_phase2a_desk_authoring_portal_signing_plan.md`

Deprecated pointer:

- `policy_05_phase2a_guardian_first_implementation_plan.md`
  replaced by `policy_05_phase2a_desk_authoring_portal_signing_plan.md`

Non-authoritative notes:

- `audit_policy.md`
