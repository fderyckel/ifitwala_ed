# Education File Semantics And Cross-App Upload Contract

Status: LOCKED target contract
Date: 2026-04-21
Related docs:

- `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`
- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`
- `ifitwala_drive/docs/04_coupling_with_ifiwala_ed.md`
- `ifitwala_drive/docs/06_api_contracts.md`

## Bottom line

- Ed owns workflow meaning, educational semantics, tenant scope, and user authorization.
- Drive owns upload sessions, binary finalize, governed storage, versions, derivatives, and grants.
- The contract between the apps should be one versioned workflow spec per governed upload surface.
- `File Classification` is outside the target contract and must not remain a parallel authority.

## 1. Why this document exists

The old model let workflow-specific code hand-author too many strings:

- purpose
- slot
- binding role
- retention policy
- attached field behavior

That makes the contract fragile.

Target model:

- each governed upload workflow has one canonical spec
- Drive validates against that spec
- the session persists the resolved contract needed for finalize

## 2. Educational semantic rules

File semantics should answer:

- why does the institution keep this file
- who is it about
- which workflow owns it
- which lifecycle governs it

The purpose must not be:

- the page where the upload happened
- the transport route
- the folder path
- a vague default such as `general`

## 3. Canonical purpose direction

This reset keeps the education semantics narrow and reusable.

| Purpose | Meaning | Typical workflow |
| --- | --- | --- |
| `learning_resource` | reusable or distributed teaching material | supporting material, task materials, course resources |
| `assessment_submission` | learner-submitted work for evaluation | task submission attachments |
| `assessment_feedback` | returned marked or feedback artifacts | feedback uploads |
| `portfolio_evidence` | curated evidence intentionally kept in a portfolio | portfolio flows |
| `journal_attachment` | attachment for reflective or journal workflows | journal flows |
| `academic_report` | formal evaluative record | transcripts, report cards, prior reports |
| `identification_document` | identity verification file | admissions or HR identity workflows |
| `medical_record` | health or medical evidence | health workflows |
| `policy_acknowledgement` | durable policy acknowledgement evidence | policy flows |
| `organization_public_media` | public presentation media | school/organization media |

## 4. Canonical workflow contract: `GovernedUploadSpec`

Each governed upload workflow must have one canonical `GovernedUploadSpec`.

Suggested examples:

- `supporting_material.file`
- `task.submission`
- `admissions.applicant_document`
- `admissions.applicant_profile_image`
- `org_communication.attachment`
- `organization_media.school_logo`

Each spec must define:

- `workflow_id`
- `contract_version`
- owner resolver
- attached target resolver
- primary subject resolver
- secondary subject rules when needed
- `data_class`
- `purpose`
- `retention_policy`
- slot resolver
- `binding_role` when needed
- privacy rule
- MIME restrictions when needed
- optional display/read profile identifier
- optional post-finalize callback identifier

For human identity-image workflows, privacy is spec-owned and defaults to private:

- `media.student_profile_image`
- `media.guardian_profile_image`
- `media.employee_profile_image`
- `admissions.applicant_profile_image`
- `admissions.applicant_guardian_image`

## 5. Authority split

### 5.1 Ed owns

- education semantics
- workflow meaning
- record ownership resolution
- tenant and role scope
- slot resolution rules
- surface-specific upload permission
- surface-specific read/open permission
- post-finalize mutation of business records

### 5.2 Drive owns

- upload session lifecycle
- temporary object storage
- blob ingress
- binary finalize
- storage object identity
- governed file/version/binding creation
- derivative generation
- preview/download grants
- erasure execution

### 5.3 No parallel authority

The spec is resolved by Ed and executed by Drive.

The same governance truth must not be duplicated into a second long-term authority such as `File Classification`.

## 6. Session persistence contract

Every governed upload session should persist the resolved contract needed for finalize:

- `workflow_id`
- `contract_version`
- resolved owner doctype/name
- resolved attached doctype/name/field when applicable
- resolved subject data
- resolved governance fields: purpose, retention policy, slot, organization, school
- resolved binding role when applicable
- upload strategy
- filename, expected size, MIME hint

Finalize should fail only when:

- the session no longer matches the authoritative business record
- the contract version is unsupported
- permissions no longer allow the action
- the bytes or MIME are invalid

Current runtime note:

- Drive persists the workflow metadata inside `Drive Upload Session.upload_contract_json.workflow`
- the session row itself remains the authority for resolved owner, attached target, subject, and governance fields
- finalize uses persisted `workflow_id` first and falls back to detection only for pre-registry sessions
- new session creation fails closed without `workflow_id`
- the locked generic DTO carries `workflow_id`, `contract_version`, and typed `workflow_result`; current runtime may also include `upload_token` for browser/proxy upload targets, but trusted server-side buffered ingest must not depend on it
- wrapper-specific metadata such as `row_name`, admissions item identifiers, or gallery captions must travel only through `workflow_result`

## 7. API shape direction

Target direction:

- Ed asks Drive to create an upload session using a `workflow_id` plus workflow identifiers
- Drive resolves and persists the authoritative spec at the boundary
- wrapper endpoints that still exist only for ergonomics are transitional compatibility, not the desired long-term contract
- current runtime already follows this model internally even though wrapper-specific public endpoints still exist

This lets the apps converge on one narrow boundary instead of many stringly wrapper exports.

## 8. Surface mapping

| Workflow | Purpose | Owner example | Slot example |
| --- | --- | --- | --- |
| `supporting_material.file` | `learning_resource` | `Supporting Material` | workflow-defined resource slot |
| `task.submission` | `assessment_submission` | `Task Submission` | `submission` |
| `task.feedback_export` | `assessment_feedback` | `Task Submission` | `feedback_export__released__student` |
| `admissions.applicant_document` | workflow-specific governed purpose | `Student Applicant` | applicant document slot |
| `admissions.applicant_profile_image` | `applicant_profile_display` | `Student Applicant` | `profile_image` |
| `admissions.applicant_guardian_image` | `applicant_profile_display` | `Student Applicant` | guardian row-derived image slot |
| `admissions.applicant_health_vaccination` | `medical_record` | `Student Applicant` | health evidence slot |
| `org_communication.attachment` | workflow-specific governed purpose | `Org Communication` | row-derived attachment slot |
| `student_log.evidence_attachment` | `safeguarding_evidence` | `Student Log` | row-derived evidence slot |
| `media.employee_profile_image` | `employee_profile_display` | `Employee` | `profile_image` |
| `media.student_profile_image` | `student_profile_display` | `Student` | `profile_image` |
| `media.guardian_profile_image` | `guardian_profile_display` | `Guardian` | `profile_image` |
| `organization_media.organization_logo` | `organization_public_media` | `Organization` | organization logo slot |
| `organization_media.school_logo` | `organization_public_media` | `School` or `Organization` | media-key-derived slot |
| `organization_media.school_gallery_image` | `organization_public_media` | `School` or `Organization` | gallery row-derived slot |
| `organization_media.asset` | `organization_public_media` | `Organization` or `School` | media-key-derived slot |

## 9. End-state rule for `File Classification`

`File Classification` is not part of the live cross-app contract.

Current rule:

- runtime code must not create, read, or depend on `File Classification`
- the cleanup refactor ends with patch-driven migration away from it and DocType removal
- any remaining mention of `File Classification` should now exist only in historical notes or migration commentary

## 10. Current-runtime note

Current code still retains some wrapper-specific public entrypoints and a small amount of finalize-time detection fallback for pre-registry sessions.

New governed session creation no longer falls back when `workflow_id` is missing.

Those patterns are transitional and are tracked in:

- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`
