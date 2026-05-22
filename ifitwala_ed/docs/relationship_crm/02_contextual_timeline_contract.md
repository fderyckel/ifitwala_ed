# Contextual Timeline Contract

Status: Admissions backend timeline endpoint, Inbox/Cockpit SPA timeline drawers, Cockpit CRM log activity/message drawer actions, Inbox/Cockpit applicant-stage offer/deposit/promotion drawer actions, Inbox/Cockpit schedule-visit drawer actions, and Inquiry/Student Applicant Desk entry points implemented; broader Relationship CRM timeline remains planned.
Code refs:
- Admissions contextual timeline endpoint: `ifitwala_ed/api/admissions_timeline.py`
- Current admissions timeline UI: `ifitwala_ed/ui-spa/src/components/admissions/AdmissionsTimelinePanel.vue`, `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsTimelineService.ts`, `ifitwala_ed/ui-spa/src/types/contracts/admissions_timeline/get_admissions_timeline_context.ts`
- Current Desk timeline entry points: `ifitwala_ed/public/js/admissions_timeline_desk.js`, `ifitwala_ed/admission/doctype/inquiry/inquiry.js`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`
- Current admissions inbox aggregation: `ifitwala_ed/api/admissions_inbox.py`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsInbox.vue`
- Current admissions CRM mutations: `ifitwala_ed/api/admissions_crm.py`
- Current applicant communication wrappers: `ifitwala_ed/api/admissions_communication.py`
- Current admissions cockpit read model: `ifitwala_ed/api/admission_cockpit.py`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`
Test refs: `ifitwala_ed/api/test_admissions_timeline.py`, `ifitwala_ed/ui-spa/src/lib/services/admissions/__tests__/admissionsTimelineService.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/AdmissionsInbox.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/AdmissionsCockpit.test.ts`; related current tests are listed in the admissions and SPA contracts.

This contract defines the contextual timeline projection for admissions and the planned broader Education Relationship CRM work.

## 1. Product Rule

The user should see:

```text
what happened, what matters, what to do next
```

The user should not see:

```text
which backend ledger owns this row
```

The timeline is a product projection. It is not a new source of truth for every item it displays.

## 2. Ledger Separation

Storage may remain separated.

Examples of valid source ledgers:

- `Inquiry`
- `Admission Conversation`
- `Admission Message`
- `Admission CRM Activity`
- `Admission Visit`
- `Org Communication`
- `Communication Interaction Entry`
- `Portal Read Receipt`
- `Applicant Enrollment Plan`
- `Sales Invoice`
- `Payment Request`
- `Program Enrollment Request`
- `Program Enrollment`
- future `Education Relationship`
- future `Relationship Case`
- future `Relationship Activity`

The timeline must not copy source rows into a second canonical ledger merely to make them visible together.

## 3. Admissions Timeline

The implemented backend admissions contextual timeline endpoint is:

```text
ifitwala_ed.api.admissions_timeline.get_admissions_timeline_context
```

Implemented backend contexts:

- Inquiry
- Student Applicant
- Admission Conversation

Implemented entry points:

- Admissions Inbox selected-row drawer
- Admissions Cockpit applicant-card drawer
- Inquiry
- Student Applicant

The endpoint projects:

- Inquiry capture, assignment, contact, qualification, archive state
- pre-applicant CRM messages and activities
- visits and visit outcomes
- applicant-stage case messages from `Org Communication`
- offer and deposit milestones from `Applicant Enrollment Plan`
- promotion, Program Enrollment Request, Program Enrollment, and identity-upgrade milestones

`Student Applicant.application_status` must not be overloaded to mean "admissions complete."

The derived admissions completion ladder is:

```text
Lead
-> Applicant
-> Submitted
-> Approved
-> Offer Sent
-> Offer Accepted
-> Deposit Ready
-> Promoted
-> Enrollment Request
-> Enrolled
-> Identity Upgraded
```

This ladder is a read-model projection. It must not become persistent state unless a later approved contract defines persistent fields.

## 4. Relationship Timeline

The planned Relationship Timeline should be available from:

- Education Relationship
- Relationship Case
- Relationship Center queue row
- linked Inquiry
- linked Student Applicant
- linked school event or visit where the relationship context is explicit

It should project:

- relationship activities
- communication summaries
- meetings and visits
- linked inquiries and applicants
- sponsor or grant milestones where approved
- linked finance state as summary only
- event participation or outcome notes where approved
- scheduled next actions

The timeline must show only purpose-appropriate context for the current user.

## 5. Timeline DTO Rules

The timeline endpoint must return a bounded DTO for first render.

Required top-level shape should include:

```text
ok
generated_at
context
summary
items
actions
has_more
```

Each item should include:

```text
id
kind
source_doctype
source_name
occurred_at
title
summary
actor
visibility
context_labels
open_url optional
actions
```

Rules:

- `source_doctype` and `source_name` are for audit/debug/deep-linking, not primary UI labels.
- `kind` must be product language such as `message`, `touchpoint`, `visit`, `offer`, `deposit`, `enrollment`, `note`, or `follow_up`.
- Raw private file paths must never appear.
- Raw contact values must not appear unless the named workflow is approved to reveal them.
- Timeline items must be sorted by real datetime, not formatted strings.
- Timeline assembly must apply permission and tenant scope before item shaping.

## 6. Contextual Actions

Actions must be server-owned and context-aware.

Examples:

- Log Activity
- Log Message
- Schedule Visit
- Message Family
- Manage Offer
- Check Deposit
- Promote
- Record Touchpoint
- Assign Owner
- Schedule Follow-up
- Link Inquiry
- Link Applicant
- Close Case

Blocked actions must explain:

- why the action is blocked
- what the user should do next

The SPA may hide or disable actions for ergonomics, but server endpoints own permission and workflow invariants.

## 7. Request And Concurrency Rules

Timeline endpoints are hot read surfaces.

Rules:

- use one bounded context endpoint per timeline load
- avoid per-row `get_doc(...)` loops
- preload shared stable inputs once
- use `limit`, never `limit_page_length`
- do not add persistent counters without a cache/invalidation contract
- do not add polling loops for timeline freshness without explicit ownership
- mutation endpoints should emit surface invalidation signals only after semantic success

## 8. Implementation Slices

Implementation sequence:

1. Admissions timeline endpoint over existing admissions and applicant ledgers. Implemented.
2. Shared timeline panel in Admissions Inbox and Admissions Cockpit. Implemented.
3. Desk contextual buttons on Inquiry and Student Applicant that open the same timeline/action pattern. Implemented.
4. Inbox/Cockpit contextual drawer actions for Log Activity, Log Message, Message Family, Manage Offer, Check Deposit, and Promote. Implemented.
5. Native SPA Admission Visit scheduling from the Cockpit/Inbox timeline drawer. Implemented.
6. Relationship timeline only after Relationship CRM schema is approved. Planned.

## 9. Test Expectations

Tests must cover:

- timeline scope filtering before DTO assembly
- no row leakage across sibling schools
- bounded query behavior for common paths
- action availability and disabled reasons
- source ledger preservation without copying into timeline truth
- applicant-stage messages remaining in `Org Communication`
- pre-applicant CRM messages remaining in `Admission Message`
- no raw private file paths or broad contact payloads
