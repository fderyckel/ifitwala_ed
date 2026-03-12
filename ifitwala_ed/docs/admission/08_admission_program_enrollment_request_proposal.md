# Admission to Enrollment Bridge - Runtime Contract (LOCKED)

This note replaces the earlier proposal text.

It now documents the implemented Option A runtime:

`Approved applicant -> offer in admissions portal -> family accepts -> promote to Student -> hydrate real Program Enrollment Request`

## 1. Decision

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_admissions_portal.py`

The admissions-to-enrollment bridge is implemented as a dual-stage model:

1. `Student Applicant` remains the admissions record of truth
2. `Applicant Enrollment Plan` (`AEP`) owns placement planning, offer, and family response
3. the true `Program Enrollment Request` (`PER`) is still student-linked and created only after promotion

## 2. Canonical Lifecycle

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/api/admissions_portal.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_admissions_portal.py`

Canonical runtime flow:

`Inquiry -> Student Applicant -> Applicant Enrollment Plan -> Committee Approved -> Offer Sent -> Offer Accepted -> Promote to Student -> Hydrate Program Enrollment Request -> Review / Validate / Approve -> Program Enrollment -> Identity Upgrade`

Important status boundary:

- `Student Applicant.application_status = Approved` remains the internal applicant decision
- `Offer Sent` / `Offer Accepted` / `Offer Declined` live on `Applicant Enrollment Plan`, not on `Student Applicant`

## 3. Boundary Rules

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

### 3.1 Student Applicant

- pre-student admissions container
- still holds `academic_year`, `term`, `program`, and `program_offering` intent
- does not own offer progression
- applicant user on this doctype is reserved for the student identity

### 3.2 Applicant Enrollment Plan

- pre-student placement / offer bridge
- one active non-terminal plan per applicant
- latest plan governs promotion eligibility
- portal acceptance is authenticated and applicant-scoped only

### 3.3 Program Enrollment Request

- still requires `student`
- still requires `courses`
- still owns validation snapshot and override workflow
- now carries read-only admissions provenance when hydrated from AEP

## 4. Promotion and Hydration Contract

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`, `ifitwala_ed/admission/doctype/admission_settings/admission_settings.json`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

Promotion rules:

- promotion still requires `Student Applicant.application_status = Approved`
- if a latest AEP exists, that latest AEP must be `Offer Accepted` or `Hydrated`
- promotion still does not create committed `Program Enrollment`

Hydration rules:

- hydration happens only after `Student` exists
- hydration creates a draft PER
- hydration is idempotent
- course seeding order is:
  1. explicit planned courses on AEP
  2. required `Program Offering Course` rows
- timing is controlled by `Admission Settings.auto_hydrate_enrollment_request_after_promotion`

## 5. Portal Offer Contract

Status: Implemented
Code refs: `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantStatus.vue`, `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts`
Test refs: `ifitwala_ed/api/test_admissions_portal.py`

Portal behavior:

- offers are shown on `/admissions/status`
- the latest plan is serialized into `enrollment_offer`
- applicant can accept or decline only while status is `Offer Sent`
- repeated accept/decline clicks are safe and return the already-recorded outcome
- declined offers remain visible in the portal after the state becomes terminal

Portal status mapping for approved applicants:

- latest plan `Offer Sent` -> portal status `Offer Sent`
- latest plan `Offer Accepted` -> portal status `Accepted`
- latest plan `Offer Declined` -> portal status `Declined`
- latest plan `Offer Expired` -> portal status `Offer Expired`
- approved applicant with no offer yet -> portal status `In Review`

## 6. Identity Upgrade Clarification

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/docs/admission/04_identity_upgrade.md`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

The applicant portal identity belongs to the student.

Current runtime meaning:

- applicant user is the future student user
- after promotion + active enrollment, the first active `Program Enrollment` can auto-trigger identity upgrade; that same user then loses `Admissions Applicant` and gains `Student`
- guardians are provisioned separately from explicit guardian rows
- the applicant user cannot be reused as a guardian user
- the named `StudentApplicant.upgrade_identity()` action remains the public rerun path when staff need to retry the idempotent access upgrade

## 7. Admissions Hub / Staff Workflow Impact

Status: Partial
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`
Test refs: `None`

Implemented in-product staff path:

- `Student Applicant` Desk form exposes `Manage Enrollment Plan`
- `Applicant Enrollment Plan` Desk form exposes actions for committee-ready, committee-approved, send-offer, hydrate-request

Not yet implemented in cockpit payload/UI:

- dedicated AEP status columns/chips in `Admissions Cockpit`
- explicit cockpit quick actions for send offer / hydrate request

## 8. Contract Matrix

Status: Partial
Code refs: `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantStatus.vue`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_admissions_portal.py`

| Area | Runtime owner | Primary surfaces | State |
| --- | --- | --- | --- |
| AEP schema and status engine | `Applicant Enrollment Plan` controller | Desk AEP form | Implemented |
| Applicant offer acceptance/decline | `ifitwala_ed.api.admissions_portal.*` | `/admissions/status` | Implemented |
| Promotion gate on latest accepted plan | `StudentApplicant.promote_to_student()` | Desk applicant form | Implemented |
| Draft PER hydration | `hydrate_program_enrollment_request_from_applicant_plan()` | Desk applicant form / AEP form | Implemented |
| Automatic identity upgrade trigger | `ProgramEnrollment.on_update()` -> `auto_upgrade_identity_for_student()` | First active `Program Enrollment` transition | Implemented |
| PER provenance fields | `Program Enrollment Request` schema | Desk PER form, downstream audit | Implemented |
| Admissions Cockpit AEP visualization | `ifitwala_ed.api.admission_cockpit`, `AdmissionsCockpit.vue` | `/staff/admissions/cockpit` | Planned |
