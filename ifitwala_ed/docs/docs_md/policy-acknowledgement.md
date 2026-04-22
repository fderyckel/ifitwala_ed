---
title: "Policy Acknowledgement: Immutable Consent Evidence"
slug: policy-acknowledgement
category: Governance
doc_order: 3
version: "2.0.3"
last_change_date: "2026-04-22"
summary: "Create permanent, tamper-proof records of who acknowledged which policy version, when, and under what context—forming your legal audit trail across staff, guardians, students, and applicants."
seo_title: "Policy Acknowledgement: Immutable Consent Evidence"
seo_description: "Learn how Policy Acknowledgements create permanent, tamper-proof records of policy consent with electronic signatures and audit trails."
---

## What is a Policy Acknowledgement?

A **Policy Acknowledgement** is the permanent, tamper-proof evidence that someone acknowledged a specific policy version. It answers the critical questions that matter in audits, disputes, and compliance reviews:

- **Who** acknowledged the policy
- **What** version they acknowledged
- **When** they acknowledged it
- **How** they acknowledged it (signature, attestation, clauses)
- **In what context** (as staff, guardian, student, or applicant)

Once created, a Policy Acknowledgement cannot be edited, cancelled, or deleted. It is **immutable evidence**—designed for the real world where "we said they agreed" isn't enough; you need proof.

<Callout type="info" title="Why immutability matters">
In traditional systems, consent records can be modified, backdated, or deleted. Ifitwala Ed's Policy Acknowledgements are append-only ledger records. When a parent questions whether they agreed to the media consent policy, you can show the exact timestamp, the typed signature, the clauses they checked, and the version they saw. No he-said-she-said. Just evidence.
</Callout>

---

## The Anatomy of an Acknowledgement

### Who Acknowledged

| Field | What It Records |
|-------|-----------------|
| **Acknowledged By** | The User who performed the acknowledgement |
| **Acknowledged For** | Their role context: Staff, Guardian, Student, or Applicant |
| **Context Record** | The specific Employee, Guardian, Student, or Student Applicant record |

### What Was Acknowledged

| Field | What It Records |
|-------|-----------------|
| **Policy Version** | The exact Policy Version acknowledged |
| **Acknowledged At** | Server-timestamp (cannot be spoofed) |
| **Typed Signature** | Full name as typed for e-signature |
| **Attestation Confirmed** | Whether legal attestation checkbox was checked |
| **Clause Snapshot** | JSON record of which clauses were checked |

<Callout type="success" title="The snapshot principle">
When someone acknowledges a policy, the system captures a snapshot—not just a reference. If the policy clauses change later, the acknowledgement record preserves what the person actually agreed to at that moment. The evidence remains valid even as policies evolve.
</Callout>

---

## How Acknowledgements Are Created

Policy Acknowledgements aren't created manually in Desk. They are the **output** of signing workflows across your organization:

### Staff Acknowledgements

Created when staff complete Focus ToDo tasks:

<Steps title="Staff Signing Flow">
  <Step title="Receive ToDo">
    Staff member receives a Focus task: "Acknowledge [Policy Name]"
  </Step>
  <Step title="Review Policy">
    Open the task to see diff viewer (what changed) or full policy text
  </Step>
  <Step title="Check Clauses">
    Check required acknowledgement clauses (e.g., "I have read...")
  </Step>
  <Step title="Type Signature">
    Type full name exactly as it appears in their employee record
  </Step>
  <Step title="Confirm Attestation">
    Check the legal attestation box
  </Step>
  <Step title="Submit">
    Click "Sign and acknowledge policy"
  </Step>
  <Step title="Evidence Created">
    Policy Acknowledgement record is created; ToDo auto-completes
  </Step>
</Steps>

### Guardian Acknowledgements

Created when guardians sign policies in their portal:

<Steps title="Guardian Signing Flow">
  <Step title="View Policies">
    Guardian navigates to `/hub/guardian/policies`
  </Step>
  <Step title="Select Policy">
    Click on a pending policy card
  </Step>
  <Step title="Read Policy">
    Expand and read the full policy text
  </Step>
  <Step title="Check Clauses">
    Check all required acknowledgement clauses
  </Step>
  <Step title="Type Signature">
    Type their full name as displayed
  </Step>
  <Step title="Confirm Attestation">
    Check legal attestation
  </Step>
  <Step title="Submit">
    Submit the acknowledgement
  </Step>
  <Step title="Evidence Created">
    Policy Acknowledgement is recorded with guardian or student context, depending on the Policy Version's guardian acknowledgement mode
  </Step>
</Steps>

<Callout type="info" title="Guardian family mode vs child mode">
For enrolled students, guardians do not always sign the same way. `Family Acknowledgement` records one guardian self-context acknowledgement for the policy version. `Child Acknowledgement` records one guardian acknowledgement row per child, using the child as the stored context while keeping the audience as `Guardian`.
</Callout>

### Student Acknowledgements

Created through the Student Hub:

- Students see pending policies at `/hub/student/policies`
- Same guided signing flow as guardians
- Acknowledgement recorded with Student context
- Part of student readiness tracking

### Applicant Acknowledgements

Created during the admissions process:

- Applicants see required policies in admissions portal
- May sign directly (child mode) or through guardian (family mode)
- Acknowledgement recorded with `Student Applicant` or `Guardian` context depending on the admissions acknowledgement mode
- Blocks application readiness until complete

---

## The Electronic Signature

Every Policy Acknowledgement includes a **typed electronic signature** with legal attestation. This isn't just clicking "I agree"—it's a deliberate, auditable process:

### Signature Requirements

| Requirement | Why It Matters |
|-------------|----------------|
| **Full name typed exactly** | Proves intentional, deliberate action |
| **Name must match record** | Prevents proxy signatures and errors |
| **Legal attestation checkbox** | Confirms understanding of e-signature legal status |
| **Required clauses checked** | Evidence of specific understandings |
| **Server validation** | Cannot be bypassed by client manipulation |

<Callout type="warning" title="No shortcuts">
The system rejects one-click acknowledgements. Staff cannot just click "Done"—they must type their name, character by character, and confirm they understand this constitutes a legal signature. This deliberate friction is the point.
</Callout>

### What the Signer Sees

Before submitting, signers see:
- **Expected signer name**: "Expected: Jane Smith"
- **Signature preview**: What they typed
- **Timestamp preview**: When it will be recorded
- **Clause checklist**: What they're agreeing to

---

## Acknowledgement Clauses

Policy Versions can define **acknowledgement clauses**—specific statements signers must agree to. These become part of the evidence snapshot.

### Common Clause Types

| Type | Example | Required? |
|------|---------|-----------|
| **Read confirmation** | "I have read and understood this policy" | Yes |
| **Agreement** | "I agree to abide by this policy" | Yes |
| **Awareness** | "I understand the consequences of violation" | Yes |
| **Optional consent** | "I consent to photography for school events" | No |

### Clause Snapshots

When an acknowledgement is created, the system records:
- Which clauses existed on that policy version
- Which clauses were required
- Which clauses the user checked

This means if you later add a new clause to the policy, old acknowledgements remain valid evidence of what was agreed to at the time.

---

## Viewing and Using Acknowledgements

### In Desk

Navigate to **Governance > Policy Acknowledgement** to see all records:

- **List view**: Who acknowledged what, when
- **Filters**: By policy version, date range, context type
- **Export**: For compliance reports and audits

### In Analytics Dashboard

The Policy Signature Analytics dashboard shows:
- Who has acknowledged (signed list)
- Who hasn't (pending list)
- Completion percentages
- Version-specific tracking

### In Applicant Records

For **Student Applicants**, the readiness panel shows:
- Which policies are acknowledged
- Which are pending
- Direct links to view acknowledgements

### In Guardian Portal

Guardians see their own acknowledgement history:
- Acknowledged status per policy row
- One family row or one row per child, depending on the policy version
- Timestamp of acknowledgement
- Cannot be forged or modified

---

## Duplicate Prevention

The system enforces **one acknowledgement per person per policy version per context**. You cannot:
- Acknowledge the same version twice
- Create duplicate records through API manipulation
- Override an existing acknowledgement

If someone tries to acknowledge again, they receive a clear message: "You have already acknowledged this policy."

<Callout type="tip" title="What about new versions?">
When a new Policy Version is activated, acknowledgements reset. Staff, guardians, and students must acknowledge the new version—even if they acknowledged the old one. This is by design: new versions mean new content, which requires new consent.
</Callout>

---

## Audit and Compliance

### What You Can Prove

With Policy Acknowledgements, you can demonstrate:

| Scenario | Evidence Available |
|----------|-------------------|
| Parent claims they didn't agree to media consent | Timestamped acknowledgement with typed signature and clauses |
| Staff disputes they knew the safeguarding rules | Version history, acknowledgement date, diff showing what was current |
| Accreditation requires policy dissemination | Completion reports, pending lists, audit trails |
| Legal discovery requests consent records | Immutable records with full context and signature evidence |

### Retention

Policy Acknowledgements are retained indefinitely. Even if:
- The Policy Version is deactivated
- The Institutional Policy is deactivated
- The user account is deactivated

The acknowledgement record persists as legal evidence.

---

## Common Questions

**Q: Can I edit a Policy Acknowledgement?**
A: No. Policy Acknowledgements are immutable by design. If there was an error in the process, create a new policy version and collect fresh acknowledgements.

**Q: What if someone made a mistake while signing?**
A: The acknowledgement stands as evidence of what occurred. If the signature was clearly wrong (e.g., typed "Mickey Mouse"), you can deactivate the current policy version, create a corrected version, and launch a new signature campaign.

**Q: Can administrators sign on behalf of others?**
A: Only System Managers can bypass certain validations, and these actions are audit-logged. Standard users must sign for themselves.

**Q: How do I export acknowledgement records?**
A: Use the Policy Acknowledgement list in Desk. Apply filters for policy version, date range, or context type, then export to Excel/CSV.

**Q: What's the difference between Policy Version and Policy Acknowledgement?**
A: Policy Version is the legal text. Policy Acknowledgement is the evidence that someone agreed to that text. Think of it as: Version = the contract; Acknowledgement = the signed copy.

**Q: Can I see what clauses someone checked?**
A: Yes. The `acknowledgement_clause_snapshot` field contains JSON showing which clauses were checked at the time of signing.

**Q: What happens to acknowledgements when I delete a user?**
A: Acknowledgements are preserved. The `acknowledged_by` field may reference a deactivated user, but the record remains valid evidence.

---

<RelatedDocs
  slugs="institutional-policy,policy-version,student-applicant,student-log"
  title="Continue With Governance Docs"
/>

---

## Technical Notes (IT)

- **DocType**: `Policy Acknowledgement` — Located in Governance module
- **Autoname**: `hash` format
- **Is Submittable**: Yes (auto-submitted on insert)
- **Immutable**: All edit, cancel, and delete operations are blocked by controller
- **Audit logging**: System Manager overrides are comment-audited

### Key Fields

| Field | Type | Notes |
|-------|------|-------|
| `policy_version` | Link | Required; must be active at time of acknowledgement |
| `acknowledged_by` | Link → User | Required; must match current session user |
| `acknowledged_for` | Select | Applicant, Student, Guardian, or Staff |
| `context_doctype` | Data | Employee, Student, Guardian, or Student Applicant |
| `context_name` | Data | Specific record name |
| `acknowledged_at` | Datetime | Server-stamped; read-only |
| `typed_signature_name` | Data | What the user typed |
| `attestation_confirmed` | Check | Whether attestation was checked |
| `acknowledgement_clause_snapshot` | JSON | Record of checked clauses |

### Controller Guards

| Hook | Behavior |
|------|----------|
| `before_insert` | Validate policy/version, user, context, role, uniqueness, scope, evidence payload |
| `before_save` | Block all edits except draft→submitted transition |
| `before_submit` | Enforce draft→submitted only |
| `before_update_after_submit` | Block all post-submit edits |
| `before_cancel` | Block cancel |
| `before_delete` | Block delete |
| `after_insert` | Auto-submit to submitted evidence state |
| `on_submit` | System Manager override comment when role matrix bypassed |

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|------|------|-------|--------|--------|-------|
| `System Manager` | Yes | Blocked | Yes | Blocked | Controller blocks edit/cancel/delete |
| `Guardian` | Yes | No | Yes | No | Runtime context checks apply |
| `Student` | Yes | No | Yes | No | Runtime context checks apply |
| `Academic Staff` | Yes | No | Yes | No | Self context visibility only |
| `Admission Officer` | Yes | No | No | No | Read-only |
| `Admissions Applicant` | Yes | No | Yes | No | Must match applicant linkage |
| `Admissions Family` | Yes | No | Yes | No | Linked guardian context required |

**Runtime Enforcement:**
- Visibility is enforced via `permission_query_conditions` and `has_permission` hooks
- Guardian access to student-context rows requires primary-guardian signer authority, enforced at runtime through `Student Guardian.can_consent`
- Duplicate tuple enforcement: `(policy_version, acknowledged_by, context_doctype, context_name)`

### API Integration Points

- `ifitwala_ed.api.admissions_portal.acknowledge_policy` — Admissions portal signing
- `ifitwala_ed.api.guardian_policy.acknowledge_guardian_policy` — Guardian portal signing
- `ifitwala_ed.api.focus.acknowledge_staff_policy` — Staff Focus action signing
- `ifitwala_ed.api.policy_signature.get_staff_policy_signature_dashboard` — Analytics data
