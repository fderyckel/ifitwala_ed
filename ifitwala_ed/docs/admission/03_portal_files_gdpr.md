# Admissions Portal Files & GDPR Contract

Status: Current supporting contract
Date: 2026-04-19
Code refs: `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/admissions_portal.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/integrations/drive/admissions.py`, `ifitwala_ed/integrations/drive/authority.py`, `ifitwala_ed/api/file_access.py`, `../ifitwala_drive/ifitwala_drive/docs/04_coupling_with_ifiwala_ed.md`, `../ifitwala_drive/ifitwala_drive/docs/21_cross_portal_governed_attachment_preview_contract.md`
Test refs: `ifitwala_ed/api/test_admissions_portal.py`, `ifitwala_ed/admission/test_admissions_portal_uploads_unit.py`, `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`
Related docs:

- `01_governance.md`
- `05_admission_portal.md`
- `07_applicant_evidence_review_redesign.md`
- `10_ifitwala_drive_portal_uploads.md`
- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`

## Bottom Line

- Drive is the sole governed-file authority for admissions uploads.
- The admissions portal owns applicant-scoped permission checks, DTO shape, and stable Ed-owned action URLs.
- `Student Applicant` remains the primary subject for applicant-side portal uploads until promotion or identity-upgrade flows create new governed records for `Student` or `Guardian`.
- `File Classification` is not part of the live admissions runtime model.

## 1. Scope

This note defines the current file and GDPR boundary for:

- applicant profile image uploads
- applicant guardian image uploads
- applicant health vaccination proof uploads
- applicant evidence document uploads and reads
- applicant-side open/download URL behavior
- promotion-time and identity-upgrade file behavior

This note does not define a generic file platform. The broader Ed/Drive model is locked in the canonical file docs.

## 2. Authority Split

### 2.1 Ifitwala_Ed owns

- applicant and family portal authentication
- applicant-scoped permission checks
- resolving which business record an upload belongs to
- stable Ed-owned read/open URLs returned to the SPA
- promotion and identity-upgrade business workflows

### 2.2 Ifitwala_Drive owns

- upload session lifecycle
- temporary and final blob placement
- authoritative `Drive File` and `Drive File Version` metadata
- derivatives and preview state
- short-lived delivery grants resolved at request time

### 2.3 Compatibility rule

- Native Frappe `File` rows still exist because Ed surfaces and framework contracts use them.
- Those `File` rows are compatibility projections, not the governance authority.
- `File Classification` rows are removed from the runtime model and must not be reintroduced by new code or tests.

## 3. Applicant-Side Upload Contracts

All applicant-side uploads remain anchored to the current `Student Applicant` in Drive metadata.

### 3.1 Applicant profile image

- owner doctype/name: `Student Applicant`
- attached doctype/name: `Student Applicant`
- primary subject: `Student Applicant`
- slot: `profile_image`
- data class: `identity_image`
- purpose: `applicant_profile_display`
- retention policy: `until_school_exit_plus_6m`

### 3.2 Guardian profile image uploaded from admissions

- owner doctype/name: `Student Applicant`
- attached doctype/name: `Student Applicant Guardian`
- primary subject: `Student Applicant`
- slot: `guardian_profile_image__<guardian_row_name>`
- data class: `identity_image`
- purpose: `applicant_profile_display`
- retention policy: `until_school_exit_plus_6m`

This is an applicant-owned portal upload. Later identity-upgrade flows may create a new governed guardian profile image owned by `Guardian` with slot `profile_image`.

### 3.3 Health vaccination proof

- owner doctype/name: `Student Applicant`
- attached doctype/name: `Applicant Health Profile`
- primary subject: `Student Applicant`
- slot: `health_vaccination_proof_<row_key>`
- data class: `safeguarding`
- purpose: `medical_record`
- retention policy: `until_school_exit_plus_6m`

### 3.4 Applicant evidence documents

- owner doctype/name: `Student Applicant`
- attached doctype/name: `Applicant Document Item`
- primary subject: `Student Applicant`
- slot: derived from `Applicant Document Type.classification_*` settings plus the item key
- data class / purpose / retention policy: resolved from the approved document type settings

Portal uploads are requirement-centric:

- the applicant uploads against a requirement
- the server resolves or creates the `Applicant Document`
- the file attaches only to `Applicant Document Item`
- repeatable and non-repeatable behavior is owned by the admissions evidence contract, not the client

## 4. Portal Read/Open Contract

Admissions portal DTOs must never expose raw private storage paths as product truth.

Rules:

- the SPA receives stable Ed-owned action URLs or safe external links
- Ed validates applicant/family scope before opening a governed file
- Drive grants are issued just in time at the server route
- direct client construction of `/private/...` or object-store paths is forbidden

For applicant images, guardian images, vaccination proofs, and applicant evidence files:

- `resolve_admissions_file_open_url(...)` is the server baseline
- if a governed `Drive File` exists, Ed remains the permission gate before Drive delivery
- if a legacy compatibility-only `File` exists without Drive authority, Ed may still return its server-owned admissions download route while migrations complete

## 5. Upload Validation Rules

Applicant and guardian profile-image uploads remain tightly normalized:

- only `JPG`, `JPEG`, and `PNG` are accepted
- file extension and decoded bytes must agree
- image decode must succeed
- original upload size is capped at `10 MB`
- decoded image size is capped at `25 megapixels`
- the server normalizes accepted uploads to canonical `JPEG`
- EXIF orientation is applied and ancillary metadata is stripped

These validations are server-owned. The SPA cannot widen them.

## 6. Promotion And Identity Transitions

### 6.1 Promotion to Student

Approved applicant evidence is copied forward as new governed Student-owned uploads:

- source: approved `Applicant Document Item` files
- target owner/subject: `Student`
- the original applicant-side governed record remains part of the admissions history
- promotion does not mutate the applicant-side Drive record into a student record

### 6.2 Guardian identity upgrade

When an admissions guardian row upgrades into a real `Guardian` identity:

- the admissions-side guardian image may be used as the source
- Ed creates a new governed guardian `profile_image` Drive record
- Drive owns derivative scheduling for `thumb`, `card`, and `viewer_preview`
- the resulting `Guardian.guardian_image` points to the new guardian-owned compatibility `File` row

## 7. GDPR Stance

Admissions file governance is designed around deterministic subject ownership:

- applicant-side portal uploads are traceable to one `Student Applicant`
- retention policy is machine-readable on the authoritative Drive record
- applicant purge and erasure workflows operate on applicant-owned governed files without guessing storage paths
- promotion creates new governed records where the business owner changes rather than silently reinterpreting the old one

This preserves admissions history while keeping erasure and retention decisions explicit.

## 8. Non-Negotiable Rules

1. New admissions file writes must use the governed Drive upload path.
2. New code must not create or depend on `File Classification`.
3. Portal DTOs must keep using stable Ed-owned open/download routes.
4. Applicant evidence files attach only to `Applicant Document Item`, never directly to `Applicant Document`.
5. Promotion and identity-upgrade flows create new governed records when ownership changes.
6. Preview, thumbnail, and derivative generation remain Drive-owned.

## 9. Drift Checks

If a future change proposes any of the following, it is architectural drift and must be rejected or explicitly re-approved:

- restoring `File Classification` as runtime authority
- bypassing Drive upload sessions from admissions code
- returning raw private file paths in admissions SPA payloads
- reusing applicant-owned governed records as if they were already student-owned or guardian-owned after identity changes
