# Identity Upgrade — Access Boundary Contract (LOCKED)

## Purpose

Define the post-promotion access upgrade boundary as a separate workflow from admissions promotion.

## Boundary Model

1. Promotion (data boundary)
- Converts `Student Applicant` -> `Student`
- Syncs `Student Patient`
- Copies approved/promotable documents
- Does not provision Guardian/Student access roles

2. Identity Upgrade (access boundary)
- Runs only after enrollment confirmation
- Enrollment confirmation signal: active `Program Enrollment` (`archived = 0`) for the promoted student
- Provisions portal identities and role transitions

## Canonical Entry Point

- Server method: `StudentApplicant.upgrade_identity()`
- Trigger surface: explicit Desk action on promoted applicants

## Preconditions

- `Student Applicant.application_status = Promoted`
- `Student Applicant.student` is set
- At least one active `Program Enrollment` exists for that student
- Guardian identity inputs are resolvable (explicit applicant guardians or applicant contact fallback with required phone+email)

## Effects

- Create/reuse `Guardian` records as needed
- Ensure each guardian is linked to a `User`
- Remove `Admissions Applicant` role and assign `Guardian` role for guardian identities
- Ensure Student portal identity exists and has `Student` role
- Link Guardian <-> Student in `Student.guardians` child rows

## Explicit Non-Effects

- Does not change admissions lifecycle state
- Does not create/modify admissions evidence documents
- Does not re-run promotion data copy

## Idempotency Requirements

Re-running identity upgrade must not:

- duplicate `Guardian` rows for the same email identity
- duplicate `Student.guardians` link rows
- duplicate role rows on a user

## Audit Requirements

Identity upgrade must record:

- actor
- timestamp
- lifecycle boundary crossed (`Promoted -> Identity Upgraded`)
- student id
- guardian links added
- users updated

## Failure Behavior

- Enrollment gate failure must hard-stop with explicit user-facing error
- Missing guardian prerequisites must hard-stop with explicit user-facing error
- Partial access provisioning is forbidden
