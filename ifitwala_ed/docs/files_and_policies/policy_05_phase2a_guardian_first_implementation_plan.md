# Phase 2A Guardian-First Implementation Plan

## Objective
Status: Planned
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
Test refs: None

Phase 2A delivers guardian-first permission requests and mutable consent for enrolled students in `/hub/guardian`.

Success criteria:

1. Staff can publish a guardian-facing request tied to one or more enrolled students.
2. Eligible guardians can review and act on that request in the guardian portal.
3. The system records immutable decision history without mutating `Policy Acknowledgement`.
4. Staff can track pending, completed, declined, withdrawn, expired, and overdue outcomes.

## In Scope
Status: Planned
Code refs: `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
Test refs: None

Rules:

1. Enrolled-student guardian workflows only.
2. Guardian actions only; student co-sign is deferred.
3. Request types:
   - one-off permission requests
   - mutable consents
4. Guardian signer eligibility comes only from `Student Guardian.can_consent`.
5. Home attention cards and one dedicated guardian page are part of the initial release.

## Out Of Scope
Status: Planned
Code refs: `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue`, `ifitwala_ed/ui-spa/src/pages/student`
Test refs: None

Rules:

1. Admissions-stage applicant/family workflows.
2. Student co-sign or student-only decision capture.
3. Durable handbook or policy acknowledgements already covered by `Policy Version` and `Policy Acknowledgement`.
4. Payment collection or unrelated guardian actions.
5. Auto-generated annual renewal jobs beyond simple reminder/expiry support.

## Approved Build Slice
Status: Planned
Code refs: `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md`
Test refs: None

Implementation order:

1. Schema and controller layer.
2. Staff publish and dashboard APIs.
3. Guardian read/action APIs.
4. Guardian portal surfaces.
5. Reminder and overdue scheduler support.
6. Mutable-consent change and withdrawal flows.
7. Offline paper capture.

## Schema Plan
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.json`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
Test refs: None

DocTypes to add:

1. `Family Consent Request`
2. `Family Consent Target`
3. `Family Consent Decision`

Rules:

1. `Family Consent Request` is the staff-owned parent record.
2. `Family Consent Target` is the frozen child target list at publish time.
3. `Family Consent Decision` is the immutable event/evidence row for guardian responses and later changes.
4. `Family Consent Decision` must never be updated in place to represent a changed answer; later actions create new rows linked by `supersedes_decision`.
5. `Family Consent Request` status lifecycle is:
   - `Draft`
   - `Published`
   - `Closed`
   - `Archived`

## Server Workflow Plan
Status: Planned
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/api/guardian_home.py`
Test refs: None

Modules to add:

1. `ifitwala_ed/api/family_consent.py`
2. `ifitwala_ed/api/family_consent_staff.py`

Named workflows:

1. `publish_family_consent_request`
2. `get_family_consent_dashboard`
3. `get_guardian_consent_board`
4. `get_guardian_consent_detail`
5. `submit_guardian_consent_decision`
6. `withdraw_guardian_consent_decision`
7. `record_family_consent_paper_decision`

Rules:

1. Publish creates target rows in one transaction.
2. Guardian submit must be idempotent against repeat clicks for the same active state transition.
3. Permission checks must resolve signer authority server-side at action time, not from cached client assumptions.
4. Paper capture must require explicit staff action and provenance fields.
5. Mutable-consent withdrawal must create a new decision row and update derived current state, not delete prior history.

## Guardian Portal Plan
Status: Planned
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
Test refs: None

Surfaces to add or extend:

1. Extend Guardian Home attention cards for pending consent actions.
2. Add a dedicated page at `/guardian/consents`.
3. Keep `/guardian/policies` focused on durable policy acknowledgements only.

UI rules:

1. The dedicated page groups requests into:
   - action needed
   - completed
   - declined or withdrawn
   - expired
2. Child names and due dates must be visible without opening every detail view.
3. A guardian without signing authority for a child must not see an actionable button for that child.
4. The submit button must always explain blocked validation states.
5. Mutable consent detail pages must show current state and prior-change history in plain language.

## Staff Surface Plan
Status: Planned
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`, `ifitwala_ed/api/admission_cockpit.py`
Test refs: None

Rules:

1. Staff need one author/publish flow and one status dashboard for Phase 2A.
2. Authoring may start in Desk if needed, but launch and follow-up must still be workflow-driven.
3. Dashboard minimum filters are:
   - organization
   - school
   - request type
   - status
4. Target blockers must remain actionable with direct links to the relevant request or target child.

## Scheduler And Reminder Plan
Status: Planned
Code refs: `ifitwala_ed/api/policy_communication.py`
Test refs: None

Rules:

1. Reminder sweeps must dispatch only published requests with unresolved current state.
2. Overdue logic must be computed from `due_on`, not inferred from age alone.
3. Scheduler work must enqueue chunks and emit processed/skipped/failed summaries.
4. Reminder jobs must not notify already-completed, declined, withdrawn, or expired targets.

## Analytics Plan
Status: Planned
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`
Test refs: None

Rules:

1. Phase 2A should extend the existing policy-signature analytics direction, not create a parallel analytics style.
2. Derived current state per target child must be computed from the latest non-superseded decision chain.
3. Dashboard counts must support:
   - pending
   - completed
   - declined
   - withdrawn
   - expired
   - overdue

## Test Plan
Status: Planned
Code refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/api/test_users.py`
Test refs: None

Required backend tests:

1. publish request creates frozen target rows
2. guardian board only shows signer-authorized targets
3. submit decision is idempotent under repeat click
4. decline and withdraw create new decision rows instead of editing old ones
5. expired requests reject new guardian actions
6. paper capture is permission-gated and auditable

Required SPA tests:

1. guardian home attention card renders pending consent items
2. `/guardian/consents` renders grouped states correctly
3. blocked submit shows inline feedback
4. child filter and child badges do not leak out-of-scope data

## Delivery Sequence
Status: Planned
Code refs: `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md`
Test refs: None

Recommended sequence:

1. Add schema and controller invariants.
2. Add staff publish + dashboard APIs.
3. Add guardian board/detail/submit APIs.
4. Add `/guardian/consents` and home-card integration.
5. Add reminder scheduler and analytics extensions.
6. Add withdrawal and paper-capture flows.

## Contract Matrix
Status: Planned
Code refs: `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/api/test_users.py`

| Layer | Phase 2A owner | Deliverable | Status |
|---|---|---|---|
| Schema / DocType | new family consent request/target/decision docs | immutable decision history plus frozen target snapshot | Planned |
| Controller / workflow logic | `family_consent.py` and `family_consent_staff.py` | publish, submit, withdraw, paper capture, derived current state | Planned |
| API endpoints | guardian and staff named workflows | no client-assembled generic CRUD | Planned |
| SPA / UI surfaces | Guardian Home plus `/guardian/consents` | action-first guardian experience | Planned |
| Reports / dashboards / briefings | staff dashboard and guardian counts | status-aware tracking | Planned |
| Scheduler / background jobs | reminder and overdue sweeps | idempotent, chunked dispatch | Planned |
| Tests | backend and SPA regression coverage | permission, status, idempotency, expiry, withdrawal | Planned |
