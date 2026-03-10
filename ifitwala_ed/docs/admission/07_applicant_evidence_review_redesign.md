# Applicant Evidence and Review Contract (LOCKED)

This note is now the canonical evidence contract for admissions.

The filename is historical. The content below reflects the implemented runtime.

## 1. Scope

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.py`, `ifitwala_ed/admission/doctype/applicant_document_item/applicant_document_item.py`, `ifitwala_ed/admission/applicant_review_workflow.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `ifitwala_ed/admission/doctype/applicant_document/test_applicant_document.py`, `ifitwala_ed/admission/doctype/applicant_document_item/test_applicant_document_item.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_focus_applicant_review.py`, `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

This contract defines:

- how admissions evidence is modeled
- which record is reviewable
- how waivers / exceptions are expressed
- which surfaces applicants and staff use

It supersedes the earlier redesign note text that treated this area as only planned.

## 2. Canonical Model

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.json`, `ifitwala_ed/admission/doctype/applicant_document_item/applicant_document_item.json`, `ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.json`, `ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.json`
Test refs: `ifitwala_ed/admission/doctype/applicant_document/test_applicant_document.py`, `ifitwala_ed/admission/doctype/applicant_review_assignment/test_applicant_review_assignment.py`

Canonical meanings:

| Record | Meaning | Human workflow role |
| --- | --- | --- |
| `Applicant Document` | Requirement card for one applicant + one document type | Aggregate only |
| `Applicant Document Item` | One concrete submitted file | Only evidence review target |
| `Applicant Review Assignment` | Review task for one submission, health profile, or overall application | Workflow only |

Hard invariants:

- one `Applicant Document` per (`student_applicant`, `document_type`)
- one or more `Applicant Document Item` rows under that requirement card
- files attach only to `Applicant Document Item`
- evidence review assignments target only `Applicant Document Item`
- parent `Applicant Document.review_status` is server-derived from submission state
- parent `Applicant Document` is not a human review target

## 3. Review and Aggregate State

Status: Implemented
Code refs: `ifitwala_ed/admission/applicant_review_workflow.py`, `ifitwala_ed/admission/doctype/applicant_document/applicant_document.py`, `ifitwala_ed/admission/doctype/applicant_document_item/applicant_document_item.py`
Test refs: `ifitwala_ed/admission/doctype/applicant_document_item/test_applicant_document_item.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

Evidence review decisions are made only on `Applicant Document Item`.

Decision mapping:

- `Approved` -> item `review_status = Approved`
- `Rejected` -> item `review_status = Rejected`
- `Needs Follow-Up` -> item `review_status = Pending`

Parent aggregate behavior:

- if approved submission count meets the requirement count, parent becomes `Approved`
- else if any active submission is `Rejected`, parent becomes `Rejected`
- else parent remains `Pending`

Repeatable types are satisfied by approved submission count, not by a manual parent approval toggle.

## 4. Waiver and Exception Policy

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.json`, `ifitwala_ed/admission/doctype/applicant_document/applicant_document.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`
Test refs: `ifitwala_ed/admission/doctype/applicant_document/test_applicant_document.py`, `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

Schools may allow explicit requirement overrides.

The runtime supports two explicit override states on `Applicant Document`:

- `Waived`
- `Exception Approved`

Rules:

- only `Admission Manager`, `Academic Admin`, or `System Manager` may set or clear them
- `override_reason` is mandatory when applying an override
- `override_by` and `override_on` are server-owned
- overrides satisfy readiness for that requirement without requiring item approval count

This is the only supported waiver / exception path. Ad hoc reviewer edits on submission rows are not the policy mechanism.

## 5. Applicant Portal Surface

Status: Implemented
Code refs: `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/admissions_portal.py`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`, `ifitwala_ed/ui-spa/src/overlays/admissions/ApplicantDocumentUploadOverlay.vue`
Test refs: `ifitwala_ed/api/test_admissions_document_items.py`

The applicant portal is requirement-centric:

- one card per requirement
- applicant-facing states are derived by the server (`Not started`, `Uploaded - waiting for review`, `Changes requested`, `Complete`, waiver / exception complete states)
- file description is optional
- non-repeatable requirements automatically reuse the existing submission slot on replacement
- applicants never need to reason about parent document vs document item

## 6. Staff Surface

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py`, `ifitwala_ed/admission/admission_utils.py`, `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`, `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue`, `ifitwala_ed/ui-spa/src/components/focus/ApplicantReviewAssignmentAction.vue`, `ifitwala_ed/api/focus_listing.py`, `ifitwala_ed/api/focus_context.py`, `ifitwala_ed/api/focus_actions_applicant_review.py`
Test refs: `ifitwala_ed/api/test_focus_applicant_review.py`, `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/admission/doctype/applicant_interview/test_applicant_interview.py`

Staff surface split is now explicit and role-based:

- `Admission Officer`, `Admission Manager`, `Academic Admin`, and `System Manager` review evidence from applicant context only:
  - Desk `Student Applicant.documents_summary`
  - Admissions Cockpit applicant workspace overlay
- submitted recommendation letters now surface a recommendation-specific review action on both of those applicant-centered surfaces so staff can read the referee answers before deciding on the linked `Applicant Document Item`
- non-admissions reviewers continue to use Focus for `Applicant Document Item` assignments
- delegated `Student Applicant` final reviewers stay in Focus for their decision action, but Focus now exposes an `Admissions Workspace` launch so they can inspect the same applicant brief, documents, recommendations, guardians, and interview context without gaining Desk applicant access
- assigned interviewers, including non-admissions staff, use the same `AdmissionsWorkspaceOverlay` from the interview event route so interview prep, applicant brief, evidence, and in-panel feedback stay in one overlay
- admissions-workspace users are intentionally blocked from document-item Focus actions to avoid duplicate mental models
- requirement overrides remain available only to `Admission Manager`, `Academic Admin`, and `System Manager`

Human workflow rule:

- staff think in terms of requirement cards and submitted files
- they do not need to reason about parent `Applicant Document` rows

## 7. Permission and Visibility

Status: Implemented
Code refs: `ifitwala_ed/hooks.py`, `ifitwala_ed/admission/doctype/applicant_document_item/applicant_document_item.py`, `ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.py`, `ifitwala_ed/admission/admission_utils.py`, `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/recommendation_intake.py`, `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py`
Test refs: `ifitwala_ed/admission/doctype/applicant_document_item/test_applicant_document_item.py`, `ifitwala_ed/admission/doctype/applicant_review_assignment/test_applicant_review_assignment.py`

Permission hardening implemented with this contract:

- `Applicant Document Item` now has canonical `permission_query_conditions` and `has_permission`
- applicant self-scope is enforced on item reads/writes
- scoped staff access is enforced on item reads/writes
- `Applicant Review Assignment` now has canonical doctype scope hooks
- raw doctype access no longer depends only on Focus or portal endpoints
- delegated overall-application reviewers get read-only access to applicant workspace payloads, governed file links, and recommendation review payloads for applicants with an open `Student Applicant` review assignment
- this does not widen Desk `Student Applicant` or admissions cockpit permissions for non-admissions staff

## 8. Legacy Retirement

Status: Implemented
Code refs: `ifitwala_ed/admission/applicant_review_workflow.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`, `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py`, `ifitwala_ed/api/focus_listing.py`, `ifitwala_ed/api/focus_context.py`, `ifitwala_ed/api/focus_actions_applicant_review.py`
Test refs: `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

Retired behavior:

- parent-level evidence review targets on `Applicant Review Assignment`
- `Applicant Review Rule.target_type = Applicant Document`
- legacy portal requirement that every new upload include a manual item description
- legacy readiness / portal / promotion reliance on files attached directly to `Applicant Document`
- reviewer-facing `is_promotable` as workflow metadata
- admissions-staff evidence review from Focus for `Applicant Document Item`

The current contract has one canonical evidence path: requirement card -> submission rows -> server-derived aggregate.

## 9. Contract Matrix

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_document/applicant_document.py`, `ifitwala_ed/admission/doctype/applicant_document_item/applicant_document_item.py`, `ifitwala_ed/admission/applicant_review_workflow.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
Test refs: `ifitwala_ed/admission/doctype/applicant_document/test_applicant_document.py`, `ifitwala_ed/admission/doctype/applicant_document_item/test_applicant_document_item.py`, `ifitwala_ed/admission/doctype/applicant_review_assignment/test_applicant_review_assignment.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_focus_applicant_review.py`, `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

| Area | Contract | State |
| --- | --- | --- |
| Schema / DocType | parent = requirement, item = submission, assignment = task | Implemented |
| Controller / workflow logic | submission-only evidence review, aggregate parent sync, explicit override policy | Implemented |
| API endpoints | governed upload, server-owned slot resolution, applicant requirement DTO | Implemented |
| SPA / UI surfaces | applicant requirement cards, admissions workspace overlay with recommendation review pane, Desk applicant evidence summary with recommendation review dialog, Focus for non-admissions reviewers only | Implemented |
| Reports / dashboards / briefings | Desk applicant summary and admissions cockpit workspace both expose the same requirement/submission model | Implemented |
| Scheduler / background jobs | None | Implemented |
| Tests | backend coverage for parent aggregate, item permissions, assignment permissions, applicant docs DTO | Implemented |
