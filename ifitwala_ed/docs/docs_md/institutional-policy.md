---
title: "Institutional Policy: Unified Governance for Your School"
slug: institutional-policy
category: Governance
doc_order: 1
version: "2.0.7"
last_change_date: "2026-04-25"
summary: "Create and manage institutional policies that flow seamlessly across your organization—from staff signature campaigns to guardian portals, student hubs, and admissions workflows—all with comprehensive analytics and audit trails."
seo_title: "Institutional Policy: Unified Governance for Your School"
seo_description: "Learn how Ifitwala Ed's integrated policy governance connects staff campaigns, guardian acknowledgements, student policies, and admissions requirements in one unified system."

## What is Institutional Policy?

An **Institutional Policy** is the foundation of your school's governance framework. It defines what a policy is, who it applies to, and where it has authority—creating a single source of truth that flows through every corner of your organization.

Unlike disconnected document storage, Ifitwala Ed's policies are **alive**. They appear automatically in the right places:
- **Staff** see policies in their Focus tasks and Morning Brief
- **Guardians** review and sign in their family portal
- **Students** acknowledge in their student hub
- **Applicants** sign during admissions
- **Administrators** track completion in real-time analytics

<Callout type="info" title="Why Ifitwala Ed is different">
Most platforms treat policies as static documents. Ifitwala Ed treats them as **governance workflows**. A single policy identity can cascade through staff signature campaigns, guardian acknowledgements, student requirements, and admissions gates—each with their own signing flow, tracking, and audit trail. It's governance that actually governs.
</Callout>

## The Policy Ecosystem: How It All Connects

### 1. **Policy Identity** (This DocType)
The root definition: what the policy is, who it applies to (Staff, Guardians, Students, Applicants), and where it has scope (Organization-wide or school-specific).

### 2. **Policy Version**
The actual legal text at a point in time. Create new versions when rules change, with automatic diff tracking and version history.

### 3. **Policy Surfaces** — Where People Interact
| Surface | Who | Experience |
|---------|-----|------------|
| **Staff Focus Action** | Employees | ToDo task with inline diff viewer and e-signature |
| **Morning Brief** | Staff | Policy announcements with one-click review |
| **Guardian Portal** | Parents | Family policy library with guardian acknowledgements filtered by signer-authorized linked students |
| **Student Hub** | Students | Age-appropriate policy review and signing |
| **Admissions Portal** | Applicants | Required policy acknowledgements before enrollment |
| **Policy Analytics Dashboard** | Admins | Real-time completion tracking across all audiences |
| **Staff Policy Campaign Overlay** | Admins | Launch targeted internal staff signature tasks |
| **Family Policy Campaign Overlay** | Admins | Publish guardian and student portal notices for one policy version |
| **Policy Inform Overlay** | Everyone | Read-only policy viewer with change history |

### 4. **Policy Acknowledgement**
Immutable evidence of who signed what, when, and which version—forming your audit trail.

## Creating an Institutional Policy

<Steps title="Setting up a New Policy">
  <Step title="Navigate to Governance">
    Go to **Governance > Institutional Policy** and click **New**.
  </Step>
  <Step title="Define the Policy Key">
    Enter a stable machine identifier (e.g., `privacy_policy`, `code_of_conduct`, `media_consent`). This never changes and is used by the system to resolve policies across all surfaces.
  </Step>
  <Step title="Add the Title">
    Enter the human-readable title (e.g., "Student Data Privacy Policy"). This appears in all portals and communications.
  </Step>
  <Step title="Choose Category">
    Select from: Safeguarding, Privacy & Data Protection, Admissions, Academic, Conduct & Behaviour, Health & Safety, Operations, Handbooks, or Employment. Categories help organize the policy library.
  </Step>
  <Step title="Set the Scope">
    Choose the Organization (required) and optionally a specific School. Leave School blank for organization-wide policies that apply to all campuses.
  </Step>
  <Step title="Define Audience">
    Select who this policy applies to: **Applicants**, **Students**, **Guardians**, **Staff**, or any combination. This determines which portals and workflows surface the policy.
  </Step>
  <Step title="Set Admissions Mode (if applicable)">
    For Applicant policies, choose signing mode: Child Acknowledgement, Family Acknowledgement, or Child Optional Consent.
  </Step>
  <Step title="Save">
    Click **Save**. Your policy identity is now ready for versions.
  </Step>
</Steps>

<Callout type="success" title="What happens automatically">
After creating the Institutional Policy, you'll create Policy Versions to hold the actual legal text. Once a version is activated, it automatically appears in all relevant portals and surfaces based on your audience selections.
</Callout>

## Policy Scope and Audience

### Understanding Scope

| Scope Level | What It Means | Example Use Case |
|-------------|---------------|------------------|
| **Organization Only** | Applies to all schools in the organization | Group-wide Data Privacy Policy |
| **Specific School** | Applies to that school and its descendants | Campus-specific uniform policy |

**Important:** School-scoped policies automatically apply to satellite campuses (child schools). This makes multi-campus management effortless.

### Understanding Audience

| Audience | Where They See It | Signing Experience |
|----------|-------------------|-------------------|
| **Applicant** | Admissions portal | Review and acknowledge before enrollment |
| **Student** | Student Hub (`/hub/student/policies`) | Age-appropriate policy review with e-signature |
| **Guardian** | Guardian Portal (`/hub/guardian/policies`) | Mode-aware guardian acknowledgement from signer-authorized linked students: one family row or one row per child |
| **Staff** | Focus tasks, Morning Brief | Inline diff viewer, ToDo-driven workflow |

<Callout type="warning" title="Audience vs. Signer Authority">
Policy audience determines who sees the policy, but not always who can sign. Guardian policies require the guardian to be the primary guardian and to hold the linked signer authority (`can_consent`) for at least one child. Staff always sign for themselves.
</Callout>

### Admissions Acknowledgement Modes

For policies that apply to Applicants:

| Mode | How It Works | Best For |
|------|--------------|----------|
| **Child Acknowledgement** | Applicant signs directly | Older students applying independently |
| **Family Acknowledgement** | Guardian signs on behalf of applicant | Younger children, family decisions |
| **Child Optional Consent** | Student can optionally consent | Media release, optional participation |

## Policy Surfaces in Detail

### 1. Staff Signature Campaigns (Launch Overlay)

Admins launch targeted policy campaigns via the **Staff Policy Campaign Overlay** (`/staff` → Set up campaign):

- **Select scope:** Organization, School, Employee Group
- **Choose policy version:** Any active version
- **Preview audience:** See eligible, signed, and pending counts before launch
- **Set due date:** Optional deadline for completion
- **Launch:** Creates Focus ToDos for all eligible staff

<Callout type="tip" title="Campaign intelligence">
The overlay shows you exactly who will receive tasks, who has already signed, and who has pending ToDos—preventing duplicate work and letting you target precisely.
</Callout>

### 2. Family Policy Campaigns (Portal Notice Overlay)

Admins publish family reminders from the **Family Policy Campaign Overlay** on the Policy Signature Analytics dashboard:

- **Select scope:** Organization and optional School
- **Choose policy version:** Any active version that applies to Guardians, Students, or both
- **Select family audiences:** Guardian, Student, or both
- **Set guardian scope when needed:** For guardian policies, choose `Family Acknowledgement` or `Child Acknowledgement` until the first guardian acknowledgement locks that setting
- **Preview pending counts:** See eligible, signed, and pending totals before publishing
- **Publish:** Creates audience-specific portal communications that deep-link to the exact policy card

<Callout type="tip" title="Notification only">
Family campaigns do not create ToDos, snapshot compliance targets, or replace Policy Acknowledgement evidence. They notify families about durable policy work that already exists.
</Callout>

### 3. Staff Policy Acknowledgement (Focus Action)

Staff sign policies through **Focus** (their task dashboard):

- **ToDo notification:** "Acknowledge [Policy Name]"
- **Inline diff viewer:** See exactly what changed from the previous version
- **Full policy text:** Expand to read complete policy
- **Change summary:** Human-readable description of amendments
- **E-signature:** Type full name + legal attestation checkbox
- **Acknowledgement clauses:** Check required boxes (e.g., "I have read...")

Once signed, the ToDo auto-completes and the acknowledgement is recorded immutably.

### 4. Policy Library (Staff Workspace)

Staff can browse policies anytime via:
- **Morning Brief** policy links
- **Org Communication** policy announcements
- **Policy Library** page at `/hub/staff/policies`

The **Policy Inform Overlay** provides:
- Current policy text
- Visual diff (if amended version)
- Version history table
- Audience chips and neutral workflow labels for guardian/student policies
- Staff acknowledgement status when the selected audience is `Staff`
- Read-only, close-only interface

For policy-admin roles such as **Academic Admin**, the Policy Library can browse `Staff`, `Guardian`, and `Student` policy audiences across the selected organization and school scope. Student and guardian acknowledgement still happens in their own portals.

### 5. Guardian Portal Policies

Guardians access policies at `/hub/guardian/policies`:

- **Policy cards:** Show title, category, version, and scope
- **Status badges:** "Acknowledged" or "Pending acknowledgement"
- **Expandable text:** Read full policy inline
- **Mode-aware scope:** Policies are resolved from signer-authorized linked students, then shown either as one family acknowledgement row or as one row per child
- **E-signature flow:** Same robust signing as staff (name match + attestation)
- **Acknowledgement clauses:** Required checkboxes per policy

Guardians only see policies explicitly scoped to them and where they are the primary guardian with signing authority for at least one child.

### 6. Student Hub Policies

Students access policies at `/hub/student/policies`:

- **Student-appropriate view:** Clean, readable policy cards
- **Progress counters:** Total, Acknowledged, Pending
- **Inline policy reading:** Expand to read without leaving the page
- **Guided signing:** Step-by-step acknowledgement flow
- **Electronic signature:** Type name + legal confirmation

### 7. Admissions Portal Policies

Applicants encounter policies during the admissions process:

- **Required acknowledgements:** Block progression until signed
- **Policy list:** All applicable applicant policies
- **Review & Acknowledge button:** Opens signing overlay
- **Read-only mode:** If application is read-only, policies display without signing
- **Status tracking:** Admissions staff see completion in readiness checks

### 8. Policy Signature Analytics Dashboard

Admins track completion in real-time at `/staff/analytics/policy-signatures`:

**KPIs at a glance:**
- Eligible Signers
- Signed
- Pending
- Completion %

**Audience sections:**
- Staff (with internal task campaign launch capability)
- Guardians (portal acknowledgement tracking plus family campaign publication)
- Students (hub acknowledgement tracking plus family campaign publication)

**Breakdown tables:**
- By Organization
- By School
- By Context (Employee Group for staff)

**Detailed rows:**
- Pending list (who still needs to sign)
- Signed list (recent acknowledgements with timestamps)

<Callout type="success" title="Real-world use case">
A Pastoral Lead filters to their school, selects the current academic year, and sees:
- 87% of staff have signed the new Safeguarding Policy
- 12 guardians still need to acknowledge the Data Privacy update
- 3 students have pending acknowledgements for the Code of Conduct
They click "Publish family campaign" to notify guardians and students, then use "Set up campaign" to assign the remaining staff ToDos.
</Callout>

## Where Policies Are Used

### Admissions Workflow
- Required policies block readiness for enrollment
- Portal shows policy list with completion status
- Admissions staff track via readiness checks
- Policies appear in order they must be acknowledged

### Guardian Engagement
- Parents see policies across their signer-authorized linked family scope
- Guardian durable acknowledgement can be configured per policy version:
  - `Family Acknowledgement` = one guardian acknowledgement per active policy version
  - `Child Acknowledgement` = one guardian acknowledgement row per child in scope
- Historical acknowledgements preserved
- Re-acknowledgement prompted for new versions

### Staff Compliance
- Morning Brief highlights new/updated policies
- Focus ToDos drive completion
- Signature campaigns target specific groups
- Completion analytics track organization-wide compliance

### Student Accountability
- Age-appropriate policy presentation
- Guided acknowledgement flow
- Part of student readiness checks
- Builds digital citizenship skills

### Operational Gates
- Media publishing checks consent policy status
- Activity participation can require current acknowledgements
- Program enrollment gates on policy compliance
- Health services check vaccination policy status

## Managing Policy Lifecycle

### Activating and Deactivating

- **Active policies** participate in resolution and acknowledgement collection
- **Inactive policies** are hidden but preserved for historical reference
- **Never delete**—always deactivate to maintain audit history

### Version Management

1. Create new **Policy Version** when rules change
2. System generates automatic diff from previous version
3. Add **change summary** explaining what changed and why
4. **Activate** new version (automatically deactivates old)
5. Affected audiences see "New version to review" status
6. Re-acknowledgement collected through respective portals

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Create the Institutional Policy before creating Policy Versions.</Do>
  <Do>Use stable, descriptive policy_keys (e.g., `data_privacy_policy`).</Do>
  <Do>Set organization scope first, then refine to school if needed.</Do>
  <Do>Deactivate old policies instead of deleting them.</Do>
  <Do>Use categories consistently for easier management.</Do>
  <Do>Create new versions for material changes—don't edit locked text.</Do>
  <Dont>Change policy_key after creation—it's immutable.</Dont>
  <Dont>Delete policies—deactivate instead.</Dont>
  <Dont>Forget to set audience—policies without audience apply to no one.</Dont>
  <Dont>Create versions before creating the policy identity.</Dont>
</DoDont>

## Common Questions

**Q: What's the difference between Institutional Policy and Policy Version?**
A: Institutional Policy is the identity and scope (what, who, where). Policy Version is the actual legal text at a point in time. You create the policy identity once, then create multiple versions as rules evolve.

**Q: How do I launch a staff signature campaign?**
A: Go to the Policy Signature Analytics dashboard and click "Set up campaign." Select your scope (organization/school/employee group), choose the policy version, preview the audience, and launch. Focus ToDos are created automatically for all eligible staff.

**Q: Can guardians sign for multiple children at once?**
A: It depends on the Policy Version's **Guardian Acknowledgement Mode**. `Family Acknowledgement` means the guardian signs once for the policy version across their eligible family scope. `Child Acknowledgement` means the guardian signs a separate row for each child in scope. Academic Admins can choose that mode in the Family Policy Campaign overlay before the first guardian acknowledgement exists; after that, the mode is locked for audit consistency. Admissions uses its own applicant-stage acknowledgement modes separately.

**Q: How do students sign policies?**
A: Students access their policy library at `/hub/student/policies`. They see policy cards with status, can read the full text inline, and complete a guided signing flow with electronic signature and legal attestation.

**Q: What happens when I update a policy?**
A: You create a new Policy Version with the updated text. The system shows the diff to users. Staff see "New version to review" in Focus. Guardians and students see updated policy cards in their portals. Analytics reset to track the new version's completion.

**Q: How do school-scoped policies interact with organization policies?**
A: The system uses "nearest match" resolution. If both organization and school-level policies exist for the same policy_key, the school-specific one wins for that school and its descendants.

**Q: Can I track policy completion across all audiences?**
A: Yes! The Policy Signature Analytics dashboard shows completion rates for Staff, Guardians, and Students side-by-side, with breakdowns by organization, school, and context.

**Q: What happens to acknowledgements when I deactivate a policy?**
A: Historical acknowledgements are preserved. New acknowledgements are no longer collected. If you reactivate, collection resumes.

**Q: Can applicants see policies before submitting an application?**
A: Yes, applicant-scoped policies appear in the admissions portal. They must acknowledge required policies before their application can be considered complete.

## Permission Matrix

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

## Related Docs

<RelatedDocs
  slugs="policy-version,policy-acknowledgement,organization,school,student-applicant"
  title="Continue With Governance Docs"
/>

## Technical Notes (IT)

- **DocType**: `Institutional Policy` — Located in Governance module
- **Autoname**: `hash` format
- **Immutable Fields**: `policy_key`, `organization` (after creation)
- **One-time Settable**: `school` (can be set if initially blank, then locked)
- **Deletion**: Blocked by controller—use `is_active` instead
- **SPA Surfaces:**
  - Staff Campaign Overlay: `/staff` → Set up campaign
  - Family Policy Campaign Overlay: `/staff/analytics/policy-signatures` → Publish family campaign
  - Policy Library: `/hub/staff/policies`
  - Staff Inform Overlay: Policy read-only viewer
  - Guardian Policies: `/hub/guardian/policies`
  - Student Policies: `/hub/student/policies`
  - Analytics Dashboard: `/staff/analytics/policy-signatures`
