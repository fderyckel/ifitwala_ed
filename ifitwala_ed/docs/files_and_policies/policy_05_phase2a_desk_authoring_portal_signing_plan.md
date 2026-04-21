# Phase 2A Desk-Authored Portal Signing Plan

## Objective
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.js`, `ifitwala_ed/governance/doctype/policy_version/policy_version.js`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/api/student_policy.py`
Test refs: None

Phase 2A delivers desk-authored permission requests and mutable consent for enrolled-student guardian and student workflows, with completion in `/hub/guardian` and `/hub/student`.

Success criteria:

1. Staff can create and publish a request from Desk without leaving canonical back-office workflows.
2. Eligible guardians and eligible students can review and sign from their own portal surfaces.
3. Most displayed fields are reused from known profile data instead of being re-entered manually.
4. When a signer edits contact or address data, the system offers an explicit choice between form-only override and profile write-back.
5. The system records immutable decision history without mutating `Policy Acknowledgement`.
6. Staff can track pending, completed, declined, withdrawn, expired, and overdue outcomes.

## In Scope
Status: Planned
Code refs: `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`
Test refs: None

Rules:

1. Enrolled-student guardian workflows and enrolled-student self-sign workflows ship together in Phase 2A.
2. Authoring starts in Desk on the canonical request form; staff SPA analytics remains monitoring-first.
3. Request types in scope are:
   - one-off permission requests
   - mutable consents
4. Guardian signer eligibility comes only from `Student Guardian.can_consent`.
5. Student self-sign uses the current logged-in student self-context only.
6. Request fields are mostly known field bindings, with limited one-off prompts where canonical data does not exist.
7. Home attention cards and one dedicated request page per portal are part of the initial release.

## Out Of Scope
Status: Planned
Code refs: `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue`
Test refs: None

Rules:

1. Admissions-stage applicant and family workflows.
2. Explicit guardian-and-student co-sign flows that require both actors on the same request.
3. Durable handbook or policy acknowledgements already covered by `Policy Version` and `Policy Acknowledgement`.
4. Generic survey building beyond the approved request/field-binding contract.
5. Payment collection or unrelated portal actions.
6. Auto-generated annual renewal jobs beyond reminder and expiry support.

## Approved Build Slice
Status: Planned
Code refs: `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md`
Test refs: None

Implementation order:

1. Schema and controller layer.
2. Desk authoring and publish flow.
3. Staff dashboard and analytics APIs.
4. Guardian and student read/action APIs.
5. Guardian and student portal surfaces.
6. Reminder and overdue scheduler support.
7. Mutable-consent change and withdrawal flows.
8. Offline paper capture.

## Schema Plan
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.json`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`, `ifitwala_ed/students/doctype/guardian/guardian.py`, `ifitwala_ed/utilities/contact_utils.py`
Test refs: None

DocTypes to add:

1. `Family Consent Request`
2. `Family Consent Target`
3. `Family Consent Field`
4. `Family Consent Decision`

Rules:

1. `Family Consent Request` is the staff-owned parent record and the canonical Desk authoring surface.
2. `Family Consent Target` is the frozen student target list at publish time.
3. `Family Consent Field` defines the reusable known-field bindings and limited one-off prompts shown to signers.
4. `Family Consent Decision` is the immutable event and evidence row for guardian or student responses and later changes.
5. `Family Consent Decision` must never be updated in place to represent a changed answer; later actions create new rows linked by `supersedes_decision`.
6. `Family Consent Request` status lifecycle is:
   - `Draft`
   - `Published`
   - `Closed`
   - `Archived`

## Desk Authoring Plan
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.js`, `ifitwala_ed/governance/doctype/policy_version/policy_version.js`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`
Test refs: None

Rules:

1. Desk is the canonical create/edit/publish surface for Phase 2A requests.
2. The initial authoring entry should be the `Family Consent Request` Desk form, not a new staff SPA page.
3. Desk authoring should guide staff through:
   - template or preset selection
   - audience choice
   - target selection
   - field binding selection
   - due/effective dates
   - publish
4. Known profile bindings should be presented as readable authoring choices rather than raw schema fieldnames.
5. Staff analytics may link to the Desk request record, but analytics is not the primary builder.

## Server Workflow Plan
Status: Planned
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/api/guardian_home.py`
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
6. `get_student_consent_board`
7. `get_student_consent_detail`
8. `submit_student_consent_decision`
9. `withdraw_family_consent_decision`
10. `record_family_consent_paper_decision`

Rules:

1. Publish creates target rows and freezes the field definition in one transaction.
2. Guardian and student submit flows must be idempotent against repeat clicks for the same active state transition.
3. Permission checks must resolve signer authority server-side at action time, not from cached client assumptions.
4. If a signer chooses profile write-back, the server must update canonical `Contact` and linked `Address` data synchronously and mirror dependent guardian contact fields where required.
5. Paper capture must require explicit staff action and provenance fields.
6. Mutable-consent withdrawal must create a new decision row and update derived current state, not delete prior history.

## Guardian And Student Portal Plan
Status: Planned
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentPolicies.vue`
Test refs: None

Surfaces to add or extend:

1. Extend Guardian Home attention cards for pending request actions.
2. Extend Student Home attention cards for pending request actions.
3. Add a dedicated page at `/guardian/consents`.
4. Add a dedicated page at `/student/consents`.
5. Keep `/guardian/policies` and `/student/policies` focused on durable policy acknowledgements only.

UI rules:

1. Dedicated request pages group items into:
   - action needed
   - completed
   - declined or withdrawn
   - expired
2. Student or child names and due dates must be visible without opening every detail view.
3. A guardian without signing authority for a child must not see an actionable button for that child.
4. Student pages must not expose guardian-only requests.
5. The submit flow must explain blocked validation states and profile write-back choices in-product.
6. Mutable consent detail pages must show current state and prior-change history in plain language.

## Staff Dashboard And Analytics Plan
Status: Planned
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`, `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`
Test refs: None

Rules:

1. Staff need one status dashboard for Phase 2A, but authoring still starts in Desk.
2. The dashboard must deep-link to the Desk request record for authoring fixes and to the relevant portal request for preview when appropriate.
3. Minimum filters are:
   - organization
   - school
   - request type
   - status
   - audience
4. Target blockers must remain actionable with direct links to the relevant request or target student.

## Scheduler And Reminder Plan
Status: Planned
Code refs: `ifitwala_ed/api/policy_communication.py`
Test refs: None

Rules:

1. Reminder sweeps must dispatch only published requests with unresolved current state.
2. Overdue logic must be computed from `due_on`, not inferred from age alone.
3. Scheduler work must enqueue chunks and emit processed, skipped, and failed summaries.
4. Reminder jobs must not notify already-completed, declined, withdrawn, or expired targets.

## Analytics Plan
Status: Planned
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`
Test refs: None

Rules:

1. Phase 2A should extend the existing policy-signature analytics direction, not create a parallel analytics style.
2. Derived current state per target student must be computed from the latest non-superseded decision chain.
3. Dashboard counts must support:
   - pending
   - completed
   - declined
   - withdrawn
   - expired
   - overdue
4. Analytics must distinguish guardian and student completion instead of collapsing them into one family count.

## Test Plan
Status: Planned
Code refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`, `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/api/test_users.py`
Test refs: None

Required backend tests:

1. publish request creates frozen target and field rows
2. guardian board only shows signer-authorized targets
3. student board only shows self-authorized targets
4. submit decision is idempotent under repeat click
5. profile write-back updates canonical contact and address ownership correctly
6. decline and withdraw create new decision rows instead of editing old ones
7. expired requests reject new guardian or student actions
8. paper capture is permission-gated and auditable

Required SPA tests:

1. guardian home attention card renders pending consent items
2. student home attention card renders pending consent items
3. `/guardian/consents` renders grouped states correctly
4. `/student/consents` renders grouped states correctly
5. blocked submit shows inline feedback
6. profile update dialog offers form-only versus profile-writeback choice
7. child or student filters do not leak out-of-scope data

## Delivery Sequence
Status: Planned
Code refs: `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md`
Test refs: None

Recommended sequence:

1. Add schema and controller invariants.
2. Add Desk authoring and publish flow.
3. Add staff dashboard APIs.
4. Add guardian and student board, detail, and submit APIs.
5. Add `/guardian/consents`, `/student/consents`, and home-card integration.
6. Add reminder scheduler and analytics extensions.
7. Add withdrawal, profile-writeback, and paper-capture flows.

## Contract Matrix
Status: Planned
Code refs: `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.js`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`, `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/api/test_users.py`

| Layer | Phase 2A owner | Deliverable | Status |
|---|---|---|---|
| Schema / DocType | new family consent request, target, field, and decision docs | immutable decision history plus frozen targets and field bindings | Planned |
| Controller / workflow logic | `family_consent.py` and `family_consent_staff.py` | publish, submit, withdraw, profile write-back, paper capture, derived current state | Planned |
| API endpoints | guardian, student, and staff named workflows | no client-assembled generic CRUD | Planned |
| Desk / portal surfaces | Desk request authoring plus Guardian Home, Student Home, `/guardian/consents`, and `/student/consents` | desk-authored, portal-completed workflow | Planned |
| Reports / dashboards / briefings | staff dashboard plus guardian and student counts | status-aware tracking across both signer audiences | Planned |
| Scheduler / background jobs | reminder and overdue sweeps | idempotent, chunked dispatch | Planned |
| Tests | backend and SPA regression coverage | permission, status, idempotency, profile write-back, expiry, and withdrawal | Planned |
