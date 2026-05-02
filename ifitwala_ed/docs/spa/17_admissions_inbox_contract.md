# Admissions Inbox SPA Contract

Status: Backend context endpoint, Phase 3B staff SPA queue route, Phase 3C controlled action drawer, Phase 3D ownership/triage workflows, Phase 3D.5 CRM intake, and Phase 3E applicant-stage message aggregation implemented; provider and media workflows planned
Code refs: `ifitwala_ed/api/admissions_inbox.py`, `ifitwala_ed/api/admissions_crm.py`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsInbox.vue`, `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsInboxService.ts`, `ifitwala_ed/ui-spa/src/types/contracts/admissions_inbox/get_admissions_inbox_context.ts`, CRM DocTypes under `ifitwala_ed/admission/doctype/admission_*`
Test refs: `ifitwala_ed/api/test_admissions_inbox.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/AdmissionsInbox.test.ts`, `ifitwala_ed/ui-spa/src/lib/services/admissions/__tests__/admissionsInboxService.test.ts`, `ifitwala_ed/admission/doctype/admission_conversation/test_admission_conversation.py`

This note defines the staff-side Admissions Inbox surface.

Current runtime behavior includes the backend context endpoint, staff SPA queue route, controlled action drawer, ownership/triage actions for Admission Conversation and Inquiry records, manual CRM intake, and applicant-stage case message aggregation. Provider replies, contact creation, and governed media conversion are still planned.

## 1. Authority

This contract inherits:

- `01_spa_architecture_and_rules.md`
- `02_style_note.md`
- `03_overlay_and_workflow.md`
- `05_focus_and_attention_system.md`
- `07_org_communication_messaging_contract.md`
- `../high_concurrency_contract.md`
- `../admission/01_governance.md`
- `../admission/05_admission_portal.md`
- `../admission/11_admissions_crm_contract.md`
- `../files_and_policies/README.md`

If a UI design conflicts with server-side admissions governance, the server contract wins.

## 2. Product Purpose

Admissions Inbox is the staff command center for lead and applicant communication work.

It is not:

- a generic chat surface
- a school-wide communication center
- a replacement for applicant portal workflows
- a client-side matching engine
- a raw provider console

It must turn every parent/inquirer message into an owned admissions next action.

## 3. Route

Implemented route:

```text
/staff/admissions/inbox
```

The page belongs to the staff SPA and must preserve the staff shell/container contract.

## 4. Data Sources

The Inbox may aggregate these sources into one display DTO:

- `Inquiry`
- `Admission Conversation`
- `Admission Message`
- `Admission CRM Activity`
- applicant-stage `Org Communication` summaries for linked `Student Applicant` cases
- applicant blockers from existing admissions workspace/cockpit read models when explicitly included by the endpoint

The Inbox must not merge the storage models.

Storage boundary:

- pre-applicant CRM messages live in `Admission Message`
- applicant portal case messages live in `Org Communication` / `Communication Interaction Entry`
- provider metadata remains on `Admission Message`
- read state for applicant portal case messages remains `Portal Read Receipt`

Implemented Phase 3A backend context includes:

- active `Inquiry` rows
- `Admission Conversation` summary rows
- latest CRM message/activity summary fields stored on `Admission Conversation`
- `Student Applicant` rows in `Invited` and `Missing Info`
- applicant-stage case message summaries from `Org Communication` when a linked applicant thread exists

Phase 3E aggregates applicant-stage `Org Communication` read state and portal-message needs-reply state through the admissions communication summary helper.

## 5. Endpoint Shape

Implemented page-init endpoint:

```text
ifitwala_ed.api.admissions_inbox.get_admissions_inbox_context
```

The endpoint must return all foundational data needed for first render.

Rules:

- one bounded context endpoint for page init
- no more than five foundational API calls
- no per-row follow-up requests to render the queue list
- server-side permission filtering before DTO assembly
- organization and school filters resolved server-side
- use `limit`, not `limit_page_length`

Implemented request parameters:

```text
organization optional
school optional
limit optional, bounded to 1..100
```

Implemented response top-level shape:

```text
ok
generated_at
filters
queues
sources
```

Implemented Phase 2A backend mutation endpoints:

```text
ifitwala_ed.api.admissions_crm.log_admission_message
ifitwala_ed.api.admissions_crm.record_admission_crm_activity
ifitwala_ed.api.admissions_crm.link_admission_conversation
ifitwala_ed.api.admissions_crm.confirm_admission_external_identity
```

Implemented Phase 3C action payloads:

```text
log_admission_message
  conversation optional
  inquiry optional
  student_applicant optional
  external_identity optional
  channel_account optional
  organization optional
  school optional
  assigned_to optional
  direction = Outbound
  message_type = Text
  delivery_status = Logged
  body required
  client_request_id required by SPA service

record_admission_crm_activity
  conversation required
  activity_type required
  outcome optional
  note optional
  next_action_on optional
  client_request_id required by SPA service

link_admission_conversation
  conversation required
  inquiry optional
  student_applicant optional
  external_identity optional
  channel_account optional
  client_request_id required by SPA service

confirm_admission_external_identity
  external_identity required
  match_status required: Unmatched | Suggested | Confirmed | Rejected
  contact optional
  guardian optional
  inquiry optional
  student_applicant optional
  client_request_id required by SPA service
```

Implemented Phase 3D action payloads:

```text
assign_admission_conversation
  conversation required
  assigned_to required
  client_request_id required by SPA service

update_admission_conversation_status
  conversation required
  status required: Open | Closed | Archived | Spam
  note optional
  client_request_id required by SPA service

create_inquiry_from_admission_conversation
  conversation required
  type_of_inquiry optional
  source optional
  message optional
  client_request_id required by SPA service

assign_inquiry_from_inbox
  inquiry required
  assigned_to required
  assignment_lane optional: Admission | Staff
  client_request_id required by SPA service

archive_inquiry_from_inbox
  inquiry required
  reason required
  client_request_id required by SPA service

mark_inquiry_contacted_from_inbox
  inquiry required
  complete_todo optional
  client_request_id required by SPA service

qualify_inquiry_from_inbox
  inquiry required
  client_request_id required by SPA service

invite_inquiry_to_apply_from_inbox
  inquiry required
  school required
  organization optional
  client_request_id required by SPA service
```

Implemented Phase 3D.5 intake payload:

```text
create_admissions_intake
  organization required
  school optional
  type_of_inquiry required
  source required
  activity_channel required
  first_name optional
  last_name optional
  email optional
  phone_number optional
  student_first_name optional
  student_last_name optional
  intended_academic_year optional
  grade_level_interest optional
  program_interest optional
  student_name_or_id optional
  relationship_to_student optional
  organization_name optional
  partnership_context optional
  message optional
  activity_type required
  outcome optional
  note optional
  next_action_on optional
  assigned_to optional
  assignment_lane optional: Admission | Staff
  client_request_id required by SPA service
```

Implemented Phase 3E applicant case reply payload:

```text
send_admissions_case_message
  context_doctype required: Student Applicant
  context_name required
  body required
  applicant_visible = 1
  client_request_id required by SPA service
```

Planned Inbox-specific mutation endpoints must continue to be named workflow endpoints, for example:

```text
send_admission_reply
link_admission_identity
link_admission_conversation_to_inquiry
link_admission_conversation_to_applicant
convert_admission_media_to_governed_file
```

Exact Inbox endpoint names and payloads require implementation approval.

## 6. Queue DTO

The server returns queue rows shaped for rendering, not raw DocType rows.

Required row concepts:

```text
id
kind
stage
title
subtitle
organization
school
inquiry
student_applicant
conversation
external_identity
channel_type
channel_account
owner
sla_state
last_activity_at
last_message_preview
needs_reply
unread_count
next_action_on
open_url
permissions
actions
```

`permissions` and `actions` are server-owned. The SPA may hide blocked actions for UX, but the server must enforce every mutation.

`open_url` is server-owned. The SPA must not derive Desk URLs from DocType names or document names.

## 7. Initial Queues

Implemented Phase 3A queues:

- Needs Reply
- Unassigned
- Overdue First Contact
- Due Today
- Qualified Not Invited
- Invited Not Started
- Missing Documents
- Stale Leads
- Unmatched Messages

Planned later queue:

- Visit / Open Day Follow-up

Queue membership is server-derived.

The SPA must not infer queue membership from raw status fields.

## 8. Actions

Implemented Phase 3B UI actions:

- open the server-owned source record URL when `permissions.can_open` and `open_url` allow it
- retry a failed page-owned context load
- switch queues client-side using the server-returned queue DTO

Implemented Phase 3C UI actions:

- log reply or log message through `log_admission_message`
- record CRM activity through `record_admission_crm_activity`
- link a conversation to Inquiry or Student Applicant through `link_admission_conversation`
- resolve external identity status through `confirm_admission_external_identity`

Implemented Phase 3D UI actions:

- assign or reassign Admission Conversation owner
- assign or reassign Inquiry owner through existing Inquiry assignment helpers
- archive or mark spam Admission Conversation
- create Inquiry from Admission Conversation
- archive Inquiry through existing Inquiry archive method
- mark Inquiry contacted through existing Inquiry controller method
- qualify Inquiry through existing Inquiry controller method
- invite Inquiry to apply through existing Inquiry-to-Applicant helper

Implemented Phase 3D.5 UI action:

- record manual CRM intake from the page header as a server-owned workflow that creates `Inquiry`, linked `Admission Conversation`, and first `Admission CRM Activity`

Implemented Phase 3E UI action:

- reply to applicant-stage case messages through `send_admissions_case_message`

Planned mutation actions:

- send provider reply
- create or link Contact
- import external media through governed workflow when eligible

Blocked actions must explain why they are blocked and what to do next.

The SPA must not render inert mutation buttons. Until a mutation endpoint and payload contract exists, staff should open the source record rather than trigger a silent or client-only workflow.

Unsupported server-returned actions may be listed as source-record workflows, but they must not be presented as executable Inbox actions.

Successful Phase 3C mutations must emit `SIGNAL_ADMISSIONS_INBOX_INVALIDATE`; the page remains the refresh owner and reloads the single context endpoint.

## 9. Messaging UX Boundary

Pre-applicant messages:

- render from `Admission Message`
- use provider/channel labels
- expose delivery status when available
- do not use `Communication Interaction Entry`

Applicant-stage case messages:

- render from the existing admissions case thread summary and thread APIs
- use `Org Communication` as the case container
- keep applicant portal visibility rules unchanged

The UI may present both in one timeline, but it must label stage/provenance clearly enough that staff can tell whether they are looking at pre-applicant CRM history or applicant-stage case communication.

## 10. Media UX Boundary

The Inbox must not render raw provider media URLs.

External media rows may show metadata and allowed actions only:

- file name
- media type
- size when available
- provider status
- eligible conversion actions

Inline previews are allowed only after the media has been imported through a governed Drive workflow and the server returns stable Ed-owned `open_url`, `preview_url`, or `thumbnail_url` values.

## 11. Matching UX

The Inbox may show suggested matches, but matching remains server-scored and staff-confirmed.

Rules:

- no fuzzy auto-link
- exact match may still require confirmation when multiple candidates exist
- staff must see why a candidate is suggested
- rejected matches must not be re-suggested without new evidence

## 12. Refresh And Signals

Mutations that affect queues, counts, or timelines must emit a SPA invalidation signal.

Planned signal:

```text
SIGNAL_ADMISSIONS_INBOX_INVALIDATE
```

The page is the refresh owner.

Overlays and action panels perform mutations, close on success when appropriate, and let the page refresh through signals.

## 13. Performance And Concurrency

Admissions Inbox is a hot path.

Rules:

- batch reads
- avoid per-row `get_doc`
- preload shared applicant, inquiry, owner, identity, and latest-message inputs once
- cap queue result sizes
- paginate or cursor large queues
- keep message sends and activity logging as short mutations
- use idempotency keys for reply/send/log actions
- defer provider delivery enrichment when safe

No cache may be added without key shape, scope dimensions, and invalidation ownership.

## 14. Testing Expectations

Backend tests must cover:

- server-side scope filtering
- organization-only Inquiry triage
- school-scoped Inquiry triage
- assigned-user visibility
- applicant-linked conversation visibility
- no fuzzy auto-link
- idempotent message ingestion/logging
- needs-reply calculation
- governed media conversion permission checks

SPA tests must cover:

- first render from one context payload
- queue filtering without request waterfalls
- blocked open-link explanation
- page-owned manual refresh
- action drawer rendering from server-owned actions
- mutation payload shape
- inline mutation failure
- signal-driven refresh after successful mutation
- no raw media URL rendering
