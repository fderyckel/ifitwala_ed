---
title: "Family Consent Decision: Immutable Signature Evidence"
slug: family-consent-decision
category: Governance
doc_order: 5
version: "1.0.0"
last_change_date: "2026-04-27"
summary: "Every portal signature and paper capture creates a permanent, append-only Family Consent Decision—your audit trail for who signed what form, for which student, when, and through which channel."
seo_title: "Family Consent Decision: Immutable Signature Evidence"
seo_description: "Learn how Family Consent Decisions create tamper-proof audit trails for every operational form signature—tracking who, what, when, and how across guardian and student portals."

## What is a Family Consent Decision?

A **Family Consent Decision** is the permanent, append-only record of a family's response to a **Family Consent Request**. It captures exactly:

- **Who** decided — the guardian or student, identified by name and DocType
- **What** they decided — Approved, Declined, Granted, Denied, or Withdrawn
- **When** they decided — server-stamped datetime, not client-reported
- **How** they decided — Guardian Portal, Student Portal, or Desk Paper Capture
- **For whom** — the specific student the decision applies to
- **What they signed** — their typed signature name and attestation confirmation
- **What data they submitted** — a complete JSON snapshot of all field values at decision time

Once created, a Family Consent Decision **cannot be edited or deleted**. It is immutable evidence—designed for audits, disputes, and compliance reviews where "we think they agreed" is not enough.

<Callout type="info" title="Why immutability matters">
In operational form workflows, families sometimes dispute whether they agreed to something. A Family Consent Decision preserves the exact moment, the exact typed signature, the exact field values, and the exact request configuration—forming evidence that holds up under scrutiny.
</Callout>

## How Decisions Are Created

### Guardian Portal Submissions

When a guardian completes a form in the guardian portal:

1. The system validates the guardian has signer authority for the targeted student
2. It checks the request is published and accepts portal submissions
3. It validates typed signature matching (if required) and attestation (if required)
4. It normalizes and validates all field values
5. It applies profile writebacks for fields marked with Allow Profile Writeback
6. It creates a **Family Consent Decision** with source channel `Guardian Portal`
7. It returns the decision name and updated status to the portal

### Student Portal Submissions

When a student completes a self-signing form in the student portal, the same validation and creation flow runs with source channel `Student Portal`.

### Desk Paper Capture

When staff receive a signed paper form, they can record it in Desk:

1. Staff create a new Family Consent Decision manually
2. Source channel must be `Desk Paper Capture`
3. Staff may attach a scanned copy as `source_file`
4. Profile writeback is blocked for paper captures (data integrity rule)
5. The decision is appended to the student's history

<Callout type="warning" title="Paper capture cannot update profiles directly">
If a family changes their address on a paper form, staff must update the profile separately. The system blocks `Update Profile` writeback mode for Desk Paper Capture decisions to prevent unverified data from overwriting canonical records.
</Callout>

## The Decision Lifecycle

### Latest Decision Wins (Mutable Consent)

For **Mutable Consent** requests, the most recent decision determines the current status. A guardian can update their emergency contact information by submitting a new decision. The old decision remains in the history, but the new one governs the current state.

### First Decision Wins (One-off Permission Request)

For **One-off Permission Request** requests, the first decision typically governs. Subsequent decisions may be recorded (for example, a withdrawal), but the operational meaning depends on the request's business rules.

### Superseding Decisions

The `supersedes_decision` field links a newer decision to an older one it replaces. This creates an explicit audit chain rather than relying on timestamps alone.

## Decision Statuses

| Status | Meaning | Typical Use |
|--------|---------|-------------|
| **Approved** | The signer agreed to the request | Approve/Decline mode |
| **Declined** | The signer refused the request | Approve/Decline mode |
| **Granted** | The signer granted permission | Grant/Deny mode |
| **Denied** | The signer denied permission | Grant/Deny mode |
| **Withdrawn** | A previous decision was retracted | Either mode |

## What the Response Snapshot Contains

The `response_snapshot` field stores a JSON object capturing the complete state of the submission:

```json
{
  "field_values": [
    {
      "field_key": "emergency_contact_phone",
      "field_label": "Emergency Contact Phone",
      "value": "+260 97 123 4567",
      "previous_value": "+260 96 765 4321"
    }
  ],
  "profile_writeback_applied": true,
  "profile_writeback_mode": "Update Profile"
}
```

This snapshot ensures that even if field definitions change later, you know exactly what the signer saw and submitted.

## Source Channels and Trust Levels

| Channel | Trust Level | Notes |
|---------|-------------|-------|
| **Guardian Portal** | High | Authenticated user, typed signature matching, attestation required |
| **Student Portal** | High | Authenticated user, typed signature matching, attestation required |
| **Desk Paper Capture** | Medium | Staff-recorded; paper evidence should be scanned and attached |

## Viewing Decisions in Desk

Staff with appropriate roles can view Family Consent Decisions through:

1. **The Family Consent Request form** — see linked decisions in the connections section
2. **The Student record** — see all decisions related to that student
3. **Forms & Signatures Analytics** — see rolled-up completion status per request
4. **Direct DocType access** — Governance > Family Consent Decision

## Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|------|------|-------|--------|--------|-------|
| `System Manager` | Yes | No | No* | No | Read-only; decisions are append-only |
| `Organization Admin` | Yes | No | No* | No | Read-only within scoped organizations |
| `Academic Admin` | Yes | No | No* | No | Read-only within scoped organizations |
| `Academic Staff` | Yes | No | No* | No | Read-only within scoped organizations |
| `Guardian` | Yes | No | No | No | Own decisions only (portal) |
| `Student` | Yes | No | No | No | Own decisions only (portal) |

*Create is allowed only through the portal API or Desk Paper Capture workflow, not through direct DocType creation by most roles.

**Runtime Enforcement:**
- Visibility is enforced via `permission_query_conditions` and `has_permission` hooks
- Staff see decisions scoped by the parent request's organization and school
- Guardians see only their own decisions
- Students see only their own decisions
- No role may edit or delete a decision after creation

## Related Docs

<RelatedDocs
  slugs="family-consent-request,institutional-policy,policy-acknowledgement,guardian,student"
  title="Continue With Governance and Family Docs"
/>

## Technical Notes (IT)

- **DocType**: `Family Consent Decision` — Located in Governance module
- **Autoname**: `FCD-.YYYY.-.MM.-.####` format
- **Immutable**: All edit and delete operations are blocked by controller
- **Append-Only**: New decisions may supersede old ones, but old ones are never modified

### Key Fields

| Field | Type | Notes |
|-------|------|-------|
| `family_consent_request` | Link → Family Consent Request | Required; the form being responded to |
| `student` | Link → Student | Required; the student the decision applies to |
| `decision_by_doctype` | Select | Guardian or Student |
| `decision_by` | Data | The specific guardian or student name |
| `decision_status` | Select | Approved, Declined, Granted, Denied, or Withdrawn |
| `decision_at` | Datetime | Server-stamped; set automatically on insert |
| `typed_signature_name` | Data | What the user typed as their electronic signature |
| `attestation_confirmed` | Check | Whether the legal attestation was checked |
| `source_channel` | Select | Guardian Portal, Student Portal, or Desk Paper Capture |
| `source_file` | Link → File | Optional scanned paper evidence; only allowed for Desk Paper Capture |
| `response_snapshot` | Long Text | JSON snapshot of submitted field values |
| `profile_writeback_mode` | Select | Form Only or Update Profile |
| `supersedes_decision` | Link → Family Consent Decision | Optional link to the decision this one replaces |

### Controller Guards

| Hook | Behavior |
|------|----------|
| `before_insert` | Normalize, validate enums, validate snapshot, validate source file, validate request channel compatibility, stamp `decision_at` |
| `before_save` | Block all edits for existing records |
| `before_delete` | Block all deletions |

### Permission Hooks

| Hook | Behavior |
|------|----------|
| `get_permission_query_conditions` | Scope staff by request organization/school; scope guardians and students to their own decisions |
| `has_permission` | Enforce read-only for all; validate staff scope; validate guardian/student ownership |

### Vue Components

| Component | Path | Purpose |
|-----------|------|---------|
| `ConsentDetailView.vue` | `ui-spa/src/components/family_consent/ConsentDetailView.vue` | Displays request text, fields, signature block, and decision history—submits new decisions via API |
| `FormsSignaturesAnalytics.vue` | `ui-spa/src/pages/staff/analytics/FormsSignaturesAnalytics.vue` | Staff analytics that rolls up latest decisions per request and student |

### API Integration Points

- `ifitwala_ed.api.family_consent.submit_guardian_consent_decision` — Guardian portal submission
- `ifitwala_ed.api.family_consent.submit_student_consent_decision` — Student portal submission
- `ifitwala_ed.api.family_consent_staff.get_family_consent_dashboard` — Staff analytics that reads latest decisions per target
