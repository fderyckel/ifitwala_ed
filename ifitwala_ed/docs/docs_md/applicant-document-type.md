---
title: "Applicant Document Type: Authoritative Admissions Evidence Catalog"
slug: applicant-document-type
category: Admission
doc_order: 5
version: "1.3.1"
last_change_date: "2026-02-23"
summary: "Define canonical admissions document types and codes that drive portal options, readiness checks, and deterministic file-classification slots."
seo_title: "Applicant Document Type: Authoritative Admissions Evidence Catalog"
seo_description: "Define canonical admissions document types and codes that drive portal options, readiness checks, and deterministic file-classification slots."
---

## Before You Start (Prerequisites)

- Create [**Organization**](/docs/en/organization/) first, and [**School**](/docs/en/school/) if you need school-scoped types.
- Define stable `code` values before go-live; `autoname` is `field:code`.
- Define classification fields (`classification_slot`, `classification_data_class`, `classification_purpose`, `classification_retention_policy`) for each active type.

`Applicant Document Type` is the canonical admissions evidence catalog. It defines what document slots exist and which of those slots are required in readiness checks.

## Authoritative Contract

`Applicant Document Type` controls admissions document semantics, not file ownership:

- semantic fields (`code`, `document_type_name`, `belongs_to`, `description`)
- scope fields (`organization`, `school`)
- gating fields (`is_required`, `is_active`)
- classification fields (`classification_slot`, `classification_data_class`, `classification_purpose`, `classification_retention_policy`)

`belongs_to` is semantic only (`student | guardian | family`) and does not change the rule that admissions files are owned by `Applicant Document`.

## Non-Negotiable Invariants

1. `code` is unique and acts as the canonical identity for the type.
2. Required-readiness contract is driven by active types where `is_required = 1`, scope matches applicant organization/school ancestors, and classification fields are complete.
3. Portal upload options must be limited to active, in-scope types.
4. Upload classification must resolve to slot/data-class/purpose/retention-policy for every active type.
5. Type deactivation (`is_active = 0`) retires future use without rewriting historical applicant evidence.

## Where It Is Used Across the ERP

- [**Applicant Document**](/docs/en/applicant-document/): each row references one type.
- [**Student Applicant**](/docs/en/student-applicant/): readiness check resolves required types by org/school scope.
- Admissions portal:
  - `list_applicant_document_types` (returns active, in-scope, upload-configured types)
  - `upload_applicant_document` pre-validation for activity and scope
- Governed upload routing:
  - source: classification fields on `Applicant Document Type`
  - active types without complete classification are rejected by admissions upload service

<Callout type="warning" title="Scope and classification are infrastructure">
Changing `code`, scope anchors, or classification fields is not cosmetic. It affects applicant visibility, readiness gating, and governed upload routing.
</Callout>

## Operational Guardrails

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use stable, deterministic `code` values and treat them as long-lived contract identifiers.</Do>
  <Do>Scope types by `organization`/`school` only when there is a real policy difference; ancestor scope applies to descendants.</Do>
  <Do>Set explicit classification fields for all active types so applicants never hit upload-time setup errors.</Do>
  <Dont>Use `belongs_to` as a permission or ownership switch; it is semantic metadata only.</Dont>
  <Dont>Deactivate by deleting historical meaning; prefer `is_active = 0` for retirement.</Dont>
</DoDont>

## Lifecycle and Governance Flow

<Steps title="Applicant Document Type Governance">
  <Step title="Define Catalog">
    Create the evidence catalog with canonical `code` and `document_type_name` values.
  </Step>
  <Step title="Set Scope and Requirements">
    Configure `organization`, optional `school`, requirement flags (`is_required`, `is_active`), and classification fields.
  </Step>
  <Step title="Publish to Portal Behavior">
    Portal document type listing returns only active and applicant-scoped types.
  </Step>
  <Step title="Drive Readiness">
    Student Applicant readiness treats required types as satisfied only when a corresponding Applicant Document is approved.
  </Step>
  <Step title="Evolve Safely">
    Retire obsolete types with `is_active = 0` and introduce new codes instead of mutating historical contract semantics.
  </Step>
</Steps>

## Reporting

- No dedicated Script/Query Report currently uses this doctype as `ref_doctype`.

## Related Docs

<RelatedDocs
  slugs="applicant-document,student-applicant,applicant-health-profile,inquiry"
  title="Related Admissions Catalog and Evidence Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-02-22)

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_document_type/applicant_document_type.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_document_type/applicant_document_type.py`
- **Required fields (`reqd=1`)**:
  - `code` (`Data`, unique)
  - `document_type_name` (`Data`)
- **Lifecycle hooks in controller**: `validate` (scope coherence + classification contract).
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Applicant Document Type` (`ifitwala_ed/admission/doctype/applicant_document_type/`)
- **Autoname**: `field:code`
- **Core field contract**:
  - `belongs_to` options: `student`, `guardian`, `family`
  - `is_required` default `0`
  - `is_active` default `1`
  - optional scope: `organization`, `school`
  - classification: `classification_slot`, `classification_data_class`, `classification_purpose`, `classification_retention_policy`
- **Portal/API surfaces**:
  - list endpoint: `ifitwala_ed/api/admissions_portal.py::list_applicant_document_types`
  - upload pre-validation path: `ifitwala_ed/api/admissions_portal.py::upload_applicant_document`
  - governed upload implementation: `ifitwala_ed/admission/admissions_portal.py::upload_applicant_document`
  - SPA consumer: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
- **Downstream gating use**:
  - required-document readiness in `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py::has_required_documents`
  - slot/classification source from doctype fields in `ifitwala_ed/admission/admission_utils.py`

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Full Desk access |
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
