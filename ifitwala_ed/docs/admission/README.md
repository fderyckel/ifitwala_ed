# Admissions Documentation Index

Status: Canonical index
Code refs: `ifitwala_ed/admission/api/`, `ifitwala_ed/api/`
Test refs: `ifitwala_ed/admission/api/test_*.py`, `ifitwala_ed/api/test_*_facade.py`

`ifitwala_ed/docs/admission/` is the canonical home for admissions pipeline rules, applicant runtime behavior, evidence/review modeling, admissions portal boundaries, and the applicant-to-enrollment bridge.

Admissions API implementation modules live under `ifitwala_ed/admission/api/`.
Public Frappe RPC paths remain under `ifitwala_ed.api.*` unless an explicit endpoint contract migration is approved.
Admissions API implementation tests live with the admission API implementation; root API tests should cover only facade delegation, payload binding, and public compatibility.

Read in this order for current runtime:

- `01_governance.md`
  admissions pipeline boundary and top-level authority split
- `02_applicant_and_promotion.md`
  applicant lifecycle, readiness, and promotion contract
- `07_applicant_evidence_review_redesign.md`
  canonical evidence and review model
- `05_admission_portal.md`
  admissions portal runtime contract
- `04_identity_upgrade.md`
  post-promotion access boundary
- `06_recommendation_intake_architecture.md`
  confidential recommendation intake flow
- `08_admission_program_enrollment_request_proposal.md`
  implemented applicant-to-enrollment bridge despite the historical filename

Partial / planned target contracts:

- `11_admissions_crm_contract.md`
  Inquiry dynamic capture, public family acknowledgement, CRM DocTypes, manual intake, Admissions Inbox backend/actions, admission visits, the backend contextual Admissions Timeline endpoint, Inbox/Cockpit timeline drawers, Cockpit CRM log activity/message drawer actions, Inbox/Cockpit applicant-stage offer/deposit/promotion drawer actions, Inbox/Cockpit schedule-visit drawer actions, and Inquiry/Student Applicant Desk entry points are partially implemented; provider adapters, governed media conversion, education-wide Relationship CRM, and lead-scoring/read-model work remain planned until implemented
- `12_admission_visit_contract.md`
  admissions visit workflow for pre-applicant and applicant-stage tours, including CRM linkage and participant-only calendar projection
- `13_admission_api_maintainability_plan.md`
  proposal for splitting large admissions API and admissions test files after ownership moves are complete

Supporting current-state notes:

- `03_portal_files_gdpr.md`
  portal surface, file, and GDPR constraints
- `10_ifitwala_drive_portal_uploads.md`
  Drive integration layering for admissions uploads

Non-authoritative planning note:

- `09_family_admissions_workspace_proposal.md`
  future-facing proposal only; do not treat as current runtime authority
