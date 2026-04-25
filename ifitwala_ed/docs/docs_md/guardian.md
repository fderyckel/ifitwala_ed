---
title: "Guardian: Manage Family Relationships and Portal Access"
slug: guardian
category: Students
doc_order: 3
version: "1.0.0"
last_change_date: "2026-04-25"
summary: "Understand how Guardian records connect families to students, enable portal access, and manage consent, finance, and communication workflows across your school."
seo_title: "Guardian: Manage Family Relationships and Portal Access"
seo_description: "Learn how to create and manage Guardian records in Ifitwala Ed—from admissions-linked families to portal users, primary guardians, and financial guardians."
---

## What is a Guardian?

A **Guardian** is the family-side identity record in Ifitwala Ed. It represents a parent, legal guardian, or other authorized adult who has a relationship with one or more students in your school.

Guardians are the bridge between your school and families. Every guardian record can:
- Be linked to one or more students with a defined relationship
- Receive portal access to view their children's information
- Act as a primary contact for school communications
- Be designated as the financial guardian for billing and invoices
- Provide electronic consent for policies, permissions, and medical decisions

<Callout type="info" title="Why Guardian is separate from Student">
Ifitwala Ed treats Guardian as a first-class identity, not just a field on the Student record. This means one guardian can be linked to multiple children, a guardian can exist before a student is enrolled, and family relationships are preserved even when students graduate or transfer.
</Callout>

## How Guardians Are Created

There are two ways Guardian records enter the system:

### 1. **Admissions Pipeline (The Normal Path)**

The standard way guardians are created is through the admissions workflow:

`Inquiry → Student Applicant → Guardians captured on application → Promoted to Student → Guardian records created automatically`

When a student applicant is promoted:
- Guardian records are created from the applicant's guardian rows
- Each guardian is linked to the new Student record
- Portal user accounts are created for guardians with email addresses
- Primary and financial guardian flags are preserved

### 2. **Direct Creation (For Existing Students)**

For students already in the system, staff can create Guardian records directly and link them manually. This is useful when:
- A new guardian joins an existing family
- You are onboarding a school with existing student data
- A guardian was missed during the admissions workflow

<Callout type="warning" title="Guardian creation requires an email for portal access">
A guardian can exist without an email, but they will not receive portal access. To create a portal user later, use the "Create Guardian User" action on the Guardian form.
</Callout>

## Guardian Fields Explained

### Identity

| Field | What It Means | Example |
|-------|---------------|---------|
| **First Name** | Guardian's given name | Maria |
| **Last Name** | Guardian's family name | González |
| **Full Name** | Auto-computed from first + last | Maria González |
| **Gender** | Guardian's gender | Female |
| **Salutation** | Formal title | Ms., Dr., Prof. |
| **Photo** | Profile image for portal and communications | Uploaded portrait |

### Contact Information

| Field | What It Means | Example |
|-------|---------------|---------|
| **Personal Email** | Primary email address; becomes portal username | maria@example.com |
| **Mobile Phone** | Primary mobile number | +260 97 123 4567 |
| **User ID** | Linked Frappe User account for portal access | maria@example.com |

<Callout type="info" title="Contact and Address integration">
When a Guardian is saved, the system automatically creates or links a Contact record. You can add addresses to the guardian through the standard Address panel on the Guardian form. Family addresses can be shared across linked students.
</Callout>

### Work Details

| Field | What It Means | Example |
|-------|---------------|---------|
| **Employment Sector** | Industry or sector of employment | Healthcare / Medical |
| **Work Place** | Organization or company name | Lusaka General Hospital |
| **Designation at Work** | Job title | Senior Nurse |
| **Work Email** | Professional email address | m.gonzalez@lgh.zm |
| **Work Phone** | Professional phone number | +260 21 123 4567 |

### Relationship Flags

| Field | What It Means | When to Use It |
|-------|---------------|----------------|
| **Is Primary Guardian** | The main point of contact for this student | The parent who should receive most communications |
| **Is Financial Guardian** | Responsible for billing and invoices | The parent who pays fees or manages the family account |
| **Authorized Signer** | Can provide electronic consent and sign policies | Enabled by default for most guardian relationships |

## The Guardian-Student Relationship

Guardians are linked to students through the **Student Guardian** child table on the Student record. Each link defines:

- **Guardian**: The guardian identity record
- **Relation**: The family relationship (Mother, Father, Stepmother, Stepfather, Grandmother, Grandfather, Aunt, Uncle, Sister, Brother, Other)
- **Authorized Signer**: Whether this guardian can sign policies and provide consent

A student can have multiple guardians. A guardian can be linked to multiple students (siblings).

<Callout type="success" title="Sibling linking is automatic">
When a guardian is linked to a student, the system checks if that guardian is already linked to other students. Sibling relationships are inferred from shared guardians and surfaced in the student record automatically.
</Callout>

## Guardian Portal Access

Guardians with a linked User account can access the Guardian Portal at `/hub/guardian`. The portal provides a family-first view of:

- **Home**: Family snapshot with counts, quick links, and briefing zones
- **Communications**: School messages and event history for all linked children
- **Student Detail**: Child-specific learning briefs and course information
- **Course Selection**: Academic self-enrollment for invited selection windows
- **Activities**: Activity booking and management
- **Attendance**: Family-wide attendance heatmap and day-detail review
- **Policies**: Active policy review and electronic acknowledgement
- **Finance**: Family invoices and payment history
- **Monitoring**: Guardian-visible student logs and published results
- **Portfolio**: Showcase evidence for guardian-visible portfolio content
- **Calendar**: Monthly school calendar overlay for family planning

### Creating a Portal User

1. Open the Guardian record
2. Ensure the guardian has a **Personal Email** filled in
3. Click **Actions → Create Guardian User**
4. The system creates a User account with the `Guardian` role
5. The guardian receives portal access immediately

If a User with that email already exists, the system links the existing user and ensures they have the Guardian role.

<Callout type="warning" title="Staff users keep staff routing">
If a guardian's email belongs to a staff member (someone with a staff portal role), the system does not override their routing. Staff members access the system through the staff portal, not the guardian portal.
</Callout>

## Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|------|------|-------|--------|--------|-------|
| `System Manager` | Yes | Yes | Yes | Yes | Full access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Full academic access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Admissions context |
| `Admission Officer` | Yes | Yes | Yes | Yes | Admissions context |
| `Academic Assistant` | Yes | Yes | Yes | No | Cannot delete |
| `Academic Staff` | Yes | No | No | No | Read-only |
| `Instructor` | Yes | No | No | No | Read-only |
| `Nurse` | Yes | No | No | No | Read-only |
| `Counselor` | Yes | No | No | No | Read-only |
| `Accreditation Visitor` | Yes | No | No | No | Read-only for audits |
| `Guardian` | Yes* | No | No | No | Own linked students only (portal) |

*Guardian read access is scoped to their own linked students through the portal.

## Guardian Data and School Demographics

Guardian records feed the **Student Demographic Analytics** dashboard (staff analytics surface). The following guardian-derived charts are currently active:

| Chart | Source Field | What It Shows |
|-------|--------------|---------------|
| **Guardian Employment Sector** | `Employment Sector` | Breakdown of guardian industries (e.g., Healthcare, Education, Government) |
| **Financial Guardian Spread** | `Is Financial Guardian` + relation | Which parent/guardian role handles billing (Mother, Father, or Other) |

The dashboard also reserves space for additional guardian demographics that are not yet populated because the corresponding fields do not exist on the Guardian DocType:

- **Guardian Nationality (Top)**
- **Preferred Communication Language**
- **Guardian Residence (Country)**
- **Guardian Residence (City)**
- **Guardian Diversity Score** (KPI)

<Callout type="info" title="Dashboards respect school scope">
Demographics aggregates are scoped to the selected school filter. Guardian counts reflect links to active students within that scope.
</Callout>

## Related Docs

<RelatedDocs
  slugs="student,student-applicant,school,organization,student-log"
  title="Continue With Student and Family Docs"
/>

## Technical Notes (IT)

- **DocType**: `Guardian` — Located in Students module
- **Autoname**: Uses Guardian identity (no auto-numbering)
- **Contact Integration**: Auto-creates or links a Contact record on save via `after_insert` hook
- **User Creation**: `create_guardian_user` whitelisted method creates a `Website User` with `Guardian` role
- **Portal Routing**: `Guardian` role routes users to `/hub/guardian`; staff roles take precedence
- **Image Upload**: `resolve_profile_image_organization` enforces single-organization constraint before upload
- **Linked Students**: Resolved bidirectionally via `Student Guardian` (student-side) and `Guardian Student` (guardian-side)
- **Sibling Sync**: Student applicant promotion synchronizes sibling relationships from shared guardians automatically
- **Address Sharing**: Family addresses can be linked to multiple students and their guardians through the address-linking API
- **Permissions**: Server-side `permission_query_conditions` enforce organization and school scope
