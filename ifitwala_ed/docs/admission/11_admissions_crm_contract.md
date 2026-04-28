# Admissions CRM Contract

Status: Partial implementation
Code refs: `ifitwala_ed/admission/doctype/inquiry/inquiry.json`, `ifitwala_ed/admission/web_form/inquiry/inquiry.json`, `ifitwala_ed/admission/web_form/inquiry/inquiry.js`
Test refs: `ifitwala_ed/admission/doctype/inquiry/test_inquiry.py`

This note defines the planned admissions CRM model for Inquiry-stage lead handling and external-channel messaging.

Phase 1 Inquiry dynamic capture is implemented. The CRM DocTypes, Inbox APIs, external-channel ingestion, and media conversion workflows remain planned until their referenced DocTypes, APIs, SPA surfaces, and tests are implemented.

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
- `Admission Conversation`, `Admission Message`, and `Admission CRM Activity` are planned CRM support records around Inquiry-stage and external-channel work.
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

## 5. Planned CRM DocTypes

### 5.1 Admission Channel Account

Represents a school-owned external channel endpoint.

Planned purpose:

- resolve organization and optional school context for inbound messages
- store enabled/disabled state
- define provider type and account identity
- define default routing hints
- hold references to provider secrets without exposing secret values in DTOs

This DocType is operational configuration, not a message ledger.

### 5.2 Admission External Identity

Represents a parent/contact identity on one external provider.

Planned purpose:

- store provider-scoped identity, such as WhatsApp phone, LINE user ID, Facebook PSID, Instagram scoped user ID, or email address
- link explicitly to `Contact`, `Inquiry`, and later `Student Applicant` when confirmed
- track match status and confidence

No fuzzy match may auto-link. Ambiguous matches must become staff decisions.

### 5.3 Admission Conversation

Represents the CRM case thread for Inquiry-stage and external-channel communication.

Planned purpose:

- group Admission Messages around an Inquiry or external identity
- optionally link to `Student Applicant` after conversion for cross-stage timeline display
- own CRM reply-state fields if persistent denormalization is approved

It must not duplicate `Org Communication` portal audience behavior.

### 5.4 Admission Message

Append-only external-channel message and provider audit record.

Planned purpose:

- webhook dedupe
- inbound/outbound direction
- provider message IDs
- delivery/read status
- provider payload summary or raw payload storage when approved
- external media metadata
- provenance link to a related applicant-stage `Org Communication` entry when applicable

It is not the applicant portal message ledger.

### 5.5 Admission CRM Activity

Append-only structured CRM activity record.

Planned purpose:

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

### Phase 3: Admissions Inbox Manual Mode

- add staff Inbox route and bounded context endpoint
- aggregate Inquiry, CRM conversation, and applicant case summaries
- expose server-owned actions only

### Phase 4: Governed Media Conversion

- add explicit import actions from external media metadata into Drive-governed applicant/student/guardian workflows
- add permission and provenance tests

### Phase 5: Provider Adapters

- WhatsApp
- LINE
- Facebook Messenger / Instagram DM
- email adapter only after ownership and inbound threading rules are approved

Each provider adapter must preserve the same CRM storage, scope, dedupe, and media governance contracts.
