---
title: "Applicant Review Assignment: Materialized Review Work Item"
slug: applicant-review-assignment
category: Admission
doc_order: 9
version: "1.2.1"
last_change_date: "2026-03-09"
summary: "System-generated admissions review work items for evidence submissions, health, and overall application decisions."
seo_title: "Applicant Review Assignment: Materialized Review Work Item"
seo_description: "System-generated admissions review work items for evidence submissions, health, and overall application decisions."
---

## Contract

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.py`, `ifitwala_ed/admission/applicant_review_workflow.py`
Test refs: `ifitwala_ed/admission/doctype/applicant_review_assignment/test_applicant_review_assignment.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

`Applicant Review Assignment` is a system-created work item.

It is not the canonical business record for evidence or health. It is the workflow wrapper that tells a reviewer what needs a decision.

## Targets

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.json`, `ifitwala_ed/admission/applicant_review_workflow.py`
Test refs: `ifitwala_ed/api/test_focus_applicant_review.py`

Each assignment targets exactly one of:

- `Applicant Document Item`
- `Applicant Health Profile`
- `Student Applicant`

`Applicant Document Item` is the only implemented evidence-review target. Parent `Applicant Document` rows are aggregate requirement cards and are not human review targets.

## Lifecycle and Decision Mapping

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.py`, `ifitwala_ed/admission/applicant_review_workflow.py`
Test refs: `ifitwala_ed/admission/doctype/applicant_review_assignment/test_applicant_review_assignment.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

Assignment actor contract:

- exactly one of `assigned_to_user` or `assigned_to_role`
- open-assignment uniqueness is enforced per target + assignee

Lifecycle:

- `Open` -> actionable in Focus
- `Done` -> decision captured
- `Cancelled` -> reserved for cleanup

Decision mapping:

- `Applicant Document Item`: `Approved`, `Needs Follow-Up`, `Rejected`
- `Applicant Health Profile`: `Cleared`, `Needs Follow-Up`
- `Student Applicant`: `Recommend Admit`, `Recommend Waitlist`, `Recommend Reject`, `Needs Follow-Up`

Runtime effects:

- document item target decisions write `Applicant Document Item.review_status` and then resync the parent bucket from items
- health target decisions write `Applicant Health Profile.review_status`
- overall application decisions are advisory and do not mutate `Student Applicant.application_status`

## User Surfaces

Status: Implemented
Code refs: `ifitwala_ed/api/focus_context.py`, `ifitwala_ed/api/focus_listing.py`, `ifitwala_ed/ui-spa/src/components/focus/ApplicantReviewAssignmentAction.vue`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`
Test refs: `ifitwala_ed/api/test_focus_applicant_review.py`

Assignments are primarily consumed through Focus.

Current surface split:

- Focus shows open assignments and supports claim / reassign / submit for non-admissions reviewers, and for Health / Overall Application review work
- admissions roles do not use Focus for `Applicant Document Item` evidence review; they work from applicant context instead
- admissions cockpit applicant workspace and Desk `Student Applicant.documents_summary` are the canonical admissions-staff evidence review surfaces
- Desk `Student Applicant.review_assignments_summary` renders completed Health and Overall Application decisions
- document reviewer truth is rendered in `Student Applicant.documents_summary`, not in the assignment summary table

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.json`, `ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.py`, `ifitwala_ed/admission/applicant_review_workflow.py`
Test refs: `ifitwala_ed/admission/doctype/applicant_review_assignment/test_applicant_review_assignment.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

- Schema supports the three runtime target types listed above.
- Scope fields (`organization`, `school`, `program_offering`) are synced from the linked `Student Applicant`.
- Rule materialization is handled in `applicant_review_workflow.py`, not in the doctype controller.
- Document-item assignment decisions resync parent document state through `sync_applicant_document_review_from_items(...)`.
- Admissions-workspace users are intentionally blocked from `Applicant Document Item` Focus actions so admissions evidence review stays in applicant context.
