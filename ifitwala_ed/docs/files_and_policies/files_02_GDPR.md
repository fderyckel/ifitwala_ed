# Privacy, Retention, And Erasure Principles For Governed Files

Status: Canonical principles and implementation gaps
Last updated: 2026-04-25
Code refs:
- `../ifitwala_drive/ifitwala_drive/services/audit/erasure.py`
- `../ifitwala_drive/ifitwala_drive/api/erasure.py`
- `ifitwala_ed/integrations/drive/workflow_specs.py`
- `ifitwala_ed/api/file_access.py`
Test refs: No complete Ed-side DPO/retention workflow tests exist yet.

## Bottom Line

- Governed file erasure must be driven by Drive metadata, not folder paths.
- Applicants and Students remain separate data-subject states with different retention and erasure posture.
- Drive currently owns file erasure execution; Ed still needs an explicit legal/business workflow for erasure decisions.
- This note is a technical architecture contract, not legal advice. GDPR, Thailand PDPA, and other jurisdiction-specific retention rules need counsel review before implementation.

## 1. Scope

This note covers governed files and attachments connected to:

- admissions applicants
- promoted students
- guardians and employees when their files are handled through Ed workflows
- organization and school media
- task, material, communication, health, safeguarding, portfolio, and similar governed attachment surfaces

This note does not define a complete legal process for data-subject requests. It defines how the file architecture must support one.

## 2. Data-Subject Separation

Applicant-scoped data is pre-enrollment data. It is normally more erasable than student data because it is tied to admissions, consent, and pre-contractual processing.

Student-scoped data is institutional education data. It may include records the school must retain for academic, safeguarding, financial, audit, or statutory reasons. Student data should not be treated as blanket-delete data.

Institutional records such as audit events, financial ledgers, anonymized aggregates, and legally required academic history may need retention or pseudonymization instead of physical deletion.

The implementation must therefore support three outcomes:

- erase file content and derivative artifacts when lawful and approved
- retain structured institutional records when legally required
- pseudonymize or minimize personal identifiers when deletion would corrupt required institutional records

## 3. Metadata-Driven Erasure Rule

Erasure scope must be resolved from governed metadata, including:

- `primary_subject_type`
- `primary_subject_id`
- `owner_doctype`
- `owner_name`
- `slot`
- `purpose`
- `retention_policy`
- `organization`
- `school`

Folders are UX/navigation only. They must never be used as legal or governance truth.

Forbidden erasure selectors:

- storage folder paths
- guessed `File.file_url` prefixes
- raw `/private/...` paths
- browser-visible URLs
- historical folder naming conventions
- compatibility `File` rows as the sole source of truth

Drive is responsible for erasing or tombstoning governed file content, versions, derivatives, grants, and file metadata according to its own erasure execution model.

Ed is responsible for deciding whether the business/legal workflow permits erasure for the subject and scope.

## 4. Current Runtime Reality

Implemented today:

- governed upload sessions persist workflow metadata and resolved governance fields
- `Drive File`, version, binding, derivative, and access-event records are the file authority
- Ed read surfaces return stable server-owned `open_url`, `preview_url`, and `thumbnail_url` values instead of raw storage paths
- Drive has an erasure execution service that can operate against Drive file metadata

Not implemented as a complete Ed-side legal workflow:

- DPO role and approval workflow
- Ed-owned erasure request/case workflow
- organization/school retention configuration workflow
- immutable Ed-side GDPR erasure log
- applicant erasure orchestration across all non-file admissions records
- student pseudonymization orchestration across academic, safeguarding, finance, and communication records
- counsel-approved jurisdiction-specific retention matrix

Any earlier documentation that marked those items as done was stale. These are implementation gaps until matching DocTypes, permissions, APIs, tests, and operating procedures exist.

## 5. Future Workflow Guardrails

When the Ed-side erasure workflow is implemented, it must:

- require explicit authorized approval before destructive action
- distinguish Applicant erasure from Student retention/pseudonymization
- resolve file scope by Drive metadata, never by folders
- call Drive erasure execution only after Ed has made the subject-level decision
- keep an immutable audit trail of who approved, who executed, what scope was requested, what was erased, and what was retained
- fail closed when retention law, subject identity, tenant scope, or file authority cannot be proven
- avoid automatic destructive erasure until retention rules, approval roles, and auditability are implemented and tested

## 6. Retired Concepts

`File Classification` is retired from the live governed-file architecture and must not be used as runtime authority for new behavior.

Legacy helper names such as `erase_applicant_data(...)` or `pseudonymize_student(...)` are not active API contracts in the current runtime. If future work introduces named erasure or pseudonymization endpoints, those endpoints must be designed from the current Drive metadata model and documented with code/test refs at that time.

## 7. Documentation Rules For New Work

New file, attachment, preview, or erasure docs must preserve these statements:

- Drive executes governed file storage, metadata, derivatives, grants, audit, and erasure.
- Ed decides workflow meaning, tenant scope, surface visibility, and legal/business authorization.
- Folders are navigation only.
- Raw private paths are not SPA/API contracts.
- Erasure is metadata-driven.
- Unimplemented legal workflows must be marked as gaps, not completed contracts.
