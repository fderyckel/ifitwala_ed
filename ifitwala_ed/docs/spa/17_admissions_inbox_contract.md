# Admissions Inbox SPA Contract

Status: Planned target contract with backend Phase 2A dependency implemented
Code refs: `ifitwala_ed/api/admissions_crm.py`, CRM DocTypes under `ifitwala_ed/admission/doctype/admission_*`
Test refs: `ifitwala_ed/admission/doctype/admission_conversation/test_admission_conversation.py`

This note defines the planned staff-side Admissions Inbox SPA surface.

It does not describe current runtime behavior until the route, endpoints, services, and tests are implemented.

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

Planned route:

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

## 5. Endpoint Shape

Planned page-init endpoint:

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

Implemented Phase 2A backend mutation endpoints:

```text
ifitwala_ed.api.admissions_crm.log_admission_message
ifitwala_ed.api.admissions_crm.record_admission_crm_activity
ifitwala_ed.api.admissions_crm.link_admission_conversation
ifitwala_ed.api.admissions_crm.confirm_admission_external_identity
```

Planned Inbox-specific mutation endpoints must continue to be named workflow endpoints, for example:

```text
log_admission_message
send_admission_reply
assign_admission_conversation
link_admission_identity
link_admission_conversation_to_inquiry
link_admission_conversation_to_applicant
create_inquiry_from_admission_conversation
record_admission_crm_activity
archive_admission_conversation
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
permissions
actions
```

`permissions` and `actions` are server-owned. The SPA may hide blocked actions for UX, but the server must enforce every mutation.

## 7. Initial Queues

Planned queues:

- Needs Reply
- Unassigned
- Overdue First Contact
- Due Today
- Qualified Not Invited
- Invited Not Started
- Missing Documents
- Visit / Open Day Follow-up
- Stale Leads
- Unmatched Messages

Queue membership is server-derived.

The SPA must not infer queue membership from raw status fields.

## 8. Actions

Initial actions:

- reply or log reply
- assign or reassign
- create or link Contact
- create or link Inquiry
- link to Student Applicant
- mark Inquiry contacted
- qualify Inquiry
- invite to apply
- record CRM activity
- archive with reason
- resolve identity match
- import external media through governed workflow when eligible

Blocked actions must explain why they are blocked and what to do next.

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
- blocked action explanation
- action payload shape
- signal-driven refresh
- no raw media URL rendering
