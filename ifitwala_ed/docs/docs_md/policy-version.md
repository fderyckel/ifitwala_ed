---
title: "Policy Version: Publish and Track Policy Changes"
slug: policy-version
category: Governance
doc_order: 2
version: "1.7.0"
last_change_date: "2026-04-11"
summary: "Create immutable policy text versions with automatic diff tracking, acknowledgement clauses, and controlled activation for applicants, guardians, and staff."
seo_title: "Policy Version: Publish and Track Policy Changes"
seo_description: "Learn how to create, publish, and version control your institutional policies with automated diff tracking and acknowledgement management."
---

## What is a Policy Version?

A **Policy Version** is the actual legal text of a policy at a specific point in time. While the Institutional Policy defines what the policy is and who it applies to, the Policy Version contains the words people read and acknowledge.

Think of it like this:
- **Institutional Policy** = The book title and catalog information
- **Policy Version** = The actual content of each edition

When your Privacy Policy needs updating, you don't edit the old text—you create a new Policy Version. This preserves the historical record, maintains audit trails, and lets you track exactly what was acknowledged when.

<Callout type="info" title="Why Ifitwala Ed is different">
Unlike simple document uploads that lose history, Ifitwala Ed's Policy Versions create an immutable legal record. Once published, the text is locked. Changes require new versions with automatic diff comparison. You can see exactly what changed between versions—down to the paragraph level—and users see a clear change summary before re-acknowledging.
</Callout>

---

## Why Policy Versions Matter

### 1. **Immutable Legal Record**
Once a version is activated or acknowledged, its text is permanently locked. No accidental edits, no "I thought I saved it" moments. Your legal history is preserved exactly as it was published.

### 2. **Automatic Diff Tracking**
When you create a new version based on an old one, the system automatically generates a visual diff showing what changed. Users see additions, deletions, and modifications clearly marked before they acknowledge.

### 3. **Acknowledgement Clauses**
Define specific checkboxes users must tick—"I have read the policy," "I consent to data processing," "I understand the consequences." These become part of the legal record.

### 4. **Controlled Activation**
Only one version can be active at a time per policy. Draft versions let you perfect the text with stakeholders before going live. Schedule effective dates for planned policy rollouts.

### 5. **Complete Audit Trail**
Who approved this version? When did it become active? How many people acknowledged it? Every action is timestamped and attributed. Accreditation and legal compliance made simple.

---

## Creating a Policy Version

<Steps title="Publishing a New Policy Version">
  <Step title="Open the Parent Policy">
    Navigate to the Institutional Policy you want to version. Click **Create Policy Version**.
  </Step>
  <Step title="Set Version Label">
    Enter a version label (e.g., "v1", "v2.1", "2024-Update"). This must be unique within the policy.
  </Step>
  <Step title="Write the Policy Text">
    Use the rich text editor to compose your policy. Include all legal language, formatting, and structure.
  </Step>
  <Step title="Add Acknowledgement Clauses">
    Define what users must check to acknowledge: "I have read and understood this policy," "I consent to X," etc.
  </Step>
  <Step title="Set Effective Dates (Optional)">
    Specify when this version becomes effective and when it expires. Useful for planned policy transitions.
  </Step>
  <Step title="Get Approval">
    Select the person who approved this version. They must have write access and be within the policy scope.
  </Step>
  <Step title="Activate">
    Check **Is Active** to publish. The previous active version is automatically deactivated. Only one version can be active at a time.
  </Step>
</Steps>

<Callout type="success" title="First version vs. amendments">
For your first version, the form opens blank. For amendments, click **Create Amendment** on an existing version to prefill with the previous text, copy the policy context, and suggest the next version label.
</Callout>

---

## Creating Policy Amendments

When you need to update an existing policy, create an amendment rather than editing the locked text.

<Steps title="Amending an Existing Policy">
  <Step title="Open Current Version">
    Find the active Policy Version you want to update. Click **Create Amendment**.
  </Step>
  <Step title="Review Auto-Prefilled Data">
    The system copies the policy text, sets the based-on version, and suggests a new version label (v1 → v2, etc.).
  </Step>
  <Step title="Document Changes">
    Fill in the **Change Summary**—a human-readable description of what changed and why. This is required for amendments.
  </Step>
  <Step title="Edit the Text">
    Modify the policy text. The system will automatically generate a diff showing what changed.
  </Step>
  <Step title="Review Diff">
    Check the auto-generated **Diff HTML** to ensure changes are captured correctly.
  </Step>
  <Step title="Activate">
    Save and activate. Users will see the change summary and diff when they next access the policy.
  </Step>
</Steps>

<Callout type="tip" title="Communication integration">
When you share a policy, the system can create an Org Communication with Morning Brief distribution. Staff see the policy in their daily briefing with a link to read and acknowledge.
</Callout>

---

## Policy Version Fields Explained

| Field | What It's For | Tips |
|-------|---------------|------|
| **Institutional Policy** | The parent policy identity | Auto-filled when created from policy; cannot change |
| **Version Label** | Human-readable version ID | Use semantic versioning (v1, v2.1) or dates (2024-01) |
| **Based On Version** | Previous version this amends | Required for amendments; creates diff automatically |
| **Policy Text** | The actual legal content | Use formatting, headings, and clear language |
| **Change Summary** | What changed and why | Required for amendments; shown to users before acknowledgement |
| **Diff HTML** | Visual comparison | Auto-generated from Based On Version; read-only |
| **Change Stats** | Metrics (paragraphs changed, etc.) | Auto-generated; read-only |
| **Acknowledgement Clauses** | Required checkboxes | Create specific consent items users must agree to |
| **Effective From/To** | Validity period | Optional; useful for scheduled policy updates |
| **Approved By/On** | Approval record | Shows who authorized this version |
| **Is Active** | Published status | Only one version per policy can be active |

---

## Locking and Immutability

### When Text Locks

Policy text becomes uneditable when:
1. **Activated** — The version is marked Is Active
2. **Acknowledged** — Anyone acknowledges this version

Once locked, text changes require creating a new version. This preserves legal integrity.

### Override (Emergency Only)

System Managers can override locks with an explicit reason, which is audit-logged. Use only for critical corrections, never for routine updates.

<Callout type="warning" title="Lock after adoption">
After activation or first acknowledgement, policy text is permanently locked. Always review carefully before activating. If you find an error, create a new version rather than trying to edit the locked one.
</Callout>

---

## Sharing and Communicating Policies

### Share Policy Button

Use **Share Policy** on any version to:
- Create an Org Communication draft
- Default to one-week Morning Brief window
- Target appropriate audiences based on policy scope
- Preselect recipients from the Applies To settings
- Optionally launch a staff signature campaign

### Audience Targeting

The share dialog respects your policy scope:
- **School-scoped policies**: Offer School and Team audiences
- **Organization-wide staff policies**: Offer Organization Staff audience
- **Mixed-audience policies**: Offer Schools in Organization, School, and Team

### Staff Signature Campaigns

For staff policies, enable the optional signature campaign:
- Targets employees by organization, school, and employee group
- Creates ToDos for pending signatures
- Tracks completion in analytics
- Reminds through Morning Brief

---

## Where Policy Versions Appear

### Admissions Portal
Applicants see the active version of Applicant policies. They must acknowledge before progressing through admissions stages. Missing acknowledgements block readiness.

### Guardian Portal
Parents see active Guardian policies for their linked children. They acknowledge once per policy per child (or family-wide depending on settings). Historical acknowledgements are preserved.

### Staff Workspace
Staff see active Staff policies in their policy library. Morning Brief highlights new or updated policies. Signature campaigns create actionable ToDos.

### Policy Inform Overlay
Clicking a policy link opens a read-only overlay showing:
- Current policy text
- Change summary (if amended)
- Visual diff (if amended)
- Acknowledgement clauses
- Action buttons to acknowledge

---

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Create a new version for every material policy change.</Do>
  <Do>Write clear change summaries explaining what changed and why.</Do>
  <Do>Review the auto-generated diff before activating.</Do>
  <Do>Use effective dates for planned policy transitions.</Do>
  <Do>Share new versions through Morning Brief for visibility.</Do>
  <Do>Deactivate old Institutional Policies rather than deleting.</Do>
  <Dont>Edit text after activation—create a new version instead.</Dont>
  <Dont>Skip the change summary for amendments.</Dont>
  <Dont>Activate without reviewing acknowledgement clauses.</Dont>
  <Dont>Create multiple active versions of the same policy.</Dont>
</DoDont>

---

## Common Questions

**Q: Can I edit a policy after activating it?**
A: No. Once active (or acknowledged), the text is locked. Create a new Policy Version instead. This preserves the legal record.

**Q: What happens to old acknowledgements when I publish a new version?**
A: Historical acknowledgements remain valid for the version they signed. Depending on your settings, users may need to re-acknowledge the new version for certain activities.

**Q: How do I see what changed between versions?**
A: The system auto-generates a visual diff. Open the newer version and look at the Diff HTML field—it highlights additions, deletions, and modifications.

**Q: Can I schedule a policy to activate later?**
A: Yes, use the Effective From date. However, the version must still be marked Is Active. The date is for reference and reporting.

**Q: What if I find a typo in an active policy?**
A: For minor typos, System Managers can override with an audit reason. For substantive changes, create a new version. When in doubt, create a new version—it's safer legally.

**Q: How do users know a policy has been updated?**
A: When you share the policy through Morning Brief or Org Communication, users see the change summary. The policy inform overlay shows the diff when they view it.

**Q: Can I have draft versions while another is active?**
A: Yes. You can create and edit draft versions while another version is active. Only activate the new version when ready to publish.

**Q: What happens if I deactivate the active version?**
A: The policy no longer appears in portals for new acknowledgements. Historical acknowledgements are preserved. If this was the only active version, the policy effectively becomes unavailable until a new version is activated.

---

<RelatedDocs
  slugs="institutional-policy,policy-acknowledgement,student-applicant,org-communication"
  title="Continue With Governance Docs"
/>

---

## Technical Notes (IT)

- **DocType**: `Policy Version` — Located in Governance module
- **Autoname**: `GOV-POL-VER-.####` format
- **Locking**: Text locks when `is_active=1` OR acknowledgements exist
- **Amendment Chain**: `based_on_version` links versions in a chain
- **Diff Generation**: Server-side generation from previous version text

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|------|------|-------|--------|--------|-------|
| `System Manager` | Yes | Yes | Yes | Blocked | Can override locks with reason |
| `Organization Admin` | Yes | Yes | Yes | Blocked | Full version management |
| `Accounts Manager` | Yes | Yes | Yes | Blocked | Full version management |
| `Admission Manager` | Yes | Yes | Yes | Blocked | Full version management |
| `Academic Admin` | Yes | Yes | Yes | Blocked | Full version management |
| `HR Manager` | Yes | Yes | Yes | Blocked | Full version management |
| `Employee` | Yes | No | No | No | Read-only access |
| `Accreditation Visitor` | Yes | No | No | No | Read-only for audits |

**Lock Rules:**
- `policy_text` and `acknowledgement_clauses` editable only while Draft (`is_active=0`) and no acknowledgements
- Once active or acknowledged, fields are lock-protected
- Only System Manager with explicit `flags.override_reason` can override
- All overrides are comment-audited

**Approval Scope:**
- School-scoped policies: Approver must belong to same school or ancestor
- Organization-scoped: Approver must belong to same organization or ancestor
