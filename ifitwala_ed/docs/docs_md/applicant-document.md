---
title: "Applicant Document: Governed Admission File Record"
slug: applicant-document
category: Admission
doc_order: 6
version: "1.2.0"
last_change_date: "2026-02-21"
summary: "Track each applicant document type, review status, and promotion relevance with strict immutability and governed file handling."
seo_title: "Applicant Document: Governed Admission File Record"
seo_description: "Track each applicant document type, review status, and promotion relevance with strict immutability and governed file handling."
---

## Applicant Document: Governed Admission File Record

## Before You Start (Prerequisites)

- Create the `Student Applicant` record first.
- Create the relevant `Applicant Document Type` first.
- Use governed upload/classification flows for attachments instead of direct ad-hoc file inserts.

`Applicant Document` is the authoritative record for one document type submitted by one applicant. It is not just a file attachment row; it carries review and promotion semantics.

## What It Enforces

- One row per (`student_applicant`, `document_type`)
- Immutable anchors after creation (`student_applicant`, `document_type`)
- Review status with review metadata stamping
- Promotion eligibility guard (`is_promotable` requires approved review)

## Where It Is Used Across the ERP

- [**Student Applicant**](/docs/en/student-applicant/):
  - readiness requires required document types present and approved
  - approval flow uses this readiness check
- Admissions portal (Applicant-facing):
  - lists the applicant's document rows and latest uploaded file (`list_applicant_documents`)
  - lists allowed document types in applicant scope (`list_applicant_document_types`)
  - uploads/replaces files through governed endpoint (`upload_applicant_document`)
- Governed file services:
  - `ifitwala_ed.admission.admissions_portal.upload_applicant_document`
  - `ifitwala_ed.utilities.file_dispatcher.create_and_classify_file`

## Admission Portal and Staff Experience

### Admissions Applicant (Portal / SPA)

- The applicant sees a document checklist-style page with:
  - required/optional document types
  - status per type (`Missing`/`Pending review`/`Approved`/`Rejected`)
  - latest uploaded file link
- Applicant upload is restricted to their own linked `Student Applicant` record.
- Portal upload source is `SPA` and goes through dispatcher-backed classification.
- Applicants do **not** review/approve documents from portal.

### Admission Officer / Admission Manager (Operational side)

- These roles typically work from Desk/operations context on `Applicant Document` rows.
- They can manage document rows and attachments operationally.
- Runtime rule still applies: changing review fields is restricted to reviewer roles (below).

### Academic Admin / System Manager (Review authority)

- Only these reviewer roles can update review fields:
  - `review_status`
  - `review_notes`
  - `reviewed_by`
  - `reviewed_on`
- `is_promotable` is also guarded and requires `review_status = Approved`.

## File Governance Behavior

- Files are attached to `Applicant Document`, not directly to `Student Applicant` (except applicant image).
- Deletion is blocked when attached files exist, except System Manager override.
- Routing/classification context is generated from document type code and applicant identity context.

<Callout type="warning" title="Immutability by design">
Changing an uploaded document's type or applicant after submission is blocked. Replace with a new governed upload instead.
</Callout>

## Operational Guardrails

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Create one canonical row per (`student_applicant`, `document_type`) and replace evidence through governed upload flows.</Do>
  <Do>Use reviewer roles (`Academic Admin`/`System Manager`) for review-status decisions and promotion flags.</Do>
  <Dont>Bypass dispatcher/classification and attach ad-hoc files directly for admissions evidence.</Dont>
  <Dont>Mutate immutable anchors after creation (`student_applicant`, `document_type`).</Dont>
</DoDont>

## Lifecycle and Linked Documents

<Steps title="Applicant Document Lifecycle">
  <Step title="Create">
    Create/select the applicant and choose the exact required document type.
  </Step>
  <Step title="Upload">
    Upload through governed flows so one canonical row is maintained per applicant and document type.
  </Step>
  <Step title="Review">
    Admissions reviewers update review fields and promotion relevance as evidence is assessed.
  </Step>
  <Step title="Promote">
    On promotion, only approved/promotable evidence is carried into student-facing records.
  </Step>
</Steps>

## When Validation Happens

Validation is enforced server-side in multiple checkpoints:

1. `Applicant Document` save (`validate`)
   - permission checks
   - applicant terminal-state lock
   - immutable anchors (`student_applicant`, `document_type`)
   - unique `(student_applicant, document_type)`
   - review metadata stamping
   - promotion flag constraints

2. `Applicant Document` delete (`before_delete`)
   - blocks deletion when attached files exist (except System Manager)

3. Admissions portal upload flow
   - applicant identity + ownership checks (`Admissions Applicant` linked to exactly one applicant)
   - document type active/scope checks (organization/school)
   - governed upload checks:
     - slot mapping from `Applicant Document Type.code`
     - classification payload validity
     - allowed `upload_source` set (`Desk`, `SPA`, `API`, `Job`)

4. Applicant readiness / decision checks (`Student Applicant`)
   - required document types are resolved from `Applicant Document Type` (`is_required=1`, active, scoped)
   - each required type must have an `Applicant Document` row with `review_status = Approved`
   - approval readiness fails if required docs are missing or unapproved

5. Promotion to Student
   - only approved documents are eligible for copy
   - copy uses governed file creation with `source_file` lineage preserved
   - promotion fails if required copy operation fails (atomic safety)

<Callout type="info" title="Why this is strict">
This doctype is the legal/operational evidence anchor for admissions. Use replacement uploads, not field mutation, when evidence changes.
</Callout>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-02-21)

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.py`
- **Required fields (`reqd=1`)**:
  - `student_applicant` (`Link` -> `Student Applicant`)
  - `document_type` (`Link` -> `Applicant Document Type`)
- **Lifecycle hooks in controller**: `validate`, `before_delete`
- **Operational/public methods**: `get_file_routing_context`

- **DocType**: `Applicant Document` (`ifitwala_ed/admission/doctype/applicant_document/`)
- **Autoname**: `hash`
- **Portal/API surfaces**:
  - public-facing upload implementation in `ifitwala_ed/admission/admissions_portal.py`
  - admissions portal wrapper endpoint in `ifitwala_ed/api/admissions_portal.py::upload_applicant_document`
  - admissions portal document listing in `ifitwala_ed/api/admissions_portal.py::list_applicant_documents`
  - SPA page using list/upload flow: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
- **Key validation methods**:
  - `_validate_permissions`
  - `_validate_applicant_state`
  - `_validate_immutable_fields`
  - `_validate_unique_document_type`
  - `_validate_review_status`
  - `_validate_promotion_flags`
  - `_validate_delete_allowed`
- **Review statuses**: `Pending`, `Approved`, `Rejected`, `Superseded`
- **Link fields**:
  - `student_applicant` -> `Student Applicant`
  - `document_type` -> `Applicant Document Type`
  - `reviewed_by` -> `User`

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access; delete guard bypass for attached files |
| `Academic Admin` | Yes | Yes | Yes | Yes | Can edit review fields |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |

Runtime controller rules:
- Upload/manage permission requires admissions or approved roles.
- Review-field edits (`review_status`, notes, reviewer fields) are restricted to `Academic Admin` or `System Manager`.
- Terminal applicant states (`Rejected`, `Promoted`) are read-only.

## Reporting

- No dedicated Script/Query Report currently declares this doctype as `ref_doctype`.

## Related Docs

<RelatedDocs
  slugs="applicant-document-type,student-applicant,applicant-health-profile"
  title="Related Evidence and Readiness Docs"
/>
