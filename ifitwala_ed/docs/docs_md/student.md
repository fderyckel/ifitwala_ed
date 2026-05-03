---
title: "Student: Your Learner Records Made Simple"
slug: student
category: Students
doc_order: 1
version: "1.3.6"
last_change_date: "2026-05-03"
summary: "Manage learner records with confidence—from admissions intake to alumni status. Understand when to use the admissions pipeline versus importing existing students."
seo_title: "Student: Your Learner Records Made Simple"
seo_description: "Learn how to manage Student records in Ifitwala Ed—from admissions promotion to bulk importing existing students with full portal access and health record integration."

## What is a Student Record?

A **Student** is the central learner record in Ifitwala Ed. It's the single source of truth for everything about a learner—their identity, academic history, guardians, health information, and portal access.

<Callout type="info" title="Why Ifitwala Ed is different">
Unlike platforms that scatter student data across disconnected modules, Ifitwala Ed's Student record is deeply integrated. One record connects to admissions, enrollment, attendance, assessments, health, finance, and the family portal—giving you a complete 360° view of every learner without switching contexts.
</Callout>

## How Students Are Created

There are two ways Student records enter the system:

### 1. **Admissions Pipeline (The Normal Path)**

The standard way students enter your system is through the admissions workflow:

`Inquiry → Student Applicant → Approved → Promoted to Student`

This is how the vast majority of your students should be created. It ensures:
- Complete application history is preserved
- All required documents are collected
- Proper approval workflows are followed
- Student and guardian portal accounts are created automatically

### 2. **Direct Import (For Existing Schools)**

If you're migrating from another system or onboarding an existing school, you can import students directly using the Data Import tool. This is an intentional exception path—not the default workflow.

<Callout type="warning" title="Choose the right path">
- **New admissions** → Always use the Applicant promotion workflow
- **Existing school migration** → Use Data Import with the special flag
- **Never** create students manually one-by-one in Desk (this is blocked for data integrity)
</Callout>

## Creating Students Through Admissions

The admissions workflow is the heart of Ifitwala Ed's student intake. Here's how it works:

<Steps title="From Prospect to Student">
  <Step title="Capture the Inquiry">
    A family expresses interest—via your website, phone, or walk-in. This creates an Inquiry record.
  </Step>
  <Step title="Invite to Apply">
    When they're ready, convert the Inquiry to a Student Applicant. The system tracks their entire application journey.
  </Step>
  <Step title="Collect Evidence">
    Applicants upload documents, complete health profiles, and submit recommendations—all linked to their application.
  </Step>
  <Step title="Review and Decide">
    Your admissions team reviews readiness, interviews the family, and makes an offer decision.
  </Step>
  <Step title="Promote to Student">
    Upon acceptance, click "Promote to Student." The system creates the Student record, portal accounts, and health profile automatically.
  </Step>
</Steps>

<Callout type="success" title="What happens automatically">
When you promote an applicant:
- Student record is created with all application data
- Student portal user account is created (email = username)
- Student Patient record is created for health services
- Contact record links the student to your CRM
- Guardian relationships and portal access are established
</Callout>

## Importing Existing Students

If you're bringing in students from a previous system, use Data Import. This is designed for one-time migrations, not ongoing intake.

### Before You Import

Make sure you have:
- **School record** already created (you'll need `anchor_school`)
- **Cohorts** set up (if you use them)
- **Student Houses** configured (if you use them)
- **Languages** defined in the system
- **Clean, unique email addresses** for every student

<Steps title="Importing Students via Data Import">
  <Step title="Open Data Import">
    Go to **Data Import** in Desk (or open Student and click Menu → Import).
  </Step>
  <Step title="Select Student DocType">
    Choose "Student" as the target DocType and select "Insert New Records."
  </Step>
  <Step title="Download Template">
    Download the import template. Include all fields you need.
  </Step>
  <Step title="Add the Required Flag">
    **Critical:** Add a column called `allow_direct_creation` and set it to `1` on every row. Without this, the import will fail.
  </Step>
  <Step title="Fill Required Fields">
    Every row needs: `student_first_name`, `student_last_name`, `student_email`, and `anchor_school`.
  </Step>
  <Step title="Add Optional Fields">
    Include: date of birth, gender, nationality, cohort, student house, joining date, etc.
  </Step>
  <Step title="Validate and Import">
    Upload your file, run validation to check for errors, then start the import.
  </Step>
</Steps>

<Callout type="tip" title="Import side effects">
When you import students, all the same automation runs as with admissions:
- Portal user accounts are created
- Student Patient records are created
- Contacts are linked
- Full names are auto-generated
</Callout>

## Student Fields Explained

| Field | What It's For | Tips |
|-------|---------------|------|
| **Student ID** | Optional external ID (legacy systems) | Leave blank to auto-generate STUD-YY-#### format |
| **First / Middle / Last Name** | Legal name | All three are used to generate the full name automatically |
| **Preferred Name** | What the student likes to be called | Shows in lists and parent communications |
| **Email** | Portal username and primary contact | Must be unique; becomes their login username |
| **Date of Birth** | Restricted source field for age calculations and approved identity/medical workflows | Cannot be after today or the joining date; visible on the Student record only to Academic Admin and System Manager |
| **Student Age** | Derived display age shown in day-to-day academic views | Used instead of full date of birth where staff need age context but not identity data |
| **Gender** | Demographics and reporting | Used for housing, sports, and diversity metrics |
| **Joining Date** | When they started at your school | Used for anniversary calculations and reporting |
| **First / Second Language** | Language proficiency tracking | Teacher-facing academic context; set up Language Xtra records first |
| **Nationality** | Citizenship information | Links to Country records |
| **Anchor School** | Primary school affiliation | Every student needs this for scoping |
| **Cohort** | Graduating class (e.g., "Class of 2030") | Great for longitudinal tracking |
| **Student House** | House/dorm assignment | For competitions and residential management |
| **Student Applicant** | Link to admissions record | Auto-set when promoted from applicant |
| **Enabled** | Active status | Uncheck to deactivate without deleting history |
| **Exit Date / Reason** | For withdrawn students | Use when a student leaves your school |

## Contact And Address Workflow

On the Student Desk form, the Contact and Address area is intended to stay visible as the family quick-view:

- `contact_html` and `address_html` render the linked CRM summary directly on the Student form
- if your role already has native `Contact` or `Address` Desk access, the Student form also exposes direct open actions to those records
- if your role can read Student but does not have native `Contact` or `Address` access, the Student form remains the safe read-only context instead of widening raw CRM permissions

### Family Address Reuse Proposal

When a student has exactly one linked Address, the Student form can propose reusing that same Address for related guardians and siblings.

Rules:

- this is always an explicit proposal, never a silent automatic link
- only related guardians and siblings with **no existing Address link** are offered
- guardians or siblings who already have an Address link are shown as excluded from the proposal
- the same Address record is reused through additional links; the system does not duplicate address text just to speed up family setup

This flow is especially useful after migration/import when staff have already linked siblings and guardians and want to avoid repetitive family address entry.

## Where You'll Use Student Records

### Admissions & Enrollment
- Track the full journey from inquiry to enrollment
- View application history and submitted documents
- Manage waitlists and offers

### Academic Life
- Enroll students in courses and programs
- Track attendance and participation
- View grades and assessment results
- Manage course loads and academic policies

### Health & Wellness
- Access Student Patient records for health services
- Track vaccinations and medical conditions
- Manage nurse visits and health screenings
- Store emergency contacts and medical consent

### Finance & Billing
- Link to Account Holder for invoicing
- View billing plans and payment history
- Manage fee concessions and scholarships
- Track family financial relationships

### Family Engagement
- Student portal for assignments and grades
- Guardian portal for parents to view progress
- Automatic communication via email
- Portfolio for showcasing student work

### Reports & Analytics
- Cohort-based longitudinal tracking
- Demographic analysis
- Retention and attrition reporting
- Academic performance dashboards

## Permission Matrix

| Role | Read | Write | Create | Delete | Import | Notes |
|------|------|-------|--------|--------|--------|-------|
| `System Manager` | Yes | Yes | Yes | Yes | No | No import by default (intentional) |
| `Academic Admin` | Yes* | Yes* | Yes | No | Yes | School-branch academic access |
| `Academic Assistant` | Yes* | Yes* | Yes | No | Yes | School-branch academic access |
| `Instructor` | Yes* | No | No | No | No | Active students in assigned Student Groups only |
| `Nurse` | Yes | Yes | No | No | No | Medical context access |
| `Counselor` | Yes | Yes | No | No | No | Assigned student access |
| `Admission Manager` | Yes | Yes | Yes | No | No | Admissions context |
| `Admission Officer` | Yes | Yes | Yes | No | No | Admissions context |
| `Guardian` | Yes* | No | No | No | No | Own children only (portal) |
| `Student` | Yes* | No | No | No | No | Self only (portal) |

*Read and write access is scoped by relationship or staff scope. Academic Admin and Academic Assistant users see only students whose Anchor School is inside their visible school branch. Instructors see only active students in active Student Groups where they are assigned as an instructor.

Sensitive identity fields are additionally separated by field permission level. `student_date_of_birth` is restricted on the Student record; non-admin attendance, student-group, morning-brief, and profile-print surfaces use `student_age` or birthday labels instead of returning the full date. Student Patient quick-info returns raw DOB only to Nurse, Academic Admin, and system-wide users; other Student Patient readers get age.

## Related Docs

<RelatedDocs
  slugs="student-applicant,school,organization,student-enrollment-playbook,inquiry"
  title="Continue With Admissions and Enrollment Docs"
/>

## Technical Notes (IT)

- **DocType**: `Student` — Located in Students module
- **Autoname**: `STUD-.YY.-.####` format (auto-generated)
- **Creation Paths**: Applicant promotion (canonical) or Data Import (exception)
- **Import Flag**: `allow_direct_creation` check field required for imports
- **Desk visibility**: Student List, Image, Report, and form access are server-scoped through scripted permissions. Academic Admin and Academic Assistant users use `Student.anchor_school` plus the active Employee school branch. Instructors use active `Student Group Instructor` and `Student Group Student` rows.
- **DOB visibility**: `student_date_of_birth` is `permlevel 2` on Student; `student_age` is the derived read-only field for general academic display.
- **Side Effects**: imported/direct student creation keeps user creation, Student Patient creation, contact linking, and image sync; applicant promotion now also materializes the canonical `Contact.links -> Student` binding synchronously.
- **Legacy remediation**: existing sites backfill missing `Contact.links -> Student` rows through the one-shot patch `ifitwala_ed.patches.backfill_student_contact_links`
- **Profile-image cleanup**: runtime Student saves no longer rename or repair legacy image files; existing sites normalize legacy `Student.student_image` rows through the one-shot patch `ifitwala_ed.patches.backfill_student_profile_images`
