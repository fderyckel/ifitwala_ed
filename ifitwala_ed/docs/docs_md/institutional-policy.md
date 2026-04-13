---
title: "Institutional Policy: Manage School Policies with Confidence"
slug: institutional-policy
category: Governance
doc_order: 1
version: "1.6.1"
last_change_date: "2026-04-13"
summary: "Create and manage institutional policies—from data privacy to conduct codes—with scoped applicability, version control, and automated acknowledgement tracking across applicants, students, guardians, and staff."
seo_title: "Institutional Policy: Manage School Policies with Confidence"
seo_description: "Learn how to manage institutional policies in Ifitwala Ed with scoped applicability, version control, and automated acknowledgement tracking."
---

## What is an Institutional Policy?

An **Institutional Policy** is the foundation of your school's governance framework. It defines what a policy is, who it applies to, and where it has authority—from organization-wide rules to school-specific guidelines.

Think of it as the "policy identity" that lives on even as the actual policy text evolves through versions. Whether it's your Code of Conduct, Data Privacy Policy, or Media Consent rules, the Institutional Policy is the anchor that ensures the right people see and acknowledge the right rules at the right time.

<Callout type="info" title="Why Ifitwala Ed is different">
Unlike document storage systems that just file PDFs, Ifitwala Ed's policy framework is alive. It knows which policies apply to which audiences, tracks who has acknowledged what, and automatically gates admissions or activities based on missing signatures. It's governance that actually governs.
</Callout>

---

## Why Institutional Policies Matter

### 1. **Audience-Aware Distribution**
Policies automatically reach the right people. An Applicant policy appears in the admissions portal. A Guardian policy shows in the family portal. Staff policies appear in the staff workspace. No manual list management, no missed communications.

### 2. **Scoped Authority**
Set policies at the organization level (applies to all schools) or specific to individual schools. A parent-school policy automatically cascades to all its satellite campuses. School-specific policies override when needed.

### 3. **Version-Proof Identity**
The Institutional Policy stays constant even as legal text evolves. When you update your Privacy Policy, you're creating a new Policy Version—not breaking historical acknowledgements or confusion about which rules applied when.

### 4. **Acknowledgement Gatekeeping**
Admissions readiness checks automatically flag missing policy acknowledgements. Media publishing is gated behind consent policy status. Staff activities can require current policy signatures. Compliance becomes automatic.

### 5. **Audit-Ready History**
Every policy version, every acknowledgement, every change is permanently recorded. Accreditation visits, legal discovery, or internal reviews—your policy history is complete and unalterable.

---

## Creating an Institutional Policy

<Steps title="Setting up a New Policy">
  <Step title="Navigate to Governance">
    Go to **Governance > Institutional Policy** and click **New**.
  </Step>
  <Step title="Define the Policy Key">
    Enter a stable machine identifier (e.g., `privacy_policy`, `code_of_conduct`, `media_consent`). This never changes and is used by the system to resolve policies.
  </Step>
  <Step title="Add the Title">
    Enter the human-readable title (e.g., "Student Data Privacy Policy"). This is what users see in portals and lists.
  </Step>
  <Step title="Choose Category">
    Select from categories like Safeguarding, Privacy & Data Protection, Admissions, Academic, Conduct & Behaviour, Health & Safety, Operations, Handbooks, or Employment.
  </Step>
  <Step title="Set the Scope">
    Choose the Organization (required) and optionally a specific School. Leave School blank for organization-wide policies.
  </Step>
  <Step title="Define Audience">
    Select who this policy applies to: Applicants, Students, Guardians, Staff, or any combination. You must select at least one.
  </Step>
  <Step title="Set Admissions Mode (if applicable)">
    For Applicant policies, choose how acknowledgements work: Child Acknowledgement, Family Acknowledgement, or Child Optional Consent.
  </Step>
  <Step title="Save">
    Click **Save**. Your policy identity is now created and ready for versions.
  </Step>
</Steps>

<Callout type="tip" title="What happens next">
After creating the Institutional Policy, you'll create Policy Versions to hold the actual legal text. Use the **Create Policy Version** button on the policy form to start your first version.
</Callout>

---

## Policy Scope and Audience

### Understanding Scope

| Scope Level | What It Means | Example Use Case |
|-------------|---------------|------------------|
| **Organization Only** | Applies to all schools in the organization | Group-wide Data Privacy Policy |
| **Specific School** | Applies only to that school and its descendants | Campus-specific uniform policy |

**Important:** When you set a School, that policy applies to the school and all its child schools (satellite campuses). This makes multi-campus management effortless.

### Understanding Audience

| Audience | Where They See It | Typical Policies |
|----------|-------------------|------------------|
| **Applicant** | Admissions portal during application | Enrollment agreements, fee policies |
| **Student** | Student portal durable-policy surface (planned) | Code of conduct, academic integrity |
| **Guardian** | Family portal (`/hub/guardian/policies`) | Data consent, communication policies |
| **Staff** | Staff workspace, Morning Brief | HR policies, safeguarding, data protection |

<Callout type="warning" title="Audience vs. Signer Authority">
Policy audience determines who sees the policy, but not always who can sign. Guardian policies require the guardian to have signer authority (can_consent flag) for a linked child. Staff always sign for themselves.
</Callout>

### Admissions Acknowledgement Modes

For policies that apply to Applicants, choose how signatures are collected:

| Mode | How It Works | Best For |
|------|--------------|----------|
| **Child Acknowledgement** | Applicant (student) signs directly | Older students applying independently |
| **Family Acknowledgement** | Guardian signs on behalf of applicant | Younger children, family decisions |
| **Child Optional Consent** | Student can optionally consent | Media release, optional participation |

---

## Where Policies Are Used

### Admissions Workflow
- Applicants see required policies in their portal
- Missing acknowledgements block readiness for enrollment
- Admissions staff can track completion status
- Policies appear in the order they must be acknowledged

### Guardian Portal
- Guardians can review active guardian-scoped policies in their family portal scope
- Durable acknowledgements are currently stored as guardian-self evidence, filtered by signer-authorized linked children
- Updated policies prompt re-acknowledgement when a new active version replaces the old one
- Historical signatures are preserved for audit

### Student Portal
- Student-scoped durable policy acknowledgement is planned but not yet wired in the current student hub
- Student audience should still be modeled on the Institutional Policy even before the student portal surface ships

### Staff Workspace
- Staff see policies applicable to their role and school
- Morning Brief can highlight new or updated policies
- Signature campaigns can target specific employee groups
- Completion analytics show organization-wide compliance

### Operational Gates
- Media publishing checks consent policy status
- Activity participation can require current acknowledgements
- Program enrollment can gate on policy compliance
- Health services can check vaccination policy status

---

## Managing Policy Lifecycle

### Activating and Deactivating

- **Active policies** participate in resolution and acknowledgement collection
- **Inactive policies** are hidden but preserved for historical reference
- **Never delete**—always deactivate to maintain audit history

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Create the Institutional Policy before creating Policy Versions.</Do>
  <Do>Use stable, descriptive policy_keys (e.g., `data_privacy_policy`).</Do>
  <Do>Set organization scope first, then refine to school if needed.</Do>
  <Do>Deactivate old policies instead of deleting them.</Do>
  <Do>Use categories consistently for easier management.</Do>
  <Dont>Change policy_key after creation—it's immutable.</Dont>
  <Dont>Delete policies—deactivate instead.</Dont>
  <Dont>Forget to set audience—policies without audience apply to no one.</Dont>
  <Dont>Create versions before creating the policy identity.</Dont>
</DoDont>

---

## Common Questions

**Q: What's the difference between Institutional Policy and Policy Version?**
A: Institutional Policy is the identity and scope (what, who, where). Policy Version is the actual legal text at a point in time. You create the policy identity once, then create multiple versions as rules evolve.

**Q: Can I move a policy to a different organization?**
A: No, organization is immutable after creation. This preserves audit integrity. Create a new policy in the target organization if needed.

**Q: What happens when I update a policy?**
A: You create a new Policy Version with the updated text. The system can show the diff to users. Depending on your settings, existing acknowledgements may remain valid or prompt re-signature.

**Q: How do school-scoped policies interact with organization policies?**
A: The system uses "nearest match" resolution. If both organization and school-level policies exist for the same policy_key, the school-specific one wins for that school and its descendants.

**Q: Can a policy apply to multiple audiences?**
A: Yes—select any combination of Applicant, Student, Guardian, and Staff. The policy will appear in all relevant portals and workflows.

**Q: What happens to acknowledgements when I deactivate a policy?**
A: Historical acknowledgements are preserved. New acknowledgements are no longer collected. If you reactivate, collection resumes.

**Q: How do I track who hasn't signed a policy?**
A: Use the Policy Acknowledgement report or check the analytics in the staff workspace. You can see completion rates by organization, school, or employee group.

---

<RelatedDocs
  slugs="policy-version,policy-acknowledgement,organization,school,student-applicant"
  title="Continue With Governance Docs"
/>

---

## Technical Notes (IT)

- **DocType**: `Institutional Policy` — Located in Governance module
- **Autoname**: `hash` format
- **Immutable Fields**: `policy_key`, `organization` (after creation)
- **One-time Settable**: `school` (can be set if initially blank, then locked)
- **Deletion**: Blocked by controller—use `is_active` instead

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|------|------|-------|--------|--------|-------|
| `System Manager` | Yes | Yes | Yes | Blocked | Controller blocks delete |
| `Organization Admin` | Yes | Yes | Yes | Blocked | Controller blocks delete |
| `Accounts Manager` | Yes | Yes | Yes | Blocked | Controller blocks delete |
| `Admission Manager` | Yes | Yes | Yes | Blocked | Controller blocks delete |
| `Academic Admin` | Yes | Yes | Yes | Blocked | Controller blocks delete |
| `HR Manager` | Yes | Yes | Yes | Blocked | Controller blocks delete |
| `Academic Staff` | Yes | No | No | No | Read-only access |
| `Accreditation Visitor` | Yes | No | No | No | Read-only for audits |

**Management Scope:** Policy admins may manage policies rooted in their base organization or descendant organizations. Read visibility is enforced through scope hooks.
