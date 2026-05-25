---
title: "Applicant Document Type: Admissions Evidence Catalog"
slug: applicant-document-type
category: Admission
doc_order: 5
version: "1.4.0"
last_change_date: "2026-05-21"
summary: "Define the document types applicants may upload, which ones are required, and how each evidence type is classified for governed admissions files."
seo_title: "Applicant Document Type: Admissions Evidence Catalog"
seo_description: "Use Applicant Document Type to define admissions evidence requirements, portal upload options, readiness rules, and governed file classification."
---

## What Is an Applicant Document Type?

`Applicant Document Type` is the admissions evidence catalog. It defines the kinds of documents applicants may be asked to provide, such as passports, transcripts, recommendation letters, or family documents.

These types decide which upload options families see in the admissions portal, which evidence is required for readiness, and how uploaded files are classified for governed storage.

<Callout type="info" title="Why Ifitwala Ed is different">
Document requirements are not just labels in Ifitwala Ed. Each type can drive portal choices, readiness checks, repeatable requirements, school scope, and governed file classification, so admissions teams can ask for the right evidence without losing control of privacy and routing.
</Callout>

## Why This Matters

- **Families see the right upload choices.** Only active, in-scope types appear in the portal.
- **Readiness checks become consistent.** Required document types drive whether an applicant is missing evidence.
- **Repeatable requirements are supported.** A school can require multiple items for one type, such as three recommendation letters.
- **Historical evidence remains stable.** Deactivating a type retires future use without rewriting old applicant records.
- **File governance stays deterministic.** Each active type must resolve to a classification path before upload.

## Before You Create or Change Types

You should have:

- [**Organization**](/docs/en/organization/) ready
- [**School**](/docs/en/school/) ready when a type is school-specific
- stable `code` values chosen before go-live
- agreement on which documents are required, repeatable, or optional
- classification fields ready when the code is not covered by deterministic mapping

<Callout type="warning" title="Codes are long-lived">
Treat `code`, scope anchors, and classification fields as contract data. Changing them can affect portal visibility, readiness, and governed upload routing.
</Callout>

## Fields You Control

| Field or area | What it controls | Why it matters |
|---|---|---|
| Code | The stable identity of the document type | Used as the canonical key and autoname |
| Document type name | The human-readable label | Helps staff and families understand the request |
| Belongs to | Student, guardian, or family semantic category | Explains who the evidence relates to; it is not a permission switch |
| Organization / School | Scope where the type applies | Lets parent scope apply to descendant schools when appropriate |
| Is required | Whether the type participates in readiness checks | Required types must be satisfied or explicitly overridden |
| Is repeatable | Whether multiple submitted items can satisfy the type | Supports requirements like multiple recommendation letters |
| Minimum items required | Number of approved items required for repeatable types | Controls readiness count |
| Is active | Whether the type is available for future use | Retires types safely without deleting history |
| Classification fields | Slot, data class, purpose, retention policy | Ensures governed uploads route correctly |

## How This Fits the Admissions Workflow

<Steps title="Applicant Document Type governance">
  <Step title="Define the catalog">
    Create the evidence types your school asks for during admissions.
  </Step>
  <Step title="Set scope and requirement rules">
    Choose organization, optional school, required/repeatable flags, and classification details.
  </Step>
  <Step title="Publish to the portal">
    Active, in-scope types become upload options for applicants and families.
  </Step>
  <Step title="Drive readiness">
    Student Applicant readiness checks required types and waits for approved evidence or explicit admissions overrides.
  </Step>
  <Step title="Retire safely">
    Use `is_active = 0` to stop future use without changing historical evidence meaning.
  </Step>
</Steps>

## Permission Matrix

These records are operational setup for admissions evidence. Keep editing access limited to staff who understand document policy and file governance.

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Full Desk access |
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |

## Practical Examples

### Passport

Create one `passport` type, keep it non-repeatable, mark it required when the school needs passport evidence before approval, and ensure classification resolves correctly.

### Recommendation letters

Create a repeatable recommendation type with `min_items_required = 3` when the school requires three letters. Readiness waits for the required number of approved submitted items.

### School-specific document

Use a school-scoped type only when that school has a real policy difference. Otherwise, define the type at the organization or parent scope so descendant schools can reuse it.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use stable, deterministic code values and treat them as long-lived identifiers.</Do>
  <Do>Scope by organization or school only when the policy truly differs.</Do>
  <Do>Use canonical codes or fill classification fields so uploads never fail at setup time.</Do>
  <Do>Deactivate obsolete types instead of deleting historical meaning.</Do>
  <Dont>Use `belongs_to` as a permission or ownership switch.</Dont>
  <Dont>Change codes casually after applicants have uploaded evidence.</Dont>
  <Dont>Leave active types without a valid classification path.</Dont>
</DoDont>

## Common Questions

### Does `belongs_to` control permissions?

No. It is semantic metadata only. Admissions files are still owned by Applicant Document and Applicant Document Item workflows.

### What happens when a type is inactive?

Inactive types stop appearing for future portal use. Historical applicant evidence remains meaningful.

### Can parent-scope types apply to child schools?

Yes. Required-readiness matching uses active types whose organization/school scope matches applicant organization or school ancestors.

## Related Docs

<RelatedDocs
  slugs="applicant-document,student-applicant,applicant-health-profile,inquiry"
  title="Continue With Related Admissions Catalog and Evidence Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_document_type/applicant_document_type.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_document_type/applicant_document_type.py`
- **Required fields (`reqd=1`)**:
  - `code` (`Data`, unique)
  - `document_type_name` (`Data`)
- **Lifecycle hooks in controller**: `validate` (scope coherence + classification contract)
- **Operational/public methods**: none beyond standard document behavior
- **Autoname**: `field:code`

### Field Contract and Invariants

- `belongs_to` options: `student`, `guardian`, `family`
- `is_required` default `0`
- `is_repeatable` default `0`
- `min_items_required` default `1`; non-repeatable types are normalized back to `1`
- `is_active` default `1`
- optional scope: `organization`, `school`
- classification: `classification_slot`, `classification_data_class`, `classification_purpose`, `classification_retention_policy`

Non-negotiable invariants:

1. `code` is unique and acts as the canonical identity for the type.
2. Required-readiness contract is driven by active types where `is_required = 1` and scope matches applicant organization/school ancestors.
3. Repeatable requirements use `min_items_required`.
4. Portal upload options must be limited to active, in-scope types.
5. Upload classification must resolve for every active type, either from explicit fields or deterministic code mapping.
6. Type deactivation retires future use without rewriting historical applicant evidence.

### Runtime Surfaces

- [**Applicant Document**](/docs/en/applicant-document/) references one type per parent bucket.
- [**Student Applicant**](/docs/en/student-applicant/) readiness resolves required types by org/school scope.
- Portal/API surfaces:
  - `ifitwala_ed/api/admissions_portal.py::list_applicant_document_types`
  - `ifitwala_ed/api/admissions_portal.py::upload_applicant_document`
  - `ifitwala_ed/admission/admissions_portal.py::upload_applicant_document`
  - `ifitwala_drive.api.admissions.upload_applicant_document`
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
- Required-document readiness: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py::has_required_documents`
- Slot/classification source and deterministic code fallback: `ifitwala_ed/admission/admission_utils.py`
