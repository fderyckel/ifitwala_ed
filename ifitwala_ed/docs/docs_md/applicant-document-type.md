---
title: "Applicant Document Type: Defining Required Admission Evidence"
slug: applicant-document-type
category: Admission
doc_order: 5
summary: "Define document taxonomy by organization/school and drive readiness checks, portal upload options, and file classification behavior."
seo_title: "Applicant Document Type: Defining Required Admission Evidence"
seo_description: "Define document taxonomy by organization/school and drive readiness checks, portal upload options, and file classification behavior."
---

## Applicant Document Type: Defining Required Admission Evidence

## Before You Start (Prerequisites)

- Define your admissions document taxonomy and stable `code` values before go-live.
- Create `Organization` first, and create `School` first if you plan school-scoped document types.
- Confirm each document type `code` is mapped in governed upload slot logic; unmapped codes are rejected.

`Applicant Document Type` is the admissions document catalog. It defines what applicants must provide and what staff reviews.

## What You Configure

- Unique code (`autoname` uses `field:code`)
- Human label (`document_type_name`)
- Scope filters (`organization`, `school`)
- Requirement flags (`is_required`, `is_active`)
- Audience hint (`belongs_to`: student/guardian/family)

## Where It Is Used Across the ERP

- [**Applicant Document**](/docs/en/applicant-document/): each row references one document type.
- [**Student Applicant**](/docs/en/student-applicant/): readiness check queries required active document types by organization/school.
- Admissions portal:
  - `list_applicant_document_types`
  - upload-time scope validation before accepting files
- Governed uploads: code-based slot mapping in `APPLICANT_DOCUMENT_SLOT_MAP` (admission utilities) drives classification metadata.

<Callout type="note" title="Classification dependency">
If a document type code is not mapped for file classification, governed upload will reject that upload request.
</Callout>

## Technical Notes (IT)

- **DocType**: `Applicant Document Type` (`ifitwala_ed/admission/doctype/applicant_document_type/`)
- **Autoname**: `field:code`
- **Portal/API surfaces**:
  - list endpoint `ifitwala_ed/api/admissions_portal.py::list_applicant_document_types`
  - upload pre-validation endpoint `ifitwala_ed/api/admissions_portal.py::upload_applicant_document`
  - SPA page consuming type catalog: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
- **Controller**: no additional controller logic (`pass`)
- **Downstream validations**:
  - required types are used in applicant readiness and approval gate flows
  - portal checks `is_active` and organization/school scope before upload

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |

## Reporting

- No dedicated Script/Query Report currently uses this doctype as `ref_doctype`.

## Related Docs

- [**Applicant Document**](/docs/en/applicant-document/) - per-applicant document row and review
- [**Student Applicant**](/docs/en/student-applicant/) - readiness and approval workflow
