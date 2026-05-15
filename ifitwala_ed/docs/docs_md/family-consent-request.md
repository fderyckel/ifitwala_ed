---
title: "Family Consent Request: Operational Forms That Families Sign"
slug: family-consent-request
category: Governance
doc_order: 4
version: "1.0.0"
last_change_date: "2026-04-27"
summary: "Build, publish, and track operational forms—from permission slips and medical consents to data agreements—that guardians and students complete through the portal, with real-time analytics on who signed what and when."
seo_title: "Family Consent Request: Operational Forms That Families Sign"
seo_description: "Learn how to create and manage Family Consent Requests for permission slips, medical consents, and data agreements—with portal signing, real-time tracking, and audit trails."

## What is a Family Consent Request?

A **Family Consent Request** is an operational form that your school publishes to families through the guardian or student portal. Unlike policies (which are broad governance documents), consent requests handle specific, actionable permissions and agreements:

- **Field trip permission slips**
- **Medical treatment consents**
- **Photo and media release forms**
- **Data processing agreements**
- **Emergency contact updates**
- **Any school-specific form that needs a signature**

Each request defines:
- **Who** must sign (guardians, students, or both)
- **What** they are signing (custom text + structured fields)
- **When** it is due (effective dates and deadlines)
- **How** they complete it (portal only, paper only, or mixed)

<Callout type="info" title="Why Family Consent Request is different from Policy Acknowledgement">
Policy Acknowledgements are about governance—broad rules that apply to everyone. Family Consent Requests are about operations—specific permissions and agreements that apply to targeted students. Policies are versioned and diff-tracked; consent requests are built per-need with custom fields and decision modes.
</Callout>

## The Family Consent Ecosystem

### 1. **Family Consent Request** (This DocType)
The form definition: title, text, fields, targets, signer rules, and completion channels.

### 2. **Family Consent Target**
The child table that specifies which students the request applies to. Each target row links a student to the request, scoped by their organization and school.

### 3. **Family Consent Field**
The child table that defines structured fields inside the form—prefilled from profile data, confirmed by the signer, or editable with profile writeback.

### 4. **Family Consent Decision**
The immutable record of what was decided, by whom, when, and through which channel. It forms the audit trail for every signature.

### 5. **Portal Surfaces** — Where Families Interact
| Surface | Who | Experience |
|---------|-----|------------|
| **Guardian Portal** | Parents | Forms & Signatures page listing all pending and completed forms per child |
| **Student Portal** | Students | Forms & Signatures page for self-signing requests |
| **Consent Detail Page** | Guardians / Students | Full form review, prefilled field editing, electronic signature, and submission |
| **Forms & Signatures Analytics** | Staff | Real-time dashboard tracking completion rates, overdue items, and exceptions |

## Request Types

| Type | Use Case | Mutability |
|------|----------|------------|
| **One-off Permission Request** | Single-event permissions like field trips or medical consents | Immutable once decided |
| **Mutable Consent** | Ongoing agreements that families can update over time, like emergency contacts | Latest decision wins; history preserved |

## Subject Scope

| Scope | Meaning |
|-------|---------|
| **Per Student** | Each targeted student gets their own independent consent instance. A guardian with three children sees three separate forms. |
| **Per Family** | One decision covers the entire family. (Reserved for future use; currently the system primarily supports Per Student.) |

## Audience and Signer Rules

| Audience Mode | Signer Rule | Meaning |
|---------------|-------------|---------|
| **Guardian** | Any Authorized Guardian | Only one guardian needs to sign per student |
| **Guardian** | All Authorized Guardians | Every linked guardian must sign |
| **Student** | Student Self | The student signs for themselves |
| **Guardian + Student** | Guardian And Student | Both a guardian and the student must sign |

## Completion Channels

| Channel | How It Works |
|---------|--------------|
| **Portal Only** | Families must complete the form in the guardian or student portal. Staff cannot record paper signatures. |
| **Portal Or Paper** | Families may complete in portal, or staff may record a paper signature through Desk Paper Capture. |
| **Paper Only** | Portal shows the request for transparency, but submission is disabled. Staff must collect and record paper signatures in Desk. |

## Building a Family Consent Request

<Steps title="Creating an Operational Form">
  <Step title="Create the Request">
    Go to **Governance > Family Consent Request > New**. Enter a clear title and select the request type.
  </Step>
  <Step title="Set Scope">
    Choose the Organization and optional School. Only students within this scope can be targeted.
  </Step>
  <Step title="Write the Request Text">
    Use the rich text editor to compose the form instructions, legal text, or explanation. This is what families read before signing.
  </Step>
  <Step title="Attach a Reference Document (Optional)">
    Link a governed file from Ifitwala Drive if families need to review a PDF or other document before signing.
  </Step>
  <Step title="Configure Audience and Signing Rules">
    Select who signs (Guardian, Student, or both) and how many signatures are required.
  </Step>
  <Step title="Set Decision Mode">
    Choose the language families see: Approve/Decline, Grant/Deny, or Acknowledge.
  </Step>
  <Step title="Choose Completion Channel">
    Decide whether the form is portal-only, paper-only, or mixed.
  </Step>
  <Step title="Set Dates">
    Define Effective From, Effective To, and Due On dates. Requests expire automatically after Effective To.
  </Step>
  <Step title="Add Targets">
    In the Targets table, add the students this request applies to. Each row must match the request's organization and school scope.
  </Step>
  <Step title="Add Fields (Optional)">
    In the Fields table, define structured data to collect. Fields can be prefilled from Student or Guardian profiles and optionally written back on submission.
  </Step>
  <Step title="Publish">
    Save as Draft, review, then publish. Once published, the request appears in relevant portals and becomes frozen—its core configuration cannot be changed.
  </Step>
</Steps>

## Form Fields Explained

Family Consent Fields let you collect structured data alongside the signature. Each field has:

| Property | Meaning |
|----------|---------|
| **Field Key** | Machine identifier for the field (auto-generated from label or value source) |
| **Field Label** | Human-readable label shown to the signer |
| **Field Type** | Text, Long Text, Phone, Email, Address, Date, or Checkbox |
| **Value Source** | Optional binding to Student or Guardian profile data (e.g., `Student.student_full_name`) |
| **Field Mode** | Display Only, Confirm Current, or Allow Override |
| **Required** | Whether the signer must provide a value before submitting |
| **Allow Profile Writeback** | If enabled and the field mode is Allow Override, the signer can choose to update their saved profile with the new value |

### Field Modes

| Mode | Behavior |
|------|----------|
| **Display Only** | Shows the prefilled value. Signer cannot change it. |
| **Confirm Current** | Shows the prefilled value and the signer confirms it is still correct. |
| **Allow Override** | Signer can edit the value. If profile writeback is enabled, they may choose to update their profile. |

## The Publishing Freeze

Once a Family Consent Request is published, its core configuration is frozen:
- Title, text, scope, audience, signer rule, decision mode, and fields cannot change
- Targets cannot be added or removed
- This prevents mid-campaign changes that could invalidate signatures already collected

If you need to change a published request:
1. Close or archive the existing request
2. Create a new request with the corrected configuration
3. Republish

<Callout type="warning" title="Published = Frozen">
Do not attempt to edit a published request's text or fields. The controller will reject the save. This is intentional: families who signed version A must not see version B's text retroactively.
</Callout>

## Portal Experience for Families

### Guardian Portal — Forms & Signatures

Guardians see a dedicated **Forms & Signatures** page in their portal. It groups requests by status:

- **Action Needed**: Pending or overdue forms requiring signature
- **Completed**: Forms already approved or granted
- **Declined or Withdrawn**: Forms where the guardian chose not to agree
- **Expired**: Forms that passed their effective-to date

Each card shows the student name, request title, decision mode, due date, and current status. Clicking a card opens the **Consent Detail Page**.

### Consent Detail Page

The detail page is where signing happens:

1. **Request Details**: The full text and any reference document preview
2. **Form Fields**: Prefilled values with optional editing (for Allow Override fields)
3. **Electronic Signature**: Type your full name exactly as recorded
4. **Attestation**: Check the legal confirmation box
5. **History**: See previous decisions for this signer and request
6. **Submit**: Approve/Grant or Decline/Deny

### Student Portal

Students with self-signing requests see the same **Forms & Signatures** page and **Consent Detail Page**, scoped to their own records only.

## Staff Analytics — Forms & Signatures Dashboard

Staff with appropriate roles access **Forms & Signatures Analytics** (`FormsSignaturesAnalytics.vue`) to monitor completion across all requests.

### What the Analytics Page Shows

| Section | Purpose |
|---------|---------|
| **KPI Row** | Total requests, completed, pending, and exceptions (declined + withdrawn + expired + overdue) |
| **Channel Cards** | Breakdown of Portal Only, Portal Or Paper, and Paper Only requests |
| **Request Tracking Table** | Per-request rollup: targets, completed, pending, exceptions, and completion percentage |

### Filters

Staff can filter by:
- Organization and School
- Request Type
- Status (Draft, Published, Closed, Archived)
- Audience Mode (Guardian, Student, Guardian + Student)
- Completion Channel

### Reading the Tracking Table

| Column | Meaning |
|--------|---------|
| **Request** | Title, key, status badge, and request type |
| **Audience** | Audience mode and signer rule |
| **Channel** | How families complete the form |
| **Scope** | Organization and school |
| **Due** | Deadline for completion |
| **Targets** | Number of students targeted |
| **Completed** | Students with Approved/Granted decisions |
| **Pending** | Students awaiting action |
| **Exceptions** | Declined, withdrawn, expired, or overdue |
| **Completion** | Percentage of targets completed |

<Callout type="success" title="Who signed what and when">
The tracking table answers the operational question staff ask every day: "Which parents have signed the field trip form, and who still needs to?" Each row rolls up the latest decision per student, so you see completion status in real time without opening individual records.
</Callout>

## Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|------|------|-------|--------|--------|-------|
| `System Manager` | Yes | Yes | Yes | Yes | Full access |
| `Organization Admin` | Yes | Yes | Yes | Yes | Within scoped organizations |
| `Academic Admin` | Yes | Yes | Yes | Yes | Within scoped organizations |
| `Academic Staff` | Yes | Yes | Yes | No | Can create and edit; no delete |

## Related Docs

<RelatedDocs
  slugs="family-consent-decision,institutional-policy,policy-version,policy-acknowledgement,guardian,student"
  title="Continue With Governance and Family Docs"
/>

## Technical Notes (IT)

- **DocType**: `Family Consent Request` — Located in Governance module
- **Autoname**: `FCR-.YYYY.-.MM.-.####` format
- **Child Tables**: `Family Consent Target` (targets), `Family Consent Field` (fields)
- **Immutable After Publish**: Published requests are frozen via `_freeze_snapshot` comparison in `validate()`
- **Status Lifecycle**: Draft → Published → Closed → Archived

### Key Fields

| Field | Type | Notes |
|-------|------|-------|
| `request_title` | Data | Human-readable title |
| `request_key` | Data | Unique public key for portal references (auto-generated) |
| `request_type` | Select | One-off Permission Request or Mutable Consent |
| `policy_version` | Link → Policy Version | Optional linkage to a governing policy |
| `organization` | Link → Organization | Required; scopes the request |
| `school` | Link → School | Optional; further restricts scope |
| `request_text` | Text Editor | Rich text instructions shown to signers |
| `source_file` | Link → File | Optional governed reference attachment |
| `subject_scope` | Select | Per Student or Per Family |
| `audience_mode` | Select | Guardian, Student, or Guardian + Student |
| `signer_rule` | Select | Any Authorized Guardian, All Authorized Guardians, Student Self, Guardian And Student |
| `decision_mode` | Select | Approve/Decline, Grant/Deny, or Acknowledge |
| `completion_channel_mode` | Select | Portal Only, Portal Or Paper, Paper Only |
| `requires_typed_signature` | Check | Whether signers must type their full name |
| `requires_attestation` | Check | Whether signers must check a legal attestation box |
| `effective_from` | Date | When the request becomes valid |
| `effective_to` | Date | When the request expires |
| `due_on` | Date | Soft deadline shown to families |
| `status` | Select | Draft, Published, Closed, Archived |

### Controller Guards

| Hook | Behavior |
|------|----------|
| `before_insert` | Auto-generate `request_key`; default status to Draft |
| `validate` | Normalize, validate enums, validate scope, validate source file, normalize targets/fields, validate date window, validate status transition and freeze |
| `before_delete` | Block deletion unless status is Draft |

### Vue Pages

| Page | Path | Purpose |
|------|------|---------|
| `FormsSignaturesAnalytics.vue` | `ui-spa/src/pages/staff/analytics/FormsSignaturesAnalytics.vue` | Staff dashboard for tracking form completion across all requests |
| `GuardianConsents.vue` | `ui-spa/src/pages/guardian/GuardianConsents.vue` | Guardian portal listing of pending and completed forms |
| `GuardianConsentDetail.vue` | `ui-spa/src/pages/guardian/GuardianConsentDetail.vue` | Guardian portal form review and signing |
| `StudentConsents.vue` | `ui-spa/src/pages/student/StudentConsents.vue` | Student portal listing of forms |
| `StudentConsentDetail.vue` | `ui-spa/src/pages/student/StudentConsentDetail.vue` | Student portal form review and signing |
| `ConsentDetailView.vue` | `ui-spa/src/components/family_consent/ConsentDetailView.vue` | Shared consent detail component used by both guardian and student detail pages |

### API Integration Points

- `ifitwala_ed.api.family_consent_staff.get_family_consent_dashboard_context` — Filter options for staff analytics
- `ifitwala_ed.api.family_consent_staff.get_family_consent_dashboard` — Analytics data for the tracking table
- `ifitwala_ed.api.family_consent_staff.publish_family_consent_request` — Publish a draft request
- `ifitwala_ed.api.family_consent.get_guardian_consent_board` — Guardian portal board data
- `ifitwala_ed.api.family_consent.get_guardian_consent_detail` — Guardian portal detail data
- `ifitwala_ed.api.family_consent.submit_guardian_consent_decision` — Guardian form submission
- `ifitwala_ed.api.family_consent.get_student_consent_board` — Student portal board data
- `ifitwala_ed.api.family_consent.get_student_consent_detail` — Student portal detail data
- `ifitwala_ed.api.family_consent.submit_student_consent_decision` — Student form submission
