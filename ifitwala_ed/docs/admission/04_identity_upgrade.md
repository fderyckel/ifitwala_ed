# Identity Upgrade — Access Boundary Contract (LOCKED)

## 1. Purpose

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

Define the post-promotion access upgrade boundary as a separate workflow from admissions promotion.

## 2. Boundary Model

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`, `ifitwala_ed/docs/admission/02_applicant_and_promotion.md`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`

1. Promotion (data boundary)
   - Converts `Student Applicant` -> `Student`
   - Syncs `Student Patient`
   - Copies approved/promotable admissions files
   - May auto-hydrate a draft `Program Enrollment Request` from an accepted `Applicant Enrollment Plan`
   - Does not provision `Student` / `Guardian` roles

2. Identity Upgrade (access boundary)
   - Runs only after promotion and active enrollment
   - Enrollment confirmation signal: active `Program Enrollment` (`archived = 0`) for the promoted student
   - Public rerun surface remains the named `Student Applicant` action, but the first active `Program Enrollment` insert or reactivation can trigger the same server-owned logic automatically
   - Removes `Admissions Applicant` from the applicant user and provisions the student-facing role set
   - Provisions guardian access only from explicit guardian rows
   - Re-runs sibling sync from shared explicit guardians after guardian carryover

## 3. Canonical Entry Point

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`

- Public server method: `StudentApplicant.upgrade_identity()`
- Internal auto-trigger path: `ProgramEnrollment.on_update()` -> `auto_upgrade_identity_for_student()`
- Trigger surfaces:
  - explicit Desk action on promoted applicants
  - first active `Program Enrollment` transition for that promoted student (new active insert or `archived: 1 -> 0`)

## 4. Preconditions

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

- `Student Applicant.application_status = Promoted`
- `Student Applicant.student` is set
- At least one active `Program Enrollment` exists for that student
- If guardian access should be provisioned, guardian identity inputs must exist in explicit applicant guardian rows

## 5. Effects

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

- Ensure the applicant user becomes the `Student` access identity
- Remove `Admissions Applicant` from that applicant user
- Create/reuse `Guardian` records from applicant guardian rows when present
- Ensure each guardian is linked to its own `User`
- Reject any attempt to reuse the applicant user as a guardian user
- Link Guardian <-> Student in `Student.guardians`
- Sync `Student.siblings` from shared explicit guardians carried over from admissions
- Link tracked guardian `Contact` rows to `Student Applicant`, `Guardian`, and promoted `Student`
- When an explicit applicant guardian row carries a photo, materialize a Guardian-owned governed `profile_image` source and canonical compact/card/richer preview variants for portal/avatar use

## 6. Explicit Non-Effects

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

- Does not change admissions lifecycle state
- Does not create/modify admissions evidence documents
- Does not re-run promotion data copy
- Does not manufacture a guardian from `applicant_contact`

## 7. Idempotency Requirements

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

Re-running identity upgrade must not:

- duplicate `Guardian` rows for the same email identity
- duplicate `Student.guardians` link rows
- duplicate role rows on a user

## 8. Audit Requirements

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`

Identity upgrade records:

- actor
- timestamp
- lifecycle boundary crossed (`Promoted -> Identity Upgraded`)
- student id
- guardian links added
- users updated
- trigger detail when the automatic enrollment trigger is the initiating surface

## 9. Failure Behavior

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`

- Enrollment gate failure hard-stops with explicit error
- Guardian-user collision with applicant user hard-stops with explicit error
- Partial access provisioning is forbidden

## 10. Contract Matrix

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`

| Area | Runtime owner | Surface | State |
| --- | --- | --- | --- |
| Enrollment gate | `StudentApplicant._require_active_enrollment()` | Desk upgrade action and automatic enrollment trigger | Implemented |
| Automatic trigger | `ProgramEnrollment.on_update()` and `auto_upgrade_identity_for_student()` | First active `Program Enrollment` insert or reactivation | Implemented |
| Student identity provisioning | `StudentApplicant._ensure_student_user_access()` | Desk upgrade action and automatic enrollment trigger | Implemented |
| Guardian provisioning | `StudentApplicant._resolve_upgrade_guardians()` and related helpers | Desk upgrade action and automatic enrollment trigger | Implemented |
| Applicant-role removal | `StudentApplicant._ensure_user_roles()` | Desk upgrade action and automatic enrollment trigger | Implemented |
