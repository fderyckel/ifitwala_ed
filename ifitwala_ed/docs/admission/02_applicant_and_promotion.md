# Student Applicant and Promotion - Runtime Contract (LOCKED)

This note replaces the previous mixed source/history document.

It is intentionally limited to the implemented runtime contract for:

- `Student Applicant` lifecycle and editability
- approval readiness
- promotion as the applicant-to-student data boundary

Evidence and review behavior is defined by the implemented contract in `docs/admission/07_applicant_evidence_review_redesign.md`.

## 1. Scope

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/admissions_portal.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_admissions_portal.py`, `ifitwala_ed/api/test_admissions_document_items.py`

The admissions runtime boundary is:

`Inquiry -> Student Applicant -> Applicant Enrollment Plan -> Promotion -> Student -> Program Enrollment Request -> Program Enrollment -> Identity Upgrade`

Authority split:

1. This note defines the current applicant lifecycle and promotion boundary.
2. `docs/admission/03_portal_files_gdpr.md` defines admissions file ownership and GDPR boundary.
3. `docs/admission/04_identity_upgrade.md` defines the post-promotion access boundary.
4. `docs/admission/05_admission_portal.md` defines the applicant SPA surface.
5. `docs/admission/06_recommendation_intake_architecture.md` defines confidential recommendation intake.
6. `docs/admission/08_admission_program_enrollment_request_proposal.md` defines the implemented admissions-to-enrollment bridge.

## 2. Student Applicant

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.json`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/api/admissions_portal.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_admissions_portal.py`

`Student Applicant` is the sole pre-student admissions container.

Current runtime invariants:

- `organization` and `school` are required at creation and are immutable afterward.
- `inquiry` is optional, but once linked it is immutable and may only be set through invite/conversion flows.
- `applicant_contact`, `applicant_email`, `portal_account_email`, and `applicant_user` are server-owned identity fields.
- `student` may only be set during promotion.
- direct file attachment is forbidden except `applicant_image`.
- `applicant_user` is reserved for the future student identity.
- family admissions collaboration is a separate access mode resolved from explicit applicant guardian rows; it does not change the `Student Applicant` data boundary.
- family-facing offer lifecycle is modeled on `Applicant Enrollment Plan`, not on `Student Applicant.application_status`.

Lifecycle and editability are server-owned:

| Status | Family edit | Staff edit | Runtime meaning |
| --- | --- | --- | --- |
| `Draft` | No | Yes | Internal shell before portal invite |
| `Invited` | Yes | Yes | Portal identity opened |
| `In Progress` | Yes | Yes | Applicant can still provide data |
| `Submitted` | No | Yes | Family handoff complete |
| `Under Review` | No | Yes | Staff review window |
| `Missing Info` | Yes | Yes | Applicant corrections requested |
| `Approved` | No | Yes | Promotion allowed |
| `Rejected` | No | No | Terminal |
| `Withdrawn` | No | No | Terminal |
| `Promoted` | No | No | Terminal on admissions side |

Status transitions are only valid through lifecycle methods on `StudentApplicant`; direct status edits are rejected.

## 3. Readiness and Review Inputs

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/applicant_review_workflow.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`, `ifitwala_ed/docs/admission/07_applicant_evidence_review_redesign.md`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

Approval readiness is computed on demand by `StudentApplicant.get_readiness_snapshot()`.

Current blocking inputs:

- profile completeness
- required policy acknowledgements
- required documents
- required recommendations
- health clearance only when `School.require_health_profile_for_approval = 1`

Recommendation blockers are surfaced to applicants as status-only progress. They are not part of the applicant document upload workflow.

Current non-blocking input:

- interviews are tracked and surfaced, but they do not currently gate approval

Current evidence model:

- `Applicant Document` = one applicant/type requirement card
- `Applicant Document Item` = one submitted file under that requirement
- repeatable requirements are satisfied by approved submission count
- waivers / exceptions are explicit policy overrides on the parent requirement card

Current review model:

- `Applicant Review Assignment` can target `Applicant Document Item`
- `Applicant Review Assignment` can target `Applicant Health Profile`
- `Applicant Review Assignment` can target `Student Applicant` for overall advisory review

Parent requirement status is server-derived and is not a human review target.

## 4. Promotion Boundary

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/docs/admission/04_identity_upgrade.md`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

Promotion is the only implemented admissions path that creates or links a `Student`.

Current promotion side-effects also carry forward explicit guardians into `Student.guardians` and seed `Student.siblings` from shared guardians when multiple promoted students belong to the same family.

Runtime preconditions:

- `Student Applicant.application_status = Approved`
- `Student Applicant.student_joining_date` is set
- if the latest `Applicant Enrollment Plan` exists, it must already be `Offer Accepted` or `Hydrated`

Runtime effects:

- create or reuse `Student`
- set `Student.student_applicant`
- copy `Student Applicant.cohort` to `Student.cohort` when present
- copy `Student Applicant.student_house` to `Student.student_house` when present
- copy Applicant Health Profile into `Student Patient`
- copy approved submission-backed admissions evidence into new student-owned governed files
- copy applicant image into the student image slot only when media consent exists
- optionally auto-hydrate a draft `Program Enrollment Request` from the accepted `Applicant Enrollment Plan`
- set `Student Applicant.student`
- transition applicant status to `Promoted`

Explicit non-effects:

- no Guardian or Student role provisioning
- no `Program Enrollment` creation
- no billing or finance setup
- no direct identity upgrade side-effects during promotion

Identity upgrade remains a separate workflow after promotion and active enrollment. The first active `Program Enrollment` can trigger that separate server-owned workflow automatically; promotion itself still stops at the data boundary.

Current runtime nuance:

- promotion copy excludes rows when `promotion_target` is set and not equal to `Student`
- promotion copies from approved `Applicant Document Item` submissions only

## 5. Known Implementation Gaps

Status: Partial
Code refs: `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`
Test refs: `ifitwala_ed/admission/doctype/applicant_interview/test_applicant_interview.py`, `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

The main remaining gaps relevant to this feature area are:

- Recommendation, health, and evidence review still live on adjacent surfaces rather than one unified applicant workspace.
- Interview review, evidence review, and recommendation context share one admissions workspace shell, but health and recommendation actions are still adjacent rather than fully embedded in the same decision panel.

## 6. Contract Matrix

Status: Partial
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/admissions_portal.py`, `ifitwala_ed/admission/applicant_review_workflow.py`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_admissions_portal.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_focus_applicant_review.py`

| Area | Runtime owner | Primary surfaces | Test refs | State |
| --- | --- | --- | --- | --- |
| Applicant lifecycle and status transitions | `StudentApplicant` controller | Desk applicant form, admissions portal status, lifecycle methods | `test_student_applicant.py`, `test_admissions_portal.py` | Implemented |
| Applicant portal identity and editability | `ifitwala_ed.api.admissions_portal.*` | `/admissions` SPA | `test_admissions_portal.py` | Implemented |
| Evidence upload and storage | `ifitwala_ed.admission.admissions_portal.upload_applicant_document` | Portal documents page, governed file dispatcher | `test_admissions_document_items.py` | Implemented |
| Evidence review workflow | `ifitwala_ed.admission.applicant_review_workflow` | Desk `Student Applicant`, admissions cockpit workspace, Focus for non-admissions reviewers, Focus-launched admissions workspace for delegated `Student Applicant` final reviewers | `test_student_applicant.py`, `test_applicant_interview.py`, `test_focus_applicant_review.py` | Implemented |
| Approval readiness | `StudentApplicant.get_readiness_snapshot()` | Desk review snapshot, portal next actions | `test_student_applicant.py` | Implemented |
| Admissions-to-enrollment bridge | `Applicant Enrollment Plan`, `StudentApplicant.promote_to_student()` | Desk applicant action, admissions portal status, post-promotion request hydration | `test_student_applicant.py`, `test_admissions_portal.py` | Implemented |
| Promotion data boundary | `StudentApplicant.promote_to_student()` | Desk action | `test_student_applicant.py` | Implemented |
| Identity upgrade access boundary | `StudentApplicant.upgrade_identity()`, `ProgramEnrollment.on_update()` | Desk action or first active `Program Enrollment` trigger | `test_student_applicant.py`, `test_program_enrollment.py` | Implemented |
