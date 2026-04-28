# Admissions CRM Contract

Status: Partial implementation
Code refs: `ifitwala_ed/admission/doctype/inquiry/inquiry.json`, `ifitwala_ed/admission/web_form/inquiry/inquiry.json`, `ifitwala_ed/admission/web_form/inquiry/inquiry.js`, `ifitwala_ed/admission/doctype/admission_acknowledgement_profile/admission_acknowledgement_profile.json`, `ifitwala_ed/admission/doctype/admission_acknowledgement_profile/admission_acknowledgement_profile.js`, `ifitwala_ed/admission/inquiry_acknowledgement.py`, `ifitwala_ed/admission/doctype/admission_channel_account/*`, `ifitwala_ed/admission/doctype/admission_external_identity/*`, `ifitwala_ed/admission/doctype/admission_conversation/*`, `ifitwala_ed/admission/doctype/admission_message/*`, `ifitwala_ed/admission/doctype/admission_crm_activity/*`, `ifitwala_ed/api/admissions_crm.py`, `ifitwala_ed/api/admissions_inbox.py`
Test refs: `ifitwala_ed/admission/doctype/inquiry/test_inquiry.py`, `ifitwala_ed/admission/doctype/admission_acknowledgement_profile/test_admission_acknowledgement_profile.py`, `ifitwala_ed/admission/doctype/admission_conversation/test_admission_conversation.py`, `ifitwala_ed/api/test_admissions_inbox.py`

This note defines the planned admissions CRM model for Inquiry-stage lead handling and external-channel messaging.

Phase 1 Inquiry dynamic capture, public family acknowledgement, Phase 2A CRM core manual mode, and the Phase 3A Admissions Inbox backend context endpoint are implemented.

The staff Inbox SPA route, provider adapters, governed media conversion, and lead-scoring/read-model work remain planned until their referenced SPA surfaces, APIs, and tests are implemented.

## 1. Authority

This contract must remain consistent with:

- `01_governance.md`
- `02_applicant_and_promotion.md`
- `03_portal_files_gdpr.md`
- `05_admission_portal.md`
- `10_ifitwala_drive_portal_uploads.md`
- `../files_and_policies/README.md`
- `../files_and_policies/files_01_architecture_notes.md`
- `../files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
- `../spa/07_org_communication_messaging_contract.md`
- `../spa/17_admissions_inbox_contract.md`

If this planned CRM contract conflicts with the locked admissions pipeline or governed-file contracts, those existing contracts win.

## 2. Pipeline Boundary

The admissions pipeline remains:

```text
Inquiry -> Student Applicant -> Promotion -> Student
```

Responsibilities:

- `Inquiry` is a lightweight triage and lead-capture record.
- `Student Applicant` is the sole pre-student admissions container.
- `Admission Conversation`, `Admission Message`, and `Admission CRM Activity` are CRM support records around Inquiry-stage and external-channel work.
- `Org Communication` remains the current applicant-stage case communication container for authenticated applicant portal messages.

No CRM work may create a parallel applicant container or bypass `Student Applicant`.

## 3. Inquiry Schema Rule

`Inquiry` may only store stable lead-triage facts.

Add a field to `Inquiry` only when it is:

- known before applicant creation
- useful for triage, routing, assignment, SLA, or lightweight reporting
- low-volume and non-repeatable
- not a derived message summary
- not provider transport metadata
- not applicant evidence, guardian identity, health, policy, document, interview, review, or promotion data

Fields that belong outside `Inquiry`:

- unread counts
- latest message previews
- provider payload JSON
- external message IDs
- delivery/read statuses
- media files
- message attachment metadata
- CRM activity history
- lead score and next-best-action fields until a concrete read-model/scoring contract is approved

## 4. Inquiry Type And Dynamic Form Contract

`type_of_inquiry` is the driver for conditional Inquiry capture.

Planned inquiry types:

```text
Admission
Current Family
General Inquiry
Partnership / Agent
Other
```

These labels are implemented in `Inquiry.type_of_inquiry`.

### 4.1 Shared Fields

All Inquiry types may use the current baseline fields:

- first name
- last name
- email
- phone number
- source
- organization
- school
- preferred contact channel
- preferred contact time
- preferred language
- consent to contact
- message
- next action note

`organization` and `school` remain triage context on Inquiry. They are informational and staff-correctable at this stage.

Hard institutional anchoring happens at `Student Applicant`, where `organization` and `school` are required and immutable.

### 4.2 Admission Fields

Show only when `type_of_inquiry = Admission`:

```text
student_first_name
student_last_name
intended_academic_year
grade_level_interest
program_interest
```

These fields are lead context only. They do not replace applicant profile fields or applicant targeting fields.

### 4.3 Current Family Fields

Show only when `type_of_inquiry = Current Family`:

```text
student_name_or_id
relationship_to_student
```

These values are staff triage hints. Matching to an enrolled student must be server-side and explicit; the public form must not expose searchable student data.

### 4.4 Partnership / Agent Fields

Show only when `type_of_inquiry = Partnership / Agent`:

```text
organization_name
partnership_context
```

These values identify the external organization and nature of the relationship. They do not create a supplier, agent, or partner record by themselves.

### 4.5 General And Other Fields

`General Inquiry` and `Other` should stay minimal beyond the shared fields:

```text
preferred_contact_channel
message
```

Additional type-specific fields require a separate schema approval.

## 4.6 Zero Lost Lead Command Center

Status: Implemented
Code refs: `ifitwala_ed/api/inquiry.py`, `ifitwala_ed/admission/doctype/inquiry/inquiry.json`, `ifitwala_ed/admission/doctype/inquiry/inquiry.py`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/InquiryAnalytics.vue`
Test refs: `ifitwala_ed/admission/doctype/inquiry/test_inquiry.py`

The current staff operational surface for Inquiry-stage lead loss prevention is the Zero Lost Lead command center at `/staff/analytics/inquiry`.

It is intentionally Inquiry-backed and does not require the planned Admissions Inbox or CRM message DocTypes.

Server-owned operational views:

- Unassigned new inquiries
- Uncontacted and due today
- Overdue first contact
- Contacted but no follow-up date
- Qualified but not invited to apply
- Invited but no applicant progress
- Archived without reason
- Leads older than 24 hours with no owner

Rules:

- queue membership is derived server-side by `ifitwala_ed.api.inquiry.get_zero_lost_lead_context`
- permissions and organization/school scope are applied before counts and rows are assembled
- operational views are all-time within the selected non-date filters so old lost leads cannot be hidden by the analytics date window
- row actions are server-owned next-action links to the canonical Desk Inquiry or Student Applicant record
- the SPA must not infer queue membership from raw fields
- the SPA command center must not mutate Inquiry workflow state directly from the analytics page until a separate workflow-overlay contract is approved
- `Inquiry.archive_reason` is required for future archive transitions; the "Archived without reason" view exists to surface legacy or bypassed rows that need operator correction

### 4.6 Public Family Acknowledgement

Status: Implemented for the first transactional version.

When a public `/apply/inquiry` submission creates an `Inquiry`, family acknowledgement has two parts:

- the Web Form success state becomes the branded thank-you page
- `Inquiry.after_insert` queues a family acknowledgement email after commit when the submission has an email address

This acknowledgement is transactional receipt and next-step guidance. It is not CRM conversation storage, applicant portal provisioning, or external-channel messaging.

Configuration lives in `Admission Acknowledgement Profile`:

- `organization` is required
- `school` is optional; a school-scoped active profile wins over an organization fallback
- `email_template` is required for configured profile email copy
- thank-you page title/message, timeline heading, footer note, and CTAs are declarative
- visit CTA may use the configured profile route or the selected School `admissions_visit_route`
- application CTA is hidden unless explicitly enabled with a public application route
- `/admissions` is rejected as an application CTA route because it is the authenticated Admissions Portal, not an anonymous application start

Runtime rules:

- The thank-you DTO is public-safe and may include only brand/copy/timeline/CTA data.
- The DTO must not expose Inquiry name, email, phone, internal assignment state, or applicant status.
- Email sending runs through `frappe.enqueue(..., queue="short", enqueue_after_commit=True)`.
- Email template rendering receives `doc`, `inquiry`, `profile`, `acknowledgement`, `brand`, `timeline`, and `ctas`.
- If no acknowledgement profile is configured, the system may send the generic transactional fallback email; school-specific copy requires a profile.
- WhatsApp, LINE, Facebook, SMS, delivery/read receipts, and external message storage remain out of scope for this acknowledgement version.

## 5. CRM DocTypes

### 5.1 Admission Channel Account

Represents a school-owned external channel endpoint.

Purpose:

- resolve organization and optional school context for inbound messages
- store enabled/disabled state
- define provider type and account identity
- define default routing hints
- hold references to provider secrets without exposing secret values in DTOs

This DocType is operational configuration, not a message ledger.

### 5.2 Admission External Identity

Represents a parent/contact identity on one external provider.

Purpose:

- store provider-scoped identity, such as WhatsApp phone, LINE user ID, Facebook PSID, Instagram scoped user ID, or email address
- link explicitly to `Contact`, `Inquiry`, and later `Student Applicant` when confirmed
- track match status and confidence

No fuzzy match may auto-link. Ambiguous matches must become staff decisions.

### 5.3 Admission Conversation

Represents the CRM case thread for Inquiry-stage and external-channel communication.

Purpose:

- group Admission Messages around an Inquiry or external identity
- optionally link to `Student Applicant` after conversion for cross-stage timeline display
- own manual-mode CRM reply-state fields: `latest_message_at`, latest inbound/outbound timestamps, `needs_reply`, `last_message_preview`, `next_action_on`, and `last_activity_at`
- store the CRM assignee in `assigned_to`

It must not duplicate `Org Communication` portal audience behavior.

### 5.4 Admission Message

Append-only external-channel message and provider audit record.

Purpose:

- webhook dedupe
- inbound/outbound direction
- provider message IDs
- delivery/read status
- provider payload summary or raw payload storage when approved
- external media metadata
- provenance link to a related applicant-stage `Org Communication` entry when applicable

It is not the applicant portal message ledger.

Implemented records are append-only for original history fields. Delivery/media status enrichment and applicant-stage provenance links may update their dedicated status/link fields, but body, direction, provider IDs, context, and external media metadata must not be rewritten.

The implemented media fields are metadata only:

```text
media_provider_id
media_mime_type
media_file_name
media_size
media_status
```

There is no `media_file` field on `Admission Message`.

### 5.5 Admission CRM Activity

Append-only structured CRM activity record.

Purpose:

- call attempt
- no answer
- reached
- qualified
- not interested
- booked tour
- attended tour
- follow-up scheduled
- archive/lost reason
- staff note that is not a channel message

It must not store chat history, reactions, or read receipts.

Implemented activity rows are append-only. Corrections must be recorded as a new activity.

Implemented manual-mode API endpoints:

```text
ifitwala_ed.api.admissions_crm.log_admission_message
ifitwala_ed.api.admissions_crm.record_admission_crm_activity
ifitwala_ed.api.admissions_crm.link_admission_conversation
ifitwala_ed.api.admissions_crm.confirm_admission_external_identity
```

These endpoints use flat payloads, server-owned permission checks, scoped CRM writes, and short-lived idempotency keys via `client_request_id`.

## 6. Messaging Boundary

Before applicant conversion:

```text
Admission Conversation -> Admission Message -> Admission CRM Activity
```

After applicant conversion:

```text
Student Applicant -> Org Communication -> Communication Interaction Entry -> Portal Read Receipt
```

The Admissions Inbox may aggregate both sources into one DTO, but storage remains separated by stage.

Pre-applicant CRM messages must not be migrated into `Org Communication` by default. Historical provenance remains attached to the Inquiry-stage CRM records.

When an external channel message arrives after applicant conversion:

```text
Admission Message stores provider envelope, dedupe, and delivery metadata
Org Communication stores the applicant-stage case message when visible in the applicant case thread
```

The `Admission Message` in that case is transport audit, not a second staff-facing message ledger.

## 7. Media And File Governance

External-channel media must not become a raw `File` row or direct Inquiry attachment.

Inbound external media starts as provider metadata only:

```text
Admission Message.media_provider_id
Admission Message.media_mime_type
Admission Message.media_file_name
Admission Message.media_size
Admission Message.media_status
```

The binary is imported only through an explicit governed workflow action.

Allowed conversion targets:

- `Applicant Document Item`
- `Student Applicant.applicant_image`
- `Student Applicant Guardian.guardian_image`
- `Student` media after promotion and valid target ownership
- `Guardian` media after identity upgrade and valid target ownership

Required conversion rules:

- staff selects the target and purpose
- server verifies permission and stage
- server fetches provider media
- Ed calls the correct workflow-aware Drive endpoint
- Drive owns upload, storage, derivatives, grants, and canonical refs
- SPA receives server-owned action URLs only

No external-channel media may bypass the Drive-governed upload contract.

## 8. Scope And Permissions

CRM records must be scoped by:

- organization
- optional school
- channel account
- linked Inquiry
- linked Student Applicant when present
- current staff role and employee scope

Role alone is insufficient. All staff reads and mutations must enforce institutional scope server-side.

For Inquiry-stage records with no school, organization scope is the maximum visibility boundary until staff assigns or corrects school context.

## 9. Concurrency And Request Shape

Provider ingestion must be idempotent.

Required rules:

- dedupe by channel account plus provider message ID
- short synchronous transaction for canonical message truth
- provider media fetch may be deferred when the provider permits it
- no user-visible success may depend on undeployed semantic queue labels
- Inbox page-init must use bounded context endpoints, not request waterfalls
- dashboard/queue summaries must avoid per-row `get_doc` loops

Persistent denormalized counters require a separate invalidation contract before implementation.

## 10. Implementation Phases

### Phase 1: Inquiry Dynamic Capture

- add approved Inquiry triage fields
- update public Inquiry web form conditional behavior
- update Inquiry docs
- keep fields lightweight and informational

### Phase 2: CRM Core Manual Mode

- add planned CRM DocTypes
- implement manual inbound/outbound logging
- implement identity confirmation and link flows
- no provider APIs yet

Status: implemented as Phase 2A backend foundation.

### Phase 3: Admissions Inbox Manual Mode

- add staff Inbox route and bounded context endpoint
- aggregate Inquiry, CRM conversation, and applicant case summaries
- expose server-owned actions only

Status: backend context endpoint implemented as Phase 3A; staff SPA route remains planned.

### Phase 4: Governed Media Conversion

- add explicit import actions from external media metadata into Drive-governed applicant/student/guardian workflows
- add permission and provenance tests

### Phase 5: Provider Adapters

- WhatsApp
- LINE
- Facebook Messenger / Instagram DM
- email adapter only after ownership and inbound threading rules are approved

Each provider adapter must preserve the same CRM storage, scope, dedupe, and media governance contracts.
