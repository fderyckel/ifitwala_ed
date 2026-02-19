---
title: "Applicant Document: Governed Admission File Record"
slug: applicant-document
category: Admission
doc_order: 6
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
- Admissions portal:
  - lists document rows and latest uploaded file
  - uploads route through governed endpoint and create/resolve Applicant Document rows
- Governed file services:
  - `ifitwala_ed.admission.admissions_portal.upload_applicant_document`
  - `ifitwala_ed.utilities.file_dispatcher.create_and_classify_file`

## File Governance Behavior

- Files are attached to `Applicant Document`, not directly to `Student Applicant` (except applicant image).
- Deletion is blocked when attached files exist, except System Manager override.
- Routing/classification context is generated from document type code and applicant identity context.

<Callout type="warning" title="Immutability by design">
Changing an uploaded document's type or applicant after submission is blocked. Replace with a new governed upload instead.
</Callout>

## Lifecycle and Linked Documents

1. Create/select the applicant and choose the exact required document type.
2. Upload through governed flows so one canonical row is maintained per applicant and document type.
3. Admissions reviewers update review fields and promotion relevance as evidence is assessed.
4. On promotion, only approved/promotable evidence is carried into student-facing records.

<Callout type="info" title="Why this is strict">
This doctype is the legal/operational evidence anchor for admissions. Use replacement uploads, not field mutation, when evidence changes.
</Callout>

## Technical Notes (IT)

### Schema and Controller Snapshot

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

- [**Applicant Document Type**](/docs/en/applicant-document-type/) - catalog and requirement rules
- [**Student Applicant**](/docs/en/student-applicant/) - readiness and decision lifecycle
- [**Applicant Health Profile**](/docs/en/applicant-health-profile/) - complementary review evidence
