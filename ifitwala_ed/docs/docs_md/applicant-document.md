---
title: "Applicant Document: Authoritative Owner of Admissions Files"
slug: applicant-document
category: Admission
doc_order: 6
version: "1.4.3"
last_change_date: "2026-03-03"
summary: "Define Applicant Document as the applicant/type bucket and Applicant Document Item as per-file slot rows for review, readiness, and promotion."
seo_title: "Applicant Document: Authoritative Owner of Admissions Files"
seo_description: "Define Applicant Document parent buckets and Applicant Document Item per-file slots for admissions upload, review, readiness, and promotion."
---

## Before You Start (Prerequisites)

- Create the [**Student Applicant**](/docs/en/student-applicant/) record first.
- Configure required [**Applicant Document Type**](/docs/en/applicant-document-type/) records with valid classification fields and organization/school scope.
- Use governed upload/classification flows only; do not use ad-hoc direct file insert patterns.

`Applicant Document` is the semantic owner of admissions evidence scope. It is the parent bucket by applicant + type, not a generic attachment row and not optional metadata.

## Authoritative Admissions Boundary

`Applicant Document` is the canonical container between applicant lifecycle and file governance:

- `Inquiry` -> `Student Applicant` -> `Applicant Document` -> promotion copy to `Student`
- admissions file entries are modeled as `Applicant Document Item` rows under each `Applicant Document`
- direct admissions file attachment to `Student Applicant` or `Student` is forbidden
- only `Student Applicant.applicant_image` remains a specific identity-image exception

<Callout type="warning" title="Non-negotiable ownership rule">
All admissions evidence files must attach to `Applicant Document Item` (scoped under `Applicant Document`). Treat any alternative attachment path as an architecture bug.
</Callout>

## Parent vs Item Model (Authoritative)

| Layer | Doctype | Record cardinality | Responsibility |
|---|---|---|---|
| Catalog | `Applicant Document Type` | many global scoped rows | Defines required/repeatable evidence semantics |
| Applicant bucket | `Applicant Document` | max one per (`student_applicant`, `document_type`) | Parent contract, promotion flags, aggregate review timeline |
| File slot | `Applicant Document Item` | many per `Applicant Document` | Per-file slot (`item_key`, `item_label`, item review status) |

`Applicant Document Item` is a **normal DocType**, not a child table, with independent permissions and lifecycle hooks.

## Non-Negotiable Invariants

1. One logical document slot per applicant/type (`student_applicant`, `document_type`).
2. `student_applicant` and `document_type` are immutable after insert.
3. Every uploaded evidence file is represented by one `Applicant Document Item` row; `item_key` is required and unique within the parent document.
4. Parent `Applicant Document.review_status` is synchronized from item review states:
   - any item `Rejected` -> parent `Rejected`
   - all items `Approved` -> parent `Approved`
   - otherwise -> parent `Pending`
5. `is_promotable` is valid only when `review_status = Approved`.
6. Applicant-side evidence is retained as admissions history; promotion creates student-side copies.
7. Portal users can upload/view only; they cannot review, retype, or delete records.

## Capability Boundaries

| Actor | Allowed | Forbidden |
|---|---|---|
| `Admissions Applicant` (portal) | list types, list documents, upload document file | approve/reject, edit review fields, change `document_type`, delete rows |
| `Admission Officer` / `Admission Manager` | create/manage rows, review decisions, promotion flags | bypassing immutable field rules |
| `Academic Admin` / `System Manager` | reviewer decisions and promotion flags | bypassing immutable field rules |

## Operational Guardrails

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use one canonical row per (`student_applicant`, `document_type`) and treat new uploads as newer evidence for that slot.</Do>
  <Do>Use reviewer roles (`Admission Officer`, `Admission Manager`, `Academic Admin`, or `System Manager`) for `review_status` and `is_promotable` decisions.</Do>
  <Dont>Attach admissions evidence directly to `Student Applicant` or `Student`.</Dont>
  <Dont>Re-link applicant-side `File` rows to student records during promotion.</Dont>
</DoDont>

## Lifecycle and Linked Documents

<Steps title="Applicant Document Authoritative Flow">
  <Step title="Create Slot">
    Create or resolve a single `Applicant Document` for (`student_applicant`, `document_type`).
  </Step>
  <Step title="Upload Evidence">
    Upload files through governed admissions endpoints so files attach to `Applicant Document Item` rows under the parent bucket.
  </Step>
  <Step title="Review">
    Reviewer roles set item-level review fields; parent review state is synchronized from item outcomes.
  </Step>
  <Step title="Set Promotion Semantics">
    Mark `is_promotable` only after approval and set `promotion_target` where applicable.
  </Step>
  <Step title="Promote Applicant">
    Promotion copies approved applicant evidence into new `Student` files with lineage; applicant-side files remain unchanged.
  </Step>
</Steps>

## Promotion Boundary (Applicant -> Student)

Promotion must keep admissions and student ownership separated:

- source files remain attached to `Applicant Document Item` rows
- student receives new file records (copy), never re-linked applicant records
- only approved applicant documents are considered
- non-promotable or rejected evidence stays applicant-side only

This preserves auditability, GDPR-local erasure semantics, and operational traceability.

## Validation and Gating Checkpoints

1. `Applicant Document.validate`
- permission guard (`UPLOAD_ROLES` + reviewer-only field guard)
- applicant terminal-state lock (`Rejected`, `Promoted`)
- immutable anchor guard (`student_applicant`, `document_type`)
- uniqueness guard on (`student_applicant`, `document_type`)
- review metadata stamping when status changes
- promotion flag guard (`is_promotable` requires approved + reviewer role)

2. `Applicant Document.before_delete`
- blocks deletion when legacy files are directly attached to `Applicant Document`
- linked `Applicant Document Item` rows keep the parent in-use through link integrity checks
- allows override only for `System Manager`

3. Portal upload flow (`upload_applicant_document`)
- applicant identity/scope checks
- document type scope/activity checks (ancestor-aware org/school scope)
- document type upload classification contract checks
- governed classification with `primary_subject_type = Student Applicant`
- resolves/creates `Applicant Document Item` (`item_key`, `item_label`) under parent bucket
- file attachment target forced to `Applicant Document Item`
- writes timeline comments on `Student Applicant` for each upload/replace event (who, when, source, file link)
- materializes `Applicant Review Assignment` rows for matching `Applicant Review Rule` scope/reviewers

4. Student Applicant readiness (`has_required_documents`)
- required doc types must exist and be approved
- approval readiness fails for missing/unapproved required slots

5. Applicant document edit timeline (`Applicant Document.on_update`)
- review/edit changes (status, notes, promotable flags, promotion target) are comment-audited on `Student Applicant`

## Worked Examples

### Example 1: Single passport upload (non-repeatable type)

1. `Applicant Document Type(passport)` is configured as `is_repeatable = 0`.
2. Applicant uploads `passport.pdf`.
3. System resolves one `Applicant Document` for (`student_applicant`, `passport`), then creates one `Applicant Document Item` slot (for example `item_key = passport`).
4. Staff reviews the item and marks it `Approved`.
5. Parent `Applicant Document.review_status` becomes `Approved` by sync.

### Example 2: Repeatable recommendations requiring 3 letters

1. `Applicant Document Type(recommendation_letter)` is configured with `is_repeatable = 1`, `is_required = 1`, `min_items_required = 3`.
2. Three independent `Applicant Document Item` rows are created (for example `reco_1`, `reco_2`, `reco_3`), each with its own file.
3. Readiness check (`Student Applicant.has_required_documents`) requires:
   - at least 3 uploaded items, and
   - at least 3 approved items.
4. If only 2 are approved, the type is present but still blocks readiness as unapproved/incomplete.

## Edge Cases and Runtime Behavior

- `min_items_required` resets to `1` when `is_repeatable = 0`:
  - This is intentional server normalization in `Applicant Document Type.validate`, not a save error.
- Missing `item_key` on upload:
  - System generates a deterministic sanitized key and still creates a valid `Applicant Document Item`.
- Mixed review outcomes across items:
  - One rejected item makes the parent `Applicant Document` rejected.
  - Mixed pending/approved (without rejection) keeps parent pending.
- Legacy records created before itemized model:
  - Readiness includes fallback handling for legacy files attached directly to `Applicant Document`.
  - New uploads must use `Applicant Document Item`.

## Reporting

- No dedicated Script/Query Report currently declares `Applicant Document` as `ref_doctype`.

## Related Docs

<RelatedDocs
  slugs="student-applicant,applicant-document-type,applicant-health-profile,applicant-interview"
  title="Related Admissions Evidence Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-03-03)

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.py`
- **Required fields (`reqd=1`)**:
  - `student_applicant` (`Link` -> `Student Applicant`)
  - `document_type` (`Link` -> `Applicant Document Type`)
- **Lifecycle hooks in controller**: `validate`, `on_update`, `before_delete`
- **Operational/public methods**: `get_file_routing_context`

- **DocType**: `Applicant Document` (`ifitwala_ed/admission/doctype/applicant_document/`)
- **Autoname**: `hash`
- **Per-file slot doctype**: `Applicant Document Item` (`ifitwala_ed/admission/doctype/applicant_document_item/`)
- **Core field contract**:
  - `document_label` optional override label
  - `review_status` options: `Pending`, `Approved`, `Rejected`, `Superseded` (default `Pending`)
  - `is_promotable` default `0`
  - `promotion_target` options: `Student`, `Administrative Record`
- **Routing context contract (`get_file_routing_context`)**:
  - `root_folder = Home/Admissions`
  - `subfolder = Applicant/<student_applicant>/Documents/<doc_type_code>`
  - `file_category = Admissions Applicant Document`
  - `logical_key = <doc_type_code>`
- **Portal/API surfaces**:
  - governed endpoint: `ifitwala_ed/admission/admissions_portal.py::upload_applicant_document`
  - portal list endpoints: `ifitwala_ed/api/admissions_portal.py::list_applicant_documents`, `list_applicant_document_types`
  - portal upload wrapper: `ifitwala_ed/api/admissions_portal.py::upload_applicant_document`
  - focus review action endpoint: `ifitwala_ed/api/focus.py::submit_applicant_review_assignment`
  - SPA page: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
- **Runtime role guards (controller)**:
  - upload/manage roles: admissions roles + `Academic Admin` + `System Manager` + `Admissions Applicant`
  - reviewer roles: `Admission Officer`, `Admission Manager`, `Academic Admin`, `System Manager`
  - review-field mutation is blocked for non-reviewer roles
- **Readiness and promotion integration**:
  - required-document readiness check in `Student Applicant.has_required_documents()`
  - promotion copy flow uses approved applicant docs in `Student Applicant._copy_promotable_documents_to_student()`
  - per-item readiness counting by `Applicant Document Item` upload + item review status

### Permission Matrix (DocType Permissions)

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `Admission Manager` | Yes | Yes | Yes | Yes | Runtime delete guard applies when files exist |
| `Admission Officer` | Yes | Yes | Yes | Yes | Reviewer authority |
| `Academic Admin` | Yes | Yes | Yes | Yes | Reviewer authority |
| `System Manager` | Yes | Yes | Yes | Yes | Reviewer authority + delete override with attached files |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes | Runtime guard limits review semantics |
| `Admissions Applicant` | Yes | Yes | Yes | No | Portal-scoped behavior still enforced server-side |
| `Academic Assistant` | Yes | Yes | Yes | Yes | Runtime guard limits review semantics |

Runtime controller rules are authoritative over DocType matrix permissions.
