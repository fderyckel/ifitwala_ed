---
title: "Policy Version: The Living Legal Text"
slug: policy-version
category: Governance
doc_order: 2
version: "2.0.1"
last_change_date: "2026-04-16"
summary: "Create versioned policy text with automatic diff tracking. When rules change, publish amendments that surface everywhere—from staff Focus tasks with inline change viewers to guardian and student portals—while preserving complete audit history."
seo_title: "Policy Version: Versioned Legal Text with Diff Tracking"
seo_description: "Learn how Policy Versions track changes, show diffs, and surface across staff, guardian, and student portals with automatic version management and audit trails."
---

## What is a Policy Version?

A **Policy Version** is the actual legal text of a policy at a specific point in time. It brings your **Institutional Policy** to life—turning an identity into content that people can read, review, and acknowledge.

Here's where it gets powerful: **Policy Versions are versioned and diff-tracked**. When you update a policy, you create a new version. The system automatically compares it to the previous version, highlighting exactly what changed. Staff see this diff in their Focus tasks. Guardians and students see "updated policy" indicators. Everyone knows what's new.

<Callout type="info" title="Why versioned policies matter">
Static document storage hides changes. Ifitwala Ed surfaces them. When the Safeguarding Policy gets updated, staff don't just see a new document—they see a side-by-side diff showing exactly which clauses changed. This isn't just convenience—it's legal transparency and risk management.
</Callout>

---

## The Policy Version Lifecycle

### 1. **Draft**
Create a new version and write the policy text. It exists but doesn't affect anyone yet.

### 2. **Active**
Activate the version to publish it. It becomes the current version for its Institutional Policy scope. Previous versions are automatically deactivated.

### 3. **Archived**
When superseded by a newer version, the old version remains visible for reference and audit—but new acknowledgements are collected against the current version.

---

## Creating a Policy Version

<Steps title="Publishing Policy Text">
  <Step title="Navigate to the Policy">
    Go to **Governance > Institutional Policy**, find your policy, and click **New Version** (or go to **Governance > Policy Version > New** and select the policy).
  </Step>
  <Step title="Verify the Parent Policy">
    Confirm the Institutional Policy is correct. This cannot be changed after creation.
  </Step>
  <Step title="Add Version Label">
    Enter a human-readable label (e.g., "2024-2025 Academic Year", "V2.1", "Post-Incident Update"). This helps people identify which version they're signing.
  </Step>
  <Step title="Write or Paste Policy Text">
    Enter the full policy content in the rich text editor. This supports formatted text, lists, and structured content.
  </Step>
  <Step title="Add Acknowledgement Clauses">
    Define what signers must agree to. Examples: "I have read this policy," "I agree to follow these rules," "I understand the consequences of violation."
  </Step>
  <Step title="Save as Draft">
    Click **Save**. The version is now a draft—you can edit freely.
  </Step>
  <Step title="Review the Diff (if applicable)">
    If a previous version exists, the system will show what changed. Review to ensure the diff accurately reflects your intent.
  </Step>
  <Step title="Activate">
    Click **Activate**. The version goes live and appears in all relevant portals.
  </Step>
</Steps>

<Callout type="success" title="What happens on activation">
When you activate a Policy Version:
- It becomes the current version for its scope
- Previous versions are automatically deactivated
- Staff see "New version to review" in Focus
- Guardians see updated policy cards in their portal
- Students see updated policy cards in their hub
- Analytics reset to track this version's completion
- Diff is available for change comparison
</Callout>

---

## Acknowledgement Clauses

Acknowledgement clauses are the specific agreements signers must confirm. They create legal clarity and audit evidence.

### Clause Types

| Field | Purpose | Example |
|-------|---------|---------|
| **Clause Text** | What the signer agrees to | "I have read and understood this policy" |
| **Is Required** | Must be checked to complete signing | Required for legal attestation clauses |
| **Display Order** | Sort order in the signing flow | Lower numbers appear first |

<DoDont doTitle="Best Practice" dontTitle="Avoid">
  <Do>Use 2-3 clauses maximum to reduce signing friction.</Do>
  <Do>Make the final clause a legal attestation (required).</Do>
  <Do>Write in clear, active language: "I agree to..." "I understand that..."</Do>
  <Do>Test the signing flow yourself before launching a campaign.</Do>
  <Dont>Create 10+ clauses—signers will abandon.</Dont>
  <Dont>Use vague language like "I acknowledge things."</Dont>
  <Dont>Make all clauses optional—at least require the legal attestation.</Dont>
</DoDont>

---

## How Versions Surface Across Your Organization

### Staff Focus Tasks

When a staff member has a pending policy acknowledgement, their Focus ToDo shows:

```
ToDo: Acknowledge Data Privacy Policy (V2.1)
```

Opening the ToDo reveals the **Staff Policy Acknowledge Action**:
- **Policy title and version** clearly displayed
- **Scope information** (organization, school)
- **Due date** from the campaign
- **Two tabs:** Changes | Full policy
- **Diff viewer** (if applicable): visual comparison with previous version
- **Change summary** (if provided): human-readable explanation
- **Acknowledgement clauses**: checkbox list
- **Electronic signature**: type full name + attestation checkbox

<Callout type="tip" title="Diff magic">
The diff viewer highlights added text in green, removed text in red, and modified sections with before/after comparison. Staff can see at a glance what changed without reading the entire policy again.
</Callout>

### Morning Brief Policy Links

Policies mentioned in Morning Brief open the **Policy Inform Overlay**:
- Shows current version by default
- Tabs: Changes | Full policy
- Version history table (Active vs Historical)
- Acknowledgement status
- Read-only—cannot sign from here

### Guardian Portal

Guardians see policy versions in `/hub/guardian/policies`:
- **Policy card** shows title, category, version label
- **Status badge**: "Acknowledged" or "Pending acknowledgement"
- **Expandable text** with full policy content
- **Acknowledgement section** (if pending):
  - Clause checkboxes
  - Expected signer name display
  - Full name input for e-signature
  - Legal attestation checkbox
  - Timestamp preview

### Student Hub

Students see similar policy cards in `/hub/student/policies`:
- Clean, age-appropriate presentation
- Progress counters (Total, Acknowledged, Pending)
- Inline policy reading
- Guided signing flow

### Admissions Portal

Applicants encounter policies with version tracking:
- Version label shown in policy list
- Review overlay displays full version text
- Acknowledgement records version signed
- Application readiness tracks version completion

### Policy Analytics Dashboard

Admins see version-specific analytics at `/staff/analytics/policy-signatures`:
- Filter by specific Policy Version
- Track completion rate for that version
- Compare to previous version completion
- Identify who signed old vs new versions

---

## Amending Policies: The Update Workflow

<Steps title="Updating a Policy">
  <Step title="Review Current Version">
    Go to the active Policy Version and review its content.
  </Step>
  <Step title="Create New Version">
    Click **New Version** (or create manually with same Institutional Policy).
  </Step>
  <Step title="Write Changes">
    Enter the updated policy text. Include all content—don't just write the changes.
  </Step>
  <Step title="Add Change Summary">
    Write a clear explanation: "Updated Section 3 to include new data retention rules following GDPR guidance."
  </Step>
  <Step title="Adjust Clauses if Needed">
    Add, remove, or modify acknowledgement clauses based on policy changes.
  </Step>
  <Step title="Save and Review Diff">
    Save the draft and review the automatic diff. Ensure it captures your changes accurately.
  </Step>
  <Step title="Activate">
    Click **Activate**. The new version goes live; old version is archived.
  </Step>
  <Step title="Launch Campaign (if staff policy)">
    For staff policies, go to Analytics and launch a signature campaign to collect acknowledgements.
  </Step>
</Steps>

<Callout type="warning" title="Version immutability">
Once activated, Policy Version text cannot be edited. This preserves audit integrity. If you find an error, deactivate and create a new version. Never edit active policy text.
</Callout>

---

## Understanding the Diff Viewer

The diff viewer appears in:
- Staff Focus actions
- Morning Brief policy overlays
- Policy Library in staff workspace

### What It Shows

| Indicator | Meaning |
|-----------|---------|
| **Green highlighting** | New text added in this version |
| **Red strikethrough** | Text removed from previous version |
| **Side-by-side** | Before and after for modified sections |
| **Change stats** | Count of additions, removals, modifications |

### Diff vs Full Policy

| Tab | When to Use |
|-----|-------------|
| **Changes** | Quick review of what's new (recommended for updates) |
| **Full policy** | First-time readers, complete legal review |

<Callout type="tip" title="Change summary matters">
While the diff shows technical changes, the Change Summary field lets you explain the *why*. "Updated data retention from 2 years to 3 years per new legal guidance" is more helpful than just seeing text change.
</Callout>

---

## Version History and Audit

Every Policy Version maintains:

- **Creation date and time**
- **Creator** (user who created the version)
- **Activation date and time**
- **Activation user**
- **Status history** (Draft → Active → Archived)
- **Acknowledgement records** linked to this version

### Accessing History

- **In Desk:** Policy Version list shows all versions
- **In SPA overlays:** Version history table shows Active vs Historical
- **In Analytics:** Filter by specific version

<Callout type="info" title="Audit readiness">
Policy versions and acknowledgements form your legal audit trail. If questioned about who knew what when, you can show: (1) the exact text of the policy at that time, (2) who acknowledged it, (3) when they acknowledged it, and (4) what version they saw.
</Callout>

---

## Where You'll Use Policy Versions

### Legal Compliance
- Track exactly which version of each policy was in effect
- Prove dissemination to affected parties
- Show timely updates following regulatory changes

### Staff Onboarding
- New hires acknowledge current versions
- Return-to-work staff review updated policies
- Role changes may trigger new policy acknowledgements

### Annual Reviews
- Refresh handbook policies yearly
- Create new versions with updated dates
- Launch signature campaigns for all staff

### Incident Response
- Rapid policy updates following incidents
- Emergency versions with accelerated acknowledgment
- Version rollback if needed (activate previous)

### Accreditation
- Export version history for inspectors
- Show systematic policy management
- Demonstrate distribution and acknowledgement tracking

---

<RelatedDocs
  slugs="institutional-policy,policy-acknowledgement,staff-focus,morning-brief"
  title="Continue With Governance Docs"
/>

---

## Technical Notes (IT)

- **DocType**: `Policy Version` — Located in Governance module
- **Parent**: Must link to one `Institutional Policy`
- **Immutable after activate**: `policy_text`, acknowledgements recorded against this text
- **Status states**: Draft → Active → Archived (or Deactivated)
- **Diff generation**: Automatic comparison with previous active version
- **Diff HTML**: Sanitized server-side before display
- **SPA Surfaces with version display:**
  - Staff Focus Action: Shows version label, diff viewer, full text
  - Policy Inform Overlay: Version tabs, history table
  - Guardian Portal: Version label on policy cards
  - Student Hub: Version label on policy cards
  - Admissions Portal: Version in policy list
  - Analytics Dashboard: Version filter and tracking

### Permission Matrix

| Role | Read | Write | Create | Delete | Activate |
|------|------|-------|--------|--------|----------|
| `System Manager` | Yes | Draft only | Yes | Draft only | Yes |
| `Organization Admin` | Yes | Draft only | Yes | Draft only | Yes |
| `HR Manager` | Yes | Draft only | Yes | Draft only | Yes |
| `Academic Admin` | Yes | Draft only | Yes | Draft only | Yes |
| `Academic Staff` | Yes | No | No | No | No |

**Notes:**
- Active versions are read-only for all roles
- Only draft versions can be edited or deleted
- Activation requires Policy Signature Manager roles
- Acknowledgements are linked to specific version records
