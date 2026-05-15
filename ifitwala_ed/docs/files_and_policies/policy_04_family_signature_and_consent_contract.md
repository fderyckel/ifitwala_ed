# Family Signature And Consent Contract

## Purpose And Scope
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.py`, `ifitwala_ed/governance/doctype/policy_version/policy_version.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/guardian_policy.py`
Test refs: None

This document is the canonical Phase-2 contract for desk-authored, portal-completed family and student signatures, permission slips, and mutable consents.

Rules:

1. Phase 2 extends the existing policy-signature foundation; it does not replace it.
2. The feature must support three family-facing document patterns:
   - durable policy or handbook acknowledgement
   - one-off permission request tied to an event or activity
   - mutable consent that may later be changed or withdrawn
3. The product contract is desk-authored and portal-completed:
   - Desk for staff authoring, targeting, and publication
   - `/admissions` for applicant-stage family work
   - `/hub/guardian` for guardian-stage work
   - `/hub/student` for student-stage work, including adult-student self-sign
4. Staff monitoring and analytics for this feature live in staff Vue analytics pages, not in Desk reporting widgets.
5. Staff workflows must remain named workflows with server-owned state transitions, not client-assembled CRUD.
6. Phase 2A delivery order is defined in `ifitwala_ed/docs/files_and_policies/policy_05_phase2a_desk_authoring_portal_signing_plan.md`.

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

## Staff Authoring Contract
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.js`, `ifitwala_ed/governance/doctype/policy_version/policy_version.js`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`
Test refs: None

Rules:

1. Staff authoring starts in Desk, not in the staff SPA analytics surface.
2. The initial authoring entry point should be the canonical `Family Consent Request` Desk form, with Desk-native helpers for template selection, targeting, and publication.
3. Staff analytics lives in staff Vue pages as the monitoring and reminder surface; it must not become the primary request builder.
4. Most form fields must be selected from known, server-owned profile bindings instead of being typed freehand for every request.
5. Free-text prompts are allowed only when no canonical profile field exists or when the request genuinely needs a one-off operational answer.
6. Staff authoring should start from institution-owned presets such as field trip, event approval, media consent, internship approval, or emergency-contact confirmation rather than a blank technical schema.

## Signer Authority Contract
Status: Partial
Code refs: `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`, `ifitwala_ed/admission/access.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Guardian signing authority is owned by relationship rows, not by guardian identity alone.
2. Applicant-stage signing authority comes from `Student Applicant Guardian.is_primary_guardian`; applicant signer authority must only be granted to rows marked primary.
3. Enrolled-student-stage signing authority comes from `Student Guardian.can_consent`, and that enrolled signer flag must be reserved for guardians who are primary guardians.
4. Only guardian rows marked primary may have family-facing signing authority for the same child or family.
5. Emergency-only or temporary-care guardians may remain linked without signing authority.
6. `is_primary` and `is_financial_guardian` must never imply document-signing authority. `is_primary_guardian` is the source rule for family-facing signer authority, while enrolled runtime permission continues to enforce the derived `Student Guardian.can_consent` flag.
7. Every Phase-2 workflow must declare whether completion means:
   - any authorized signer may complete it once, or
   - all required signers must complete it
8. Student signature authority is never inferred from guardian authority; if a student signature is required, the workflow must state it explicitly.
9. Enrolled adult students must be able to self-sign on day one wherever the request audience is `Student`.

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
7. Guardian and student request pages should feel like sibling portal surfaces, with the same evidence, status, and blocked-submit patterns.
8. If a request is configured as `Paper Only`, the family portal may show the request and its status, but it must not offer an electronic submit action.
9. `Portal Or Paper` requests must make it clear that electronic completion is available but paper return remains acceptable.

## Field Binding And Profile Reuse Contract
Status: Planned
Code refs: `ifitwala_ed/students/doctype/guardian/guardian.py`, `ifitwala_ed/utilities/contact_utils.py`, `ifitwala_ed/students/doctype/student/student.py`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
Test refs: None

Rules:

1. Request fields should default to known bindings from `Student`, `Guardian`, `Student Guardian`, linked `Contact`, and linked `Address` data before introducing free-text entry.
2. Phase 2A exposes a server-owned binding registry for the initial portal slice:
   - `Student.student_full_name`
   - `Student.student_email`
   - `Student.student_mobile_number`
   - `Student.anchor_school`
   - `Guardian.guardian_full_name`
   - `Guardian.guardian_email`
   - `Guardian.guardian_mobile_phone`
   - `Student.primary_address`
   - `Guardian.primary_address`
3. `Student.primary_address` and `Guardian.primary_address` resolve only when the server can identify exactly one canonical linked `Address` row for that signer context; otherwise the field may still be shown or edited for form-only use, but profile write-back must stay disabled until Desk authoring or linked-address ownership is clarified.
4. `Student.student_email` may be shown and captured on the form, but Phase 2A portal submit keeps profile write-back disabled for that binding until student portal identity is no longer keyed directly from `Student.student_email`.
5. `Address` field payloads use a structured value with:
   - `address_line1`
   - `address_line2`
   - `city`
   - `state`
   - `country`
   - `pincode`
6. Bound fields must declare one of three modes:
   - display only
   - confirm current
   - allow override
7. If a signer edits bound phone, email, or address data, the portal must ask whether the change is:
   - for this form only
   - the new profile data everywhere
8. `Update my profile everywhere` is an explicit self-service choice, not a silent background mutation and not a deferred review task in the default contract.
9. Profile write-back must update the canonical linked `Contact` and `Address` records, then mirror convenience fields such as `Guardian.guardian_email`, `Guardian.guardian_mobile_phone`, `Student.student_email`, and `Student.student_mobile_number` where the runtime model depends on them.
10. Form-only overrides must never silently mutate master profile data.
11. Every submitted decision must retain an immutable snapshot of the presented values, submitted values, and chosen write-back mode.

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
7. If a signer chooses profile write-back during submit, the workflow must record enough before/after evidence to audit what changed.
8. Requests may declare that completion is accepted through portal submit, paper collection, or either channel, and that choice must be enforced server-side.

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
6. Communications may deep-link into guardian or student request pages, but the Desk authoring form remains the canonical staff edit surface.

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
   - completion channel mode
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
6. Staff analytics for this feature belongs in Vue staff pages under the staff portal shell, while Desk remains the authoring and edit surface.

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
8. Editing a bound address or phone value for one request must not silently overwrite sibling or guardian records unless the signer explicitly chose profile write-back.
9. `Paper Only` requests must reject guardian or student portal submit attempts even if a stale client still shows an action button.

## Approved Architecture Decisions
Status: Partial
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.json`, `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
Test refs: None

Approved decisions:

1. The new request/decision layer will use these DocTypes:
   - `Family Consent Request`
   - `Family Consent Target`
   - `Family Consent Field`
   - `Family Consent Decision`
2. The product label is `Forms & Signatures`; the backend request/decision layer may keep the `Family Consent*` names.
3. Phase 2A ships desk-authored enrolled-student workflows with guardian signing and student self-sign available on day one.
4. Student self-sign does not require guardian-first rollout and must be modeled as a first-class audience from the start.
5. Default completion rule is `Any Authorized Guardian` for guardian-only requests and `Student Self` for student-only requests; requests may opt into `All Authorized Guardians` or explicit co-sign later.
6. Student co-sign that requires both guardian and student remains a later slice and must not block day-one student self-sign.
7. Mutable consents must carry explicit effective-window fields and use renewal by new request, not silent rollover.
8. Offline paper capture lives on the same workflow artifact as a staff-recorded `Family Consent Decision`, with governed file evidence attached to that decision.
9. Desk is the canonical authoring home; the staff analytics page remains tracking, reminder, and launch support rather than the primary builder.
10. Staff monitoring, reminder follow-up, and completion analytics for this feature live in Vue staff pages rather than Desk.
11. Most collected form content must be field-bound to known profile data, with explicit signer choice for profile write-back when edits are made.

## Exact DocType Schema Contract
Status: Planned
Code refs: `ifitwala_ed/students/doctype/guardian/guardian.py`, `ifitwala_ed/students/doctype/student/student.py`, `ifitwala_ed/utilities/contact_utils.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`
Test refs: None

Frappe child-table bookkeeping fields (`parent`, `parenttype`, `parentfield`, `idx`) are implied and not repeated below. The tables below list business fields only.

### `Family Consent Request`

| Field | Contract | Required | Notes |
|---|---|---|---|
| `request_title` | human-readable request title | Yes | Staff-facing and family-facing title |
| `request_key` | immutable unique request key | Yes | Server-generated; used for portal routing and deep links |
| `template_key` | preset/template identifier | No | Stable preset key such as field trip or media consent |
| `request_type` | request family | Yes | See enum contract |
| `policy_version` | link to `Policy Version` | No | Allowed only when the request is seeded from policy-library content; it does not convert this workflow into durable acknowledgement |
| `organization` | link to `Organization` | Yes | Top tenant scope for the request |
| `school` | link to `School` | No | Blank only when a request legitimately spans multiple schools inside the selected organization scope |
| `request_text` | sanitized rich-text body shown to signers | Yes | Canonical explanatory text and any legal wording for the form |
| `source_file` | governed source attachment | No | Must follow the governed attachment contract; no raw URL storage in API DTOs |
| `subject_scope` | target-scope selector | Yes | Phase 2A supports `Per Student` only |
| `audience_mode` | audience selector | Yes | Guardian, Student, or later guardian-and-student |
| `signer_rule` | completion rule | Yes | Values constrained by `audience_mode` |
| `decision_mode` | decision semantics | Yes | Distinguishes approval vs consent semantics |
| `completion_channel_mode` | accepted completion channels | Yes | Portal Only, Portal Or Paper, or Paper Only |
| `requires_typed_signature` | typed-signature requirement flag | Yes | Default on for legal-signature flows |
| `requires_attestation` | electronic-signature attestation requirement flag | Yes | Default on for legal-signature flows |
| `effective_from` | effective start date | No | Primarily used by mutable consent |
| `effective_to` | effective end date | No | Primarily used by mutable consent |
| `due_on` | due date | No | Drives overdue state and reminders |
| `status` | request lifecycle status | Yes | Draft, Published, Closed, Archived |
| `targets` | child table of `Family Consent Target` | Yes before publish | Frozen publish-time target set |
| `fields` | child table of `Family Consent Field` | Yes before publish | Ordered field/binding definition shown to signers |

### `Family Consent Target`

| Field | Contract | Required | Notes |
|---|---|---|---|
| `organization` | frozen organization scope for the target student | Yes | Supports scoped analytics without rereading student hierarchy on every row |
| `school` | frozen school scope for the target student | Yes | Supports staff filters and descendant-scope summaries |
| `student` | link to `Student` | Yes | Canonical target subject for Phase 2A |

### `Family Consent Field`

| Field | Contract | Required | Notes |
|---|---|---|---|
| `field_key` | immutable stable response key | Yes | Used in snapshots and submit payloads; does not change after publish |
| `field_label` | signer-facing label | Yes | Friendly label shown in Desk and portal |
| `field_type` | display/input type | Yes | See enum contract |
| `value_source` | server-owned binding source | No | Required for bound fields; blank only for true one-off prompts |
| `field_mode` | interaction mode | Yes | Display Only, Confirm Current, or Allow Override |
| `required` | completion requirement flag | Yes | Applies to confirm and override inputs only |
| `allow_profile_writeback` | write-back eligibility flag | Yes | Valid only for writable profile-backed fields |

### `Family Consent Decision`

| Field | Contract | Required | Notes |
|---|---|---|---|
| `family_consent_request` | link to `Family Consent Request` | Yes | Parent request for this decision event |
| `student` | link to `Student` | Yes | Target student for whom the decision applies |
| `decision_by_doctype` | signer actor type | Yes | `Guardian` or `Student` |
| `decision_by` | signer actor name | Yes | Actor entity, not just the logged-in user |
| `decision_status` | immutable decision event outcome | Yes | See enum contract |
| `decision_at` | decision timestamp | Yes | Stored explicitly for evidence and reporting |
| `typed_signature_name` | submitted typed signature | No | Required only when the request requires typed signature |
| `attestation_confirmed` | signer attestation flag | Yes | Required only when the request requires attestation |
| `source_channel` | channel that created the decision | Yes | Guardian Portal, Student Portal, or Desk Paper Capture |
| `source_file` | governed evidence attachment | No | Used for scanned paper evidence or supporting attachments |
| `response_snapshot` | immutable JSON payload of presented and submitted values | Yes | See snapshot contract |
| `profile_writeback_mode` | write-back decision for this submit | No | Blank when no writable profile-backed fields changed |
| `supersedes_decision` | link to prior `Family Consent Decision` | No | Used for withdrawal or later changes without mutating earlier evidence |

## State And Enum Contract
Status: Planned
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/api/policy_signature.py`
Test refs: None

Rules:

1. `Family Consent Request.status` values are:
   - `Draft`
   - `Published`
   - `Closed`
   - `Archived`
2. `subject_scope` values are:
   - `Per Student`
   - `Per Family` reserved for a later contract
3. `audience_mode` values are:
   - `Guardian`
   - `Student`
   - `Guardian + Student`
4. `signer_rule` values are:
   - `Any Authorized Guardian`
   - `All Authorized Guardians`
   - `Student Self`
   - `Guardian And Student`
5. Phase 2A implements only:
   - `Guardian` with `Any Authorized Guardian` or `All Authorized Guardians`
   - `Student` with `Student Self`
6. `decision_mode` values are:
   - `Approve / Decline`
   - `Grant / Deny`
   - `Acknowledge` reserved for a later non-durable operational receipt contract
7. `completion_channel_mode` values are:
   - `Portal Only`
   - `Portal Or Paper`
   - `Paper Only`
8. `Family Consent Field.field_type` values are:
   - `Text`
   - `Long Text`
   - `Phone`
   - `Email`
   - `Address`
   - `Date`
   - `Checkbox`
9. `Family Consent Field.field_mode` values are:
   - `Display Only`
   - `Confirm Current`
   - `Allow Override`
10. `Family Consent Decision.decision_status` values are:
   - `Approved`
   - `Declined`
   - `Granted`
   - `Denied`
   - `Withdrawn`
11. `Family Consent Decision.source_channel` values are:
   - `Guardian Portal`
   - `Student Portal`
   - `Desk Paper Capture`
12. `profile_writeback_mode` values are:
   - blank
   - `Form Only`
   - `Update Profile`
13. `pending`, `completed`, `declined`, `withdrawn`, `expired`, and `overdue` are derived board and analytics states, not raw `decision_status` values stored on the decision row.
14. `completed` maps from the latest non-superseded `Approved` or `Granted` event that is still active inside the request window.
15. `declined` maps from the latest non-superseded `Declined` or `Denied` event.
16. `withdrawn` maps from the latest non-superseded `Withdrawn` event.
17. `expired` and `overdue` are time-derived target/request states and must not be inserted as synthetic decision rows.
18. `Paper Only` requests may only be completed through `Desk Paper Capture`.

## Snapshot Payload Contract
Status: Planned
Code refs: `ifitwala_ed/students/doctype/guardian/guardian.py`, `ifitwala_ed/students/doctype/student/student.py`, `ifitwala_ed/utilities/contact_utils.py`
Test refs: None

Rules:

1. `response_snapshot` is the immutable evidence payload for every `Family Consent Decision`.
2. `response_snapshot` must store these top-level blocks:
   - `request`
   - `signer`
   - `field_values`
   - `writeback`
3. `request` must contain:
   - `request_key`
   - `request_title`
   - `request_type`
   - `decision_mode`
   - `effective_from`
   - `effective_to`
   - `due_on`
4. `signer` must contain:
   - `decision_by_doctype`
   - `decision_by`
   - `typed_signature_name`
   - `attestation_confirmed`
5. `field_values` must be an ordered list of rows, each containing:
   - `field_key`
   - `field_label`
   - `field_type`
   - `field_mode`
   - `value_source`
   - `presented_value`
   - `submitted_value`
   - `changed`
   - `allow_profile_writeback`
6. For `field_type = Address`, `presented_value` and `submitted_value` use the structured address payload defined in the field-binding contract; other field types continue to use scalar values.
7. `writeback` must contain:
   - `profile_writeback_mode`
   - `changed_profile_fields`
   - `before_values`
   - `after_values`
8. When the signer chooses `Form Only`, `submitted_value` still captures the override while `before_values` and `after_values` remain equal for master profile data.
9. When the signer chooses `Update Profile`, the snapshot must preserve both the presented values and the canonical after-values written to `Contact`, `Address`, and mirrored convenience fields.
10. For student self-sign, mirrored convenience fields include `Student.student_email` and `Student.student_mobile_number` because student runtime and user linkage still depend on them.
11. For guardian sign, mirrored convenience fields include `Guardian.guardian_email` and `Guardian.guardian_mobile_phone`.

## Named Endpoint Contract
Status: Planned
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/api/guardian_home.py`
Test refs: None

Rules:

1. Desk workflows use `Family Consent Request.name` as the primary identifier.
2. Portal workflows use `request_key` plus `student` as the stable detail identifier.
3. Board and detail endpoints must return one bounded payload each; portal surfaces must not build the form through request waterfalls.
4. No endpoint may emit raw private file URLs. Any request attachment or paper-evidence attachment must use the governed attachment/open-preview contract from `files_08_cross_portal_governed_attachment_preview_contract.md`.
5. Submit and withdraw workflows must be idempotent. A repeated identical transition returns a success response with `status = already_current` instead of duplicating evidence rows.

### Staff Workflows

1. `get_family_consent_dashboard_context`
   - caller: staff Vue analytics/dashboard surface
   - request:
     - `organization?: string`
   - response:
     - `filters.organization`
     - `options.organizations: string[]`
     - `options.schools: string[]`
     - `options.request_types: string[]`
     - `options.statuses: string[]`
     - `options.audience_modes: string[]`
     - `options.completion_channel_modes: string[]`
2. `publish_family_consent_request`
   - caller: Desk button or Desk form action
   - request:
     - `family_consent_request: string`
     - `send_initial_communication?: 0 | 1`
   - response:
     - `ok: boolean`
     - `status: "published" | "already_published"`
     - `family_consent_request: string`
     - `request_key: string`
     - `target_count: number`
     - `communication_count: number`
3. `get_family_consent_dashboard`
   - caller: staff Vue analytics/dashboard surface
   - request:
     - `organization?: string`
     - `school?: string`
     - `request_type?: string`
     - `status?: string`
     - `audience_mode?: string`
     - `completion_channel_mode?: string`
   - response:
     - `meta.generated_at`
     - `filters`
     - `counts` with:
       - `requests`
       - `pending`
       - `completed`
       - `declined`
       - `withdrawn`
       - `expired`
       - `overdue`
     - `rows[]` with:
       - `family_consent_request`
       - `request_key`
       - `request_title`
     - `request_type`
     - `audience_mode`
     - `signer_rule`
     - `completion_channel_mode`
     - `status`
     - `organization`
     - `school`
       - `due_on`
       - `target_count`
       - `pending_count`
       - `completed_count`
       - `declined_count`
       - `withdrawn_count`
       - `expired_count`
       - `overdue_count`

### Guardian Workflows

3. `get_guardian_consent_board`
   - request: none
   - response:
     - `meta.generated_at`
     - `meta.guardian.name`
     - `family.children`
     - `counts` with:
       - `pending`
       - `completed`
       - `declined`
       - `withdrawn`
       - `expired`
       - `overdue`
     - `groups` with:
       - `action_needed[]`
       - `completed[]`
       - `declined_or_withdrawn[]`
       - `expired[]`
     - each board row contains:
       - `request_key`
       - `request_title`
       - `request_type`
       - `decision_mode`
       - `student`
       - `student_name`
       - `organization`
       - `school`
       - `due_on`
       - `effective_from`
       - `effective_to`
       - `current_status`
       - `current_status_label`
       - `last_decision_at`
       - `last_decision_by`
4. `get_guardian_consent_detail`
   - request:
     - `request_key: string`
     - `student: string`
   - response:
     - `meta.generated_at`
     - `request` with:
       - `family_consent_request`
       - `request_key`
       - `request_title`
       - `request_type`
       - `decision_mode`
       - `completion_channel_mode`
       - `request_text`
       - `source_attachment_preview`
       - `effective_from`
       - `effective_to`
       - `due_on`
       - `requires_typed_signature`
       - `requires_attestation`
     - `target` with:
       - `student`
       - `student_name`
       - `organization`
       - `school`
       - `current_status`
       - `current_status_label`
     - `signer` with:
       - `doctype`
       - `name`
       - `expected_signature_name`
     - `fields[]` with:
       - `field_key`
       - `field_label`
       - `field_type`
       - `field_mode`
       - `required`
       - `presented_value`
       - `allow_profile_writeback`
       - `binding_label`
     - `history[]` with:
       - `decision_status`
       - `decision_at`
       - `decision_by_doctype`
       - `decision_by`
       - `source_channel`
   - attachment rule:
     - `request.source_attachment_preview` follows the governed `AttachmentPreviewItem` DTO contract from `files_08_cross_portal_governed_attachment_preview_contract.md`
5. `submit_guardian_consent_decision`
   - request:
     - `request_key: string`
     - `student: string`
     - `decision_status: string`
     - `typed_signature_name?: string`
     - `attestation_confirmed?: 0 | 1`
     - `field_values: Array<{ field_key: string; value: string | number | boolean | null | { address_line1?: string; address_line2?: string; city?: string; state?: string; country?: string; pincode?: string } }>`
     - `profile_writeback_mode?: "Form Only" | "Update Profile"`
   - response:
     - `ok: boolean`
     - `status: "submitted" | "already_current"`
     - `decision_name: string`
     - `request_key: string`
     - `student: string`
     - `current_status: string`
     - `profile_writeback_mode: string | null`
   - server rule:
     - reject submit when `completion_channel_mode = "Paper Only"`

### Student Workflows

6. `get_student_consent_board`
   - request: none
   - response:
     - `meta.generated_at`
     - `meta.student.name`
     - `identity.student`
     - `counts` with:
       - `pending`
       - `completed`
       - `declined`
       - `withdrawn`
       - `expired`
       - `overdue`
     - `groups` with:
       - `action_needed[]`
       - `completed[]`
       - `declined_or_withdrawn[]`
       - `expired[]`
     - board row shape matches guardian board rows except there is no family child list
7. `get_student_consent_detail`
   - request:
     - `request_key: string`
     - `student: string`
   - response:
     - same structural blocks as guardian detail, except `signer.doctype = "Student"` and `signer.expected_signature_name` is resolved from the current student context
8. `submit_student_consent_decision`
   - request:
     - `request_key: string`
     - `student: string`
     - `decision_status: string`
     - `typed_signature_name?: string`
     - `attestation_confirmed?: 0 | 1`
     - `field_values: Array<{ field_key: string; value: string | number | boolean | null | { address_line1?: string; address_line2?: string; city?: string; state?: string; country?: string; pincode?: string } }>`
     - `profile_writeback_mode?: "Form Only" | "Update Profile"`
   - response:
     - same shape as `submit_guardian_consent_decision`
   - server rule:
     - reject submit when `completion_channel_mode = "Paper Only"`

### Shared Mutation Workflows

9. `withdraw_family_consent_decision`
   - caller: guardian portal or student portal when the current state allows withdrawal
   - request:
     - `request_key: string`
     - `student: string`
     - `typed_signature_name?: string`
     - `attestation_confirmed?: 0 | 1`
   - response:
     - `ok: boolean`
     - `status: "withdrawn" | "already_current"`
     - `decision_name: string`
     - `request_key: string`
     - `student: string`
     - `current_status: "withdrawn"`
10. `record_family_consent_paper_decision`
   - caller: Desk only
   - request:
     - `family_consent_request: string`
     - `student: string`
     - `decision_by_doctype: "Guardian" | "Student"`
     - `decision_by: string`
     - `decision_status: string`
     - `decision_at: string`
     - `source_file?: string`
   - response:
     - `ok: boolean`
     - `status: "recorded"`
     - `decision_name: string`
     - `family_consent_request: string`
     - `student: string`

## Decision Rationale
Status: Partial
Code refs: `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
Test refs: None

Pros:

1. Keeps immutable `Policy Acknowledgement` semantics intact instead of overloading them with mutable states.
2. Keeps staff authoring in Frappe-native Desk workflows, which fits day-to-day school and university operations better than introducing a second authoring shell.
3. Preserves the enrolled signer-authority runtime model on `can_consent` while tightening the business rule so only primary guardians receive that signer authority.
4. Adds day-one adult-student self-sign without forcing student-specific logic into guardian pages.
5. Reduces duplicate data entry by binding most fields to known profile data instead of asking families to retype it.
6. Makes reminders, expiry, withdrawal, and profile-writeback choice explicit instead of encoding them as absence of acknowledgement.

Cons:

1. Introduces a second governance workflow family beside versioned policy acknowledgements.
2. Requires new desk authoring workflow, request schema, and portal request pages rather than only extending the current policy page.
3. Field binding and profile-writeback behavior increase implementation complexity compared with a simple yes/no consent flow.

Blind spots:

1. The final Desk authoring UX for template/preset management still needs implementation design.
2. Renewal cadence defaults for annual consents are not yet wired and will depend on school operations.
3. Later admissions-stage reuse may require extending targets beyond enrolled students.

Risks:

1. If request types and decision modes are blurred in UI, families may not understand whether they are acknowledging, approving, or granting consent.
2. If signer authority is not enforced uniformly server-side, emergency-only guardians could be exposed to actions they must not take.
3. If staff dashboards reuse custom scope math instead of canonical helpers, permission drift will reappear.
4. If profile write-back bypasses canonical `Contact` and `Address` ownership, guardian/student contact data will drift and Desk quick views will become inconsistent.

## Contract Matrix
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/doctype/policy_version/policy_version.json`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.json`, `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`
Test refs: `ifitwala_ed/api/test_admissions_portal.py`, `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_policy_signature.py`

| Layer | Current canonical owner | Phase-2 extension | Status |
|---|---|---|---|
| Schema / DocType | `Institutional Policy`, `Policy Version`, `Policy Acknowledgement`, applicant/student guardian relationship rows | Add one approved request/decision layer plus request field bindings without changing the meaning of immutable acknowledgement evidence | Planned |
| Controller / workflow logic | `policy_utils`, admissions policy acknowledgement, guardian policy overview, policy acknowledgement permission checks | Add named workflows for request creation, guardian/student decision capture, profile write-back choice, change/withdraw, reminder safety, and offline evidence capture | Planned |
| API endpoints | `acknowledge_policy`, `get_guardian_policy_overview`, staff policy communication and signature APIs | Add named family request endpoints instead of assembling generic CRUD from the client | Planned |
| Desk / portal surfaces | Admissions policies page, guardian policies page, guardian home, student policies page, staff policy analytics | Add Desk authoring, family action cards, dedicated guardian/student request pages, and explicit request-mode UI for one-off and mutable decisions | Planned |
| Reports / dashboards / briefings | Staff policy signature analytics and current portal counts | Extend to request-type and decision-status analytics for family workflows while keeping Desk as the authoring home | Planned |
| Scheduler / background jobs | Existing policy communication and staff reminder patterns only | Add reminder and overdue sweeps with idempotent, status-aware dispatch | Planned |
| Tests | Existing admissions, guardian-policy, and staff policy signature coverage | Add end-to-end coverage for request creation, decision capture, withdrawal, expiry, and permission enforcement | Planned |
