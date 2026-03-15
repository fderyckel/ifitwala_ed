# Family Signature And Consent Contract

## Purpose And Scope
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.py`, `ifitwala_ed/governance/doctype/policy_version/policy_version.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/guardian_policy.py`
Test refs: None

This document is the canonical Phase-2 contract for family-facing signatures, permission slips, and mutable consents.

Rules:

1. Phase 2 extends the existing policy-signature foundation; it does not replace it.
2. The feature must support three family-facing document patterns:
   - durable policy or handbook acknowledgement
   - one-off permission request tied to an event or activity
   - mutable consent that may later be changed or withdrawn
3. The product contract is portal-first:
   - `/admissions` for applicant-stage family work
   - `/hub/guardian` for guardian-stage work
   - `/hub/student` when student action is explicitly required
4. Staff workflows must remain named workflows with server-owned state transitions, not client-assembled CRUD.
5. Phase 2A delivery order is defined in `ifitwala_ed/docs/files_and_policies/policy_05_phase2a_guardian_first_implementation_plan.md`.

## Reuse Model
Status: Planned
Code refs: `ifitwala_ed/governance/policy_utils.py`, `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/doctype/policy_version/policy_version.json`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.json`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/api/policy_signature.py`
Test refs: `ifitwala_ed/governance/doctype/policy_version/test_policy_version.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/test_policy_acknowledgement.py`, `ifitwala_ed/api/test_policy_signature.py`

Rules:

1. `Institutional Policy` remains the semantic root for durable institution-owned policies.
2. `Policy Version` remains the legal text snapshot for versioned policy content.
3. `Policy Acknowledgement` remains immutable receipt evidence and must not be overloaded to represent mutable yes/no/withdraw decisions.
4. `Org Communication` remains the delivery rail for notifications, reminders, and briefing links.
5. Staff policy analytics patterns are reused for dashboarding, but Phase 2 must add family-oriented decision statuses beyond signed/not-signed.

## Capability Modes
Status: Planned
Code refs: `ifitwala_ed/governance/policy_utils.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/guardian_policy.py`
Test refs: `ifitwala_ed/api/test_admissions_portal.py`, `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. `Versioned acknowledgement` is used for handbook, code-of-conduct, acceptable-use, and other durable institution rules.
2. `One-off permission request` is used for field trips, event approvals, special-program participation, and similar operational requests tied to a specific occurrence or window.
3. `Mutable consent` is used for permissions that can be explicitly granted, denied, and later changed, such as media consent or recurring participation consent.
4. `Co-sign requirement` is used only when the workflow explicitly requires both a student action and a guardian action.
5. A single family-facing label may group these modes in the UI, but server logic must keep them distinct because their legal and operational semantics differ.

## Signer Authority Contract
Status: Partial
Code refs: `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`, `ifitwala_ed/admission/access.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Guardian signing authority is owned by relationship rows, not by guardian identity alone.
2. Applicant-stage signing authority comes from `Student Applicant Guardian.can_consent`.
3. Enrolled-student-stage signing authority comes from `Student Guardian.can_consent`.
4. More than one guardian may have signing authority for the same child or family.
5. Emergency-only or temporary-care guardians may remain linked without signing authority.
6. `is_primary`, `is_primary_guardian`, and `is_financial_guardian` must never imply document-signing authority.
7. Every Phase-2 workflow must declare whether completion means:
   - any authorized signer may complete it once, or
   - all required signers must complete it
8. Student signature authority is never inferred from guardian authority; if a student signature is required, the workflow must state it explicitly.

## Family UX Contract
Status: Planned
Code refs: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: None

Rules:

1. Required signatures and consents must surface where families already work:
   - home/landing attention cards
   - a dedicated details page
   - direct links from communications
2. The UX must be family-first, but correctness remains child-scoped when the request applies per child.
3. One UI action may batch siblings, but the server must record child-level outcomes separately.
4. A blocked action must explain why it is blocked; silent non-action is a defect.
5. A guardian who can view a child in the portal but cannot sign for that child must not be presented as an eligible signer.
6. One-off requests and mutable consents must not be hidden inside the current policy page without explicit mode labeling.

## Decision Lifecycle Contract
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/policy_signature.py`
Test refs: None

Rules:

1. Every Phase-2 workflow starts from an explicit request published by staff, not from an implied missing row.
2. Durable policy updates create a new required action instead of mutating prior evidence.
3. One-off requests must preserve the decision history after completion; reopening must be explicit and auditable.
4. Mutable consent must support later change or withdrawal without deleting prior evidence.
5. Offline paper capture may be recorded as staff-entered evidence, but staff must never impersonate a guardian or student electronic signature.
6. Expiry, withdrawal, decline, and supersession are first-class outcomes in this feature and must not be collapsed into "not signed."

## Communication And Reminder Contract
Status: Planned
Code refs: `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/api/org_communication_interactions.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`
Test refs: None

Rules:

1. Initial request publication must be capable of creating an in-product communication, not only a back-office record.
2. Families must receive a direct next action from communications, not a generic FYI message.
3. Reminder sends must be idempotent and status-aware so already-completed requests are not re-notified.
4. Overdue and upcoming items must be distinguishable in both family and staff views.
5. Communications for one-off requests and mutable consents must reuse existing org communication audience and read-state patterns where possible.

## Analytics And Dashboard Contract
Status: Planned
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`, `ifitwala_ed/api/admission_cockpit.py`
Test refs: None

Rules:

1. Staff dashboards must report more than signed/not-signed once Phase 2 ships.
2. Minimum reporting dimensions are:
   - organization
   - school
   - audience mode
   - request type
   - current status
3. Minimum outcome statuses for analytics are:
   - pending
   - completed
   - declined
   - withdrawn
   - expired
   - overdue
4. Analytics visibility must reuse canonical server-side permission predicates and must not implement separate scope math.
5. Family-facing counts must stay action-oriented and avoid legal or operational jargon where simpler wording exists.

## Edge-Case Rules
Status: Planned
Code refs: `ifitwala_ed/governance/policy_utils.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`
Test refs: None

Rules:

1. A sibling batch action in the UI must still persist one outcome per child when the request is child-specific.
2. Losing signing authority after launch must affect future actions immediately; stale UI assumptions are not enough.
3. Changing policy text after acceptance must create a new versioned requirement, not edit prior text.
4. Mutable consent must preserve the prior state history when a family changes from yes to no or no to yes.
5. A child becoming inactive or leaving the school must stop future reminders without destroying past evidence.
6. Co-sign flows must track guardian completion and student completion separately.
7. A guardian linked by email only is not a signer unless a relationship row grants authority.

## Approved Architecture Decisions
Status: Partial
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.json`, `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
Test refs: None

Approved decisions:

1. The new request/decision layer will use these DocTypes:
   - `Family Consent Request`
   - `Family Consent Target`
   - `Family Consent Decision`
2. Phase 2A ships guardian-first on enrolled-student guardian workflows in `/hub/guardian`.
3. Student co-sign is deferred to a later phase and must not block guardian-first release.
4. Default completion rule is `Any Authorized Guardian`; requests may opt into `All Authorized Guardians`.
5. Mutable consents must carry explicit effective-window fields and use renewal by new request, not silent rollover.
6. Offline paper capture lives on the same workflow artifact as a staff-recorded `Family Consent Decision`, with governed file evidence attached to that decision.

Approved field set for the new request/decision layer:

1. `Family Consent Request`
   - `request_title`
   - `request_key`
   - `request_type`
   - `policy_version`
   - `organization`
   - `school`
   - `request_text`
   - `source_file`
   - `subject_scope`
   - `audience_mode`
   - `signer_rule`
   - `decision_mode`
   - `requires_typed_signature`
   - `requires_attestation`
   - `effective_from`
   - `effective_to`
   - `due_on`
   - `status`
   - child table `targets`
2. `Family Consent Target`
   - `student`
3. `Family Consent Decision`
   - `family_consent_request`
   - `student`
   - `decision_by`
   - `decision_status`
   - `decision_at`
   - `typed_signature_name`
   - `attestation_confirmed`
   - `source_channel`
   - `source_file`
   - `supersedes_decision`

## Decision Rationale
Status: Partial
Code refs: `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
Test refs: None

Pros:

1. Keeps immutable `Policy Acknowledgement` semantics intact instead of overloading them with mutable states.
2. Delivers the highest-value family workflow first: guardian-facing permission requests and consents in `/hub/guardian`.
3. Preserves the signer-authority model already established by `can_consent`.
4. Supports later student co-sign without forcing student-specific complexity into Phase 2A.
5. Makes reminders, expiry, and withdrawal explicit instead of encoding them as absence of acknowledgement.

Cons:

1. Introduces a second governance workflow family beside versioned policy acknowledgements.
2. Requires new staff publishing and analytics surfaces rather than only extending the current policy page.
3. Guardian-first release means applicant-stage and student co-sign use cases remain out of scope initially.

Blind spots:

1. The exact staff authoring UX for target selection still needs implementation design.
2. Renewal cadence defaults for annual consents are not yet wired and will depend on school operations.
3. Later admissions-stage reuse may require extending targets beyond enrolled students.

Risks:

1. If request types and decision modes are blurred in UI, families may not understand whether they are acknowledging, approving, or granting consent.
2. If signer authority is not enforced uniformly server-side, emergency-only guardians could be exposed to actions they must not take.
3. If staff dashboards reuse custom scope math instead of canonical helpers, permission drift will reappear.

## Contract Matrix
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/doctype/policy_version/policy_version.json`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.json`, `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`
Test refs: `ifitwala_ed/api/test_admissions_portal.py`, `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_policy_signature.py`

| Layer | Current canonical owner | Phase-2 extension | Status |
|---|---|---|---|
| Schema / DocType | `Institutional Policy`, `Policy Version`, `Policy Acknowledgement`, applicant/student guardian relationship rows | Add one approved request/decision layer without changing the meaning of immutable acknowledgement evidence | Planned |
| Controller / workflow logic | `policy_utils`, admissions policy acknowledgement, guardian policy overview, policy acknowledgement permission checks | Add named workflows for request creation, family decision capture, change/withdraw, reminder safety, and offline evidence capture | Planned |
| API endpoints | `acknowledge_policy`, `get_guardian_policy_overview`, staff policy communication and signature APIs | Add named family request endpoints instead of assembling generic CRUD from the client | Planned |
| SPA / UI surfaces | Admissions policies page, guardian policies page, guardian home, staff policy analytics | Add family action cards, dedicated request pages, and explicit request-mode UI for one-off and mutable decisions | Planned |
| Reports / dashboards / briefings | Staff policy signature analytics and current portal counts | Extend to request-type and decision-status analytics for family workflows | Planned |
| Scheduler / background jobs | Existing policy communication and staff reminder patterns only | Add reminder and overdue sweeps with idempotent, status-aware dispatch | Planned |
| Tests | Existing admissions, guardian-policy, and staff policy signature coverage | Add end-to-end coverage for request creation, decision capture, withdrawal, expiry, and permission enforcement | Planned |
