---
title: "Applicant Document: Authoritative Owner of Admissions Files"
slug: applicant-document
category: Admission
doc_order: 6
version: "1.7.2"
last_change_date: "2026-04-25"
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
- binary upload/finalize for applicant documents is delegated by `ifitwala_ed.admission.admissions_portal` to `ifitwala_drive.api.admissions.upload_applicant_document`

<Callout type="warning" title="Non-negotiable ownership rule">
All admissions evidence files must attach to `Applicant Document Item` (scoped under `Applicant Document`). Treat any alternative attachment path as an architecture bug.
</Callout>

## Parent vs Item Model (Authoritative)

| Layer | Doctype | Record cardinality | Responsibility |
|---|---|---|---|
| Catalog | `Applicant Document Type` | many global scoped rows | Defines required/repeatable evidence semantics |
| Applicant bucket | `Applicant Document` | max one per (`student_applicant`, `document_type`) | Requirement card, explicit override policy, promotion routing, aggregate review timeline |
| File slot | `Applicant Document Item` | many per `Applicant Document` | One submitted file (`item_key`, `item_label`, item review status) |

`Applicant Document Item` is a **normal DocType**, not a child table, with independent permissions and lifecycle hooks.

## Non-Negotiable Invariants

1. One logical document slot per applicant/type (`student_applicant`, `document_type`).
2. `student_applicant` and `document_type` are immutable after insert.
3. Every uploaded evidence file is represented by one `Applicant Document Item` row; `item_key` is required and unique within the parent document.
4. Parent `Applicant Document.review_status` is synchronized from item review states:
   - approved submission count meeting the requirement count -> parent `Approved`
   - any active item `Rejected` before requirement completion -> parent `Rejected`
   - otherwise -> parent `Pending`
5. Requirement waivers and exceptions are explicit parent-level policy overrides (`Waived`, `Exception Approved`) and are restricted to `Admission Manager`, `Academic Admin`, and `System Manager`.
6. Applicant-side evidence is retained as admissions history; promotion creates student-side copies.
7. Portal users can upload/view only; they cannot review, retype, or delete records.

## Capability Boundaries

| Actor | Allowed | Forbidden |
|---|---|---|
| `Admissions Applicant` (portal) | list types, list documents, upload document file | approve/reject, edit review fields, change `document_type`, delete rows |
| `Admission Officer` | create/manage rows, review submitted files from applicant context, promotion routing | set requirement waivers/exceptions, bypass immutable field rules |
| `Admission Manager` | create/manage rows, review submitted files from applicant context, promotion routing, requirement waivers/exceptions | bypassing immutable field rules |
| `Academic Admin` / `System Manager` | review submitted files from applicant context, promotion routing, requirement waivers/exceptions | bypassing immutable field rules |

## Operational Guardrails

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use one canonical row per (`student_applicant`, `document_type`) and treat new uploads as newer evidence for that slot.</Do>
  <Do>Use explicit requirement overrides (`Waived`, `Exception Approved`) when schools allow documented waivers/exceptions.</Do>
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
  <Step title="Apply Policy Overrides When Needed">
    If the school allows a waiver or exception, `Admission Manager`, `Academic Admin`, or `System Manager` records it on the parent requirement with a mandatory reason.
  </Step>
  <Step title="Set Promotion Semantics">
    Set `promotion_target` where applicable so promotion knows whether approved evidence should copy to `Student`.
  </Step>
  <Step title="Promote Applicant">
    Promotion copies approved applicant evidence into new `Student` files with lineage; applicant-side files remain unchanged.
  </Step>
</Steps>

## Promotion Boundary (Applicant -> Student)

Promotion must keep admissions and student ownership separated:

- source files remain attached to `Applicant Document Item` rows
- student receives new file records (copy), never re-linked applicant records
- only approved submission-backed applicant requirements are considered
- current runtime excludes rows when `promotion_target` is explicitly not `Student`

This preserves auditability, GDPR-local erasure semantics, and operational traceability.

## Validation and Gating Checkpoints

1. `Applicant Document.validate`
- permission guard (`UPLOAD_ROLES` + reviewer-only field guard)
- applicant terminal-state lock (`Rejected`, `Promoted`)
- immutable anchor guard (`student_applicant`, `document_type`)
- uniqueness guard on (`student_applicant`, `document_type`)
- aggregate review fields are server-derived and cannot be edited directly
- requirement override guard (`Waived` / `Exception Approved` require manager/admin role + reason)
- promotion routing guard (`promotion_target`, `promotion_notes`) is reviewer-managed

2. `Applicant Document.before_delete`
- blocks deletion when invalid direct files are attached to `Applicant Document`
- linked `Applicant Document Item` rows keep the parent in-use through link integrity checks
- allows override only for `System Manager`

3. Portal upload flow (`upload_applicant_document`)
- applicant identity/scope checks
- document type scope/activity checks (ancestor-aware org/school scope)
- document type upload classification contract checks
- resolves/creates `Applicant Document` and `Applicant Document Item` in `ifitwala_ed` before the file is sent to Drive
- delegates upload session creation and governed finalize to `ifitwala_drive.api.admissions.upload_applicant_document`
- governed classification with `primary_subject_type = Student Applicant`
- resolves/creates `Applicant Document Item` (`item_key`, `item_label`) under parent bucket
- file attachment target forced to `Applicant Document Item`
- writes timeline comments on `Student Applicant` for each upload/replace event (who, when, source, file link)
- materializes `Applicant Review Assignment` rows for matching `Applicant Review Rule` scope/reviewers

Staff review surface rule:
- admissions roles use dual entry points over one workflow contract:
  - Desk `Student Applicant.documents_summary` quick actions remain available
  - Admissions Cockpit document blockers open the applicant workspace with requirement or submitted-file anchors
  - both surfaces read the same server-built requirement/submission readiness payload
- non-admissions reviewers handle `Applicant Document Item` Focus assignments

4. Student Applicant readiness (`has_required_documents`)
- required doc types must exist and be approved
- admissions cockpit consumes the same shared requirement/submission readiness payload instead of re-implementing separate document rules
- approval readiness fails for missing/incomplete required slots unless the requirement has an explicit waiver/exception

5. Applicant document edit timeline (`Applicant Document.on_update`)
- override and promotion-routing changes are comment-audited on `Student Applicant`

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
  - A rejected active item keeps the parent requirement rejected until approvals satisfy the required count.
  - Mixed pending/approved (without enough approved submissions) keeps parent pending.
- Waivers and exceptions:
  - `Waived` and `Exception Approved` satisfy readiness without requiring item approval count.

## Reporting

- No dedicated Script/Query Report currently declares `Applicant Document` as `ref_doctype`.

## Permission Matrix (Effective Runtime)

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `Admission Manager` | Yes | Yes | Yes | Yes | Scoped to applicant visibility; runtime delete guard applies when files exist |
| `Admission Officer` | Yes | Yes | Yes | Yes | Scoped to applicant visibility; reviewer authority |
| `Academic Admin` | Yes | Yes | Yes | Yes | Scoped to applicant visibility; reviewer authority |
| `System Manager` | Yes | Yes | Yes | Yes | Reviewer authority + delete override with attached files |
| `Admissions Applicant` | Yes | Yes | Yes | No | Own applicant rows only (self-link enforced) |
| `Curriculum Coordinator` | No | No | No | No | Not in runtime admissions-file access contract |
| `Academic Assistant` | No | No | No | No | Not in runtime admissions-file access contract |

Runtime controller rules are authoritative over DocType matrix permissions.

## Related Docs

<RelatedDocs
  slugs="student-applicant,applicant-document-type,applicant-health-profile,applicant-interview"
  title="Related Admissions Evidence Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-03-12)

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
  - `requirement_override` options: blank, `Waived`, `Exception Approved`
  - `promotion_target` options: `Student`, `Administrative Record`
- **Routing context contract (`get_file_routing_context`)**:
  - `root_folder = Home/Admissions`
  - `subfolder = Applicant/<student_applicant>/Documents/<doc_type_code>`
  - `file_category = Admissions Applicant Document`
  - `logical_key = <doc_type_code>`
- **Portal/API surfaces**:
  - governed endpoint: `ifitwala_ed/admission/admissions_portal.py::upload_applicant_document`
  - Drive wrapper called by that endpoint: `ifitwala_drive.api.admissions.upload_applicant_document`
  - portal list endpoints: `ifitwala_ed/api/admissions_portal.py::list_applicant_documents`, `list_applicant_document_types`
  - portal upload wrapper: `ifitwala_ed/api/admissions_portal.py::upload_applicant_document`
  - shared readiness helper: `ifitwala_ed/admission/applicant_document_readiness.py`
  - admissions cockpit read endpoint: `ifitwala_ed/api/admission_cockpit.py::get_admissions_cockpit_data`
  - admissions workspace read endpoint: `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py::get_applicant_workspace`
  - admissions workspace action endpoints: `ifitwala_ed/api/admissions_review.py::review_applicant_document_submission`, `set_document_requirement_override`
  - focus review action endpoint: `ifitwala_ed/api/focus.py::submit_applicant_review_assignment`
  - SPA page: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
- **Runtime role guards (controller)**:
  - upload/manage roles: admissions roles + `Academic Admin` + `System Manager` + `Admissions Applicant`
  - reviewer roles: `Admission Officer`, `Admission Manager`, `Academic Admin`, `System Manager`
  - override roles: `Admission Manager`, `Academic Admin`, `System Manager`
  - staff operations are applicant-scope gated (organization/school visibility with transfer-aware student-school matching)
  - `Admissions Applicant` can operate only on own linked applicant rows
  - aggregate review-field mutation is blocked because it is server-derived
- **Readiness and promotion integration**:
  - required-document readiness check in `Student Applicant.has_required_documents()`
  - admissions cockpit document blockers reuse the same readiness payload and open workspace anchors for requirement/submission review
  - explicit requirement overrides satisfy readiness in `Student Applicant.has_required_documents()`
  - promotion copy flow uses approved `Applicant Document Item` submissions in `Student Applicant._copy_promotable_documents_to_student()`
  - `promotion_target` is the active exclusion control for Student copy
  - per-item readiness counting is driven by uploaded submission rows + item review status
