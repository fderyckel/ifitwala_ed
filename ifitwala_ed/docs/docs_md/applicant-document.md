---
title: "Applicant Document: Admissions Evidence Owner"
slug: applicant-document
category: Admission
doc_order: 6
version: "1.8.0"
last_change_date: "2026-05-21"
summary: "Manage applicant evidence buckets and per-file submissions for admissions upload, review, readiness, and promotion copy."
seo_title: "Applicant Document: Admissions Evidence Owner"
seo_description: "Use Applicant Document parent buckets and Applicant Document Item file slots for admissions upload, review, readiness, and promotion copy."
---

## What Is an Applicant Document?

`Applicant Document` is the admissions evidence bucket for one applicant and one document type. It is not a random attachment row. It is the record that says, "This applicant needs or has this kind of evidence."

Each uploaded file lives below it as an `Applicant Document Item`. That parent-plus-item model lets Ifitwala Ed review files, count repeatable requirements, apply waivers or exceptions, and copy approved evidence forward during promotion without breaking admissions history.

<Callout type="warning" title="Non-negotiable ownership rule">
Admissions evidence files must attach to Applicant Document Item rows under Applicant Document. Direct evidence attachment to Student Applicant or Student is an architecture bug, except the specific applicant image slot.
</Callout>

## Why This Matters

- **Admissions evidence has one owner.** Files live in a predictable applicant/type bucket.
- **Repeatable evidence works cleanly.** Multiple file items can satisfy one repeatable requirement.
- **Review status is trustworthy.** Parent review status is synchronized from item decisions and explicit overrides.
- **Promotion stays auditable.** Student-side files are new copies; applicant-side evidence remains admissions history.
- **Portal users stay in the right lane.** Applicants and families upload/view evidence, while staff own review decisions.

## Before You Use Applicant Documents

You should have:

- the [**Student Applicant**](/docs/en/student-applicant/) record
- required [**Applicant Document Type**](/docs/en/applicant-document-type/) records with valid scope and classification
- governed upload/classification flows available
- clear staff rules for reviews, waivers, exceptions, and promotion targets

## Information You Manage

| Area | What it controls | Why it matters |
|---|---|---|
| Student Applicant | Applicant who owns the evidence bucket | Keeps evidence scoped to the admissions record |
| Document Type | The evidence requirement or category | Connects files to readiness rules |
| Applicant Document Item | One submitted file slot under the parent bucket | Supports multiple uploads and item-level review |
| Review status | Pending, approved, rejected, or superseded | Shows aggregate requirement state |
| Requirement override | Waived or Exception Approved | Lets authorized staff satisfy requirements without file approval when policy allows |
| Promotion target | Whether approved evidence should copy to Student | Controls promotion copy behavior |
| Timeline comments | Upload, replace, override, and routing audit trail | Makes evidence history explainable |

## How This Fits the Admissions Workflow

<Steps title="Applicant Document evidence flow">
  <Step title="Create or resolve the bucket">
    The system creates or resolves one Applicant Document for each applicant and document type.
  </Step>
  <Step title="Upload evidence">
    Applicants, families, or staff upload through governed admissions endpoints. Each file becomes an Applicant Document Item.
  </Step>
  <Step title="Review submissions">
    Staff review item-level submissions from applicant context, Desk summaries, cockpit workspace, or Focus where applicable.
  </Step>
  <Step title="Sync readiness">
    The parent requirement becomes approved only when enough submitted items are approved, or when an authorized override satisfies the requirement.
  </Step>
  <Step title="Promote safely">
    Promotion copies approved applicant evidence into Student-owned files. It does not relink applicant-side files.
  </Step>
</Steps>

## Permission Matrix

Runtime controller rules are authoritative over DocType matrix permissions. Applicants and families can upload/view their own evidence; staff review and override authority is narrower.

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `Admission Manager` | Yes | Yes | Yes | Yes | Scoped to applicant visibility; runtime delete guard applies when files exist |
| `Admission Officer` | Yes | Yes | Yes | Yes | Scoped to applicant visibility; reviewer authority |
| `Academic Admin` | Yes | Yes | Yes | Yes | Scoped to applicant visibility; reviewer authority |
| `System Manager` | Yes | Yes | Yes | Yes | Reviewer authority + delete override with attached files |
| `Admissions Applicant` | Yes | Yes | Yes | No | Own applicant rows only |
| `Admissions Family` | Yes | Yes | Yes | No | Family workspace only; explicit guardian linkage required |
| `Curriculum Coordinator` | No | No | No | No | Not in runtime admissions-file access contract |
| `Academic Assistant` | No | No | No | No | Not in runtime admissions-file access contract |

## Practical Examples

### Single passport upload

The `passport` document type is non-repeatable. The applicant uploads `passport.pdf`, staff approve the submitted item, and the parent Applicant Document becomes `Approved`.

### Three recommendation letters

The recommendation type is repeatable and requires three approved items. The applicant requirement is not complete until three submitted items are approved or an authorized override satisfies the requirement.

### Requirement waiver

If school policy allows an exception, an Admission Manager, Academic Admin, or System Manager can mark the parent requirement `Waived` or `Exception Approved` with a required reason.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use one canonical row per applicant and document type.</Do>
  <Do>Review submitted items from applicant context so evidence stays connected to the application.</Do>
  <Do>Use explicit waivers or exceptions when policy allows them.</Do>
  <Do>Let promotion copy approved evidence instead of moving original admissions files.</Do>
  <Dont>Attach admissions evidence directly to Student Applicant or Student.</Dont>
  <Dont>Re-link applicant-side File rows to student records during promotion.</Dont>
  <Dont>Let applicants or families edit review fields.</Dont>
</DoDont>

## Common Questions

### Why is there a parent document and item rows?

The parent is the requirement bucket. Item rows are actual submitted files. This lets one requirement have one or many submissions and lets review status sync predictably.

### Can a rejected file block readiness?

Yes. Parent review status is synchronized from active item review states and approved-count requirements.

### Do waivers satisfy readiness?

Yes, explicit `Waived` or `Exception Approved` requirement overrides satisfy readiness without requiring item approval count.

### What happens during promotion?

Approved admissions evidence is copied into Student-owned governed files. Original applicant files remain attached to Applicant Document Item rows.

## Related Docs

<RelatedDocs
  slugs="student-applicant,applicant-document-type,applicant-health-profile,applicant-interview"
  title="Continue With Related Admissions Evidence Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.py`
- **Required fields (`reqd=1`)**:
  - `student_applicant` (`Link` -> `Student Applicant`)
  - `document_type` (`Link` -> `Applicant Document Type`)
- **Lifecycle hooks in controller**: `validate`, `on_update`, `before_delete`
- **Operational/public methods**: `get_file_routing_context`
- **Autoname**: `hash`
- **Per-file slot doctype**: `Applicant Document Item` (`ifitwala_ed/admission/doctype/applicant_document_item/`)

### Parent vs Item Model

| Layer | Doctype | Record cardinality | Responsibility |
|---|---|---|---|
| Catalog | `Applicant Document Type` | many global scoped rows | Defines required/repeatable evidence semantics |
| Applicant bucket | `Applicant Document` | max one per (`student_applicant`, `document_type`) | Requirement card, explicit override policy, promotion routing, aggregate review timeline |
| File slot | `Applicant Document Item` | many per `Applicant Document` | One submitted file (`item_key`, `item_label`, item review status) |

`Applicant Document Item` is a normal DocType, not a child table, with independent permissions and lifecycle hooks.

### Invariants and Field Contract

1. One logical document slot per applicant/type.
2. `student_applicant` and `document_type` are immutable after insert.
3. Every uploaded evidence file is represented by one `Applicant Document Item`; `item_key` is required and unique within the parent document.
4. Parent `Applicant Document.review_status` is synchronized from item review states.
5. Requirement waivers/exceptions are explicit parent-level overrides restricted to `Admission Manager`, `Academic Admin`, and `System Manager`.
6. Applicant-side evidence is retained as admissions history; promotion creates student-side copies.
7. Portal users can upload/view only; they cannot review, retype, or delete records.

Core fields:

- `document_label` optional override label
- `review_status`: `Pending`, `Approved`, `Rejected`, `Superseded`
- `requirement_override`: blank, `Waived`, `Exception Approved`
- `promotion_target`: `Student`, `Administrative Record`

Routing context from `get_file_routing_context`:

- `root_folder = Home/Admissions`
- `subfolder = Applicant/<student_applicant>/Documents/<doc_type_code>`
- `file_category = Admissions Applicant Document`
- `logical_key = <doc_type_code>`

### Validation and Gating

- `Applicant Document.validate` enforces permission guard, terminal-state lock, immutable anchors, uniqueness, server-derived aggregate review fields, requirement override guard, and promotion routing guard.
- `Applicant Document.before_delete` blocks deletion when invalid direct files are attached to Applicant Document; System Manager override exists.
- Portal upload flow checks applicant identity/scope, document type scope/activity, classification contract, parent/item resolution in Ed, Drive upload/finalize delegation, forced file attachment target, timeline comments, and review-assignment materialization.
- Staff review surfaces:
  - Desk `Student Applicant.documents_summary`
  - Admissions Cockpit applicant workspace
  - Focus for non-admissions reviewers handling Applicant Document Item assignments
- Student Applicant readiness fails for missing/incomplete required slots unless explicit waiver/exception exists.
- `Applicant Document.on_update` audits override and promotion-routing changes on Student Applicant.

### Runtime Surfaces and Helpers

- Governed endpoint: `ifitwala_ed/admission/admissions_portal.py::upload_applicant_document`
- Drive wrapper: `ifitwala_drive.api.admissions.upload_applicant_document`
- Portal list endpoints: `ifitwala_ed/api/admissions_portal.py::list_applicant_documents`, `list_applicant_document_types`
- Portal upload wrapper: `ifitwala_ed/api/admissions_portal.py::upload_applicant_document`
- Shared readiness helper: `ifitwala_ed/admission/applicant_document_readiness.py`
- Admissions cockpit read endpoint: `ifitwala_ed/api/admission_cockpit.py::get_admissions_cockpit_data`
- Admissions workspace read endpoint: `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py::get_applicant_workspace`
- Admissions workspace action endpoints: `ifitwala_ed/api/admissions_review.py::review_applicant_document_submission`, `set_document_requirement_override`
- Focus review action endpoint: `ifitwala_ed/api/focus.py::submit_applicant_review_assignment`
- SPA page: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
- Promotion copy flow: `Student Applicant._copy_promotable_documents_to_student()`
