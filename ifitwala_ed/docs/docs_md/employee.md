---
title: "Employee: Managing Your Staff Records"
slug: employee
category: HR
doc_order: 1
version: "1.0.1"
last_change_date: "2026-04-25"
summary: "Learn how to create and manage Employee records—from onboarding and work history to profile images and user account provisioning."
seo_title: "Employee: Managing Your Staff Records"
seo_description: "Complete guide to managing Employee records in Ifitwala Ed including onboarding, work history, designation changes, and user account creation."

## What is an Employee Record?

An **Employee** record is the central staff identity in Ifitwala Ed. It holds everything about a staff member—their personal information, professional details, work history, leave balances, and links to their user account for portal and Desk access.

<Callout type="info" title="Why Ifitwala Ed is different">
Unlike platforms that separate HR data from academic operations, Ifitwala Ed's Employee record connects seamlessly to teaching assignments, staff calendars, leave management, professional development, and the staff portal. One record, complete visibility.
</Callout>


## Creating a New Employee

<Steps title="Adding a New Staff Member">
  <Step title="Open the Employee List">
    Go to **HR > Employee** and click **New**.
  </Step>
  <Step title="Enter Personal Information">
    Fill in the staff member's first name, last name, gender, date of birth, and professional email. The full name is generated automatically.
  </Step>
  <Step title="Add Contact Details">
    Enter mobile phone, personal email, and emergency contact information.
  </Step>
  <Step title="Set Professional Details">
    Enter the date of joining, employment status, employment type, designation, department, organization, and school.
  </Step>
  <Step title="Set Reporting Structure">
    Choose who this employee reports to. This builds your organization chart automatically.
  </Step>
  <Step title="Save">
    Click **Save**. The employee record is now created.
  </Step>
</Steps>

<Callout type="success" title="What happens automatically">
When you save an Employee record:
- A unique Employee ID is generated (format: `HR-EMP-####`)
- The full name is auto-composed from first, middle, and last names
- The organization chart updates to reflect reporting relationships
</Callout>


## Employee Fields Explained

### Personal Information

| Field | What It's For | Tips |
|-------|---------------|------|
| **First / Middle / Last Name** | Legal name | Required; used to generate full name automatically |
| **Preferred Name** | What they like to be called | Shows in lists and communications |
| **Gender** | Demographics | Used for reporting and diversity metrics |
| **Date of Birth** | Age calculations | Used for birthday alerts in Morning Brief |
| **Nationality** | Citizenship | Links to Country records |
| **Professional Email** | Primary work contact | Required and must be unique |
| **Personal Email** | Secondary contact | Optional |
| **Mobile Phone** | Primary phone | Include country code for international staff |

### Professional Information

| Field | What It's For | Tips |
|-------|---------------|------|
| **Date of Joining** | When they started | Required for leave eligibility calculations |
| **Employment Status** | Active, Temporary Leave, Suspended, Left | Only Active employees can access the system |
| **Employment Type** | Full-time, Part-time, Contract, etc. | Set up types in Employment Type |
| **Designation** | Job title | Controls default role access |
| **Department** | Functional area | Links to Department records |
| **Organization** | Primary organization | Drives permission scope |
| **School** | Primary campus | Drives school-scoped visibility |
| **Reports To** | Manager | Builds the organization chart |
| **Employee Group** | Staff category | Used for staff calendar matching |
| **Leave Approver** | Who approves their leave | Defaults can be set per designation |
| **Expense Approver** | Who approves their expenses | Optional |


## Work History (Employee History)

The **Employee History** child table tracks position changes over time. This is essential for staff who move between roles, schools, or departments.

<Steps title="Recording a Position Change">
  <Step title="Open the Employee Record">
    Navigate to the employee and scroll to the Work History section.
  </Step>
  <Step title="Add a New Row">
    Click **Add Row** in the Employee History table.
  </Step>
  <Step title="Fill Position Details">
    Enter designation, organization, school, from date, and optional to date.
  </Step>
  <Step title="Set Access Mode">
    Choose the appropriate access mode, role profile, and workspace override if needed.
  </Step>
  <Step title="Save the Employee">
    The history row is saved and the employee's access is updated automatically.
  </Step>
</Steps>

<Callout type="tip" title="History rules">
- `from_date` cannot be before the employee's joining date
- `to_date` cannot be before `from_date`
- Overlapping entries are blocked for identical (designation, organization, school) combinations
- `is_current` is derived automatically from the dates
</Callout>


## Creating a User Account

Every active employee needs a linked **User** account to access the staff portal and Desk (depending on their roles).

<Steps title="Provisioning a User Account">
  <Step title="Open the Employee Record">
    Make sure the employee has a professional email address filled in.
  </Step>
  <Step title="Click Create User">
    Find the **Create User** button in the User Info section and click it.
  </Step>
  <Step title="Confirm">
    The system validates the email, creates the User, and links it back to the Employee.
  </Step>
  <Step title="Review Added Roles">
    A dialog shows which roles were automatically assigned based on the employee's designation and history.
  </Step>
</Steps>

<Callout type="warning" title="Important">
- The employee must have a valid professional email to create a user
- User accounts are automatically enabled only when employment status is **Active**
- Non-active statuses (Temporary Leave, Suspended, Left) disable the linked user automatically
- The baseline **Employee** role is always added for active staff
</Callout>


## Employee Profile Image

Uploading a profile image helps identify staff across the organization chart, Morning Brief, and public website profiles.

<Steps title="Uploading a Profile Photo">
  <Step title="Open the Employee Record">
    Navigate to the employee form.
  </Step>
  <Step title="Upload Image">
    Click the image upload area and select a photo. The system handles privacy and generates variants automatically.
  </Step>
  <Step title="Save">
    Save the record. The image syncs to the linked User account automatically.
  </Step>
</Steps>

<Callout type="tip" title="Image variants">
The system automatically creates optimized variants for different surfaces:
- **Thumb** — For avatars and small lists
- **Card** — For profile cards and org chart
- **Medium** — For larger previews
</Callout>


## Public Website Profile

Some staff members can be featured on your public website (leadership page, staff directory).

| Field | What It Does |
|-------|--------------|
| **Show on Website** | Enables public profile display |
| **Small Bio** | Short description for the website |
| **Show Public Profile Page** | Creates a dedicated profile page |
| **Public Profile Slug** | Custom URL segment (optional) |
| **Featured on Website** | Highlights on leadership pages |
| **Website Sort Order** | Controls display ordering |

<Callout type="info" title="Privacy note">
Public website photos are delivered through a separate public route, not through the authenticated employee file path. This keeps private staff data secure while allowing controlled public exposure.
</Callout>


## Employee Status and Access Control

The **Employment Status** field is the master switch for system access:

| Status | User Account | System Access |
|--------|--------------|---------------|
| **Active** | Enabled | Full access based on roles |
| **Temporary Leave** | Disabled | No access during leave |
| **Suspended** | Disabled | No access |
| **Left** | Disabled | No access; record preserved for history |

<Callout type="warning" title="Automatic enforcement">
When you change an employee's status away from Active:
- The linked User is disabled immediately
- All assigned roles are removed
- They cannot log in to Desk or Portal
</Callout>


## The Organization Chart

The built-in organization chart visualizes your reporting structure. It is available from the Employee list view.

<Callout type="info" title="Chart visibility">
- Any authenticated active employee can view the org chart
- The chart defaults to showing all organizations, not just your own
- Avatar images resolve through optimized variants for fast loading
</Callout>


## Permission Matrix

| Role | What They Can Do | Typical User |
|------|------------------|--------------|
| **HR Manager** | Full CRUD on employees in their organization scope | Head of HR |
| **HR User** | Create and edit employees in their organization scope | HR Coordinator |
| **Academic Admin** | Read-only access to employees in their school scope | Principal, Registrar |
| **Employee** | View their own record only | Any staff member |
| **System Manager** | Full access | IT Administrator |

<Callout type="tip" title="Scope rules">
- HR roles see employees in their organization and all descendant organizations, plus employees with blank organization
- Academic Admin scope resolves from their active Employee profile first, then from user defaults
- Employees can only see their own record
</Callout>


## Best Practices

### For HR Teams
- Always use a valid professional email—it's required for user creation
- Record position changes in Employee History rather than editing the main designation field directly
- Set the reporting structure carefully; it drives the org chart
- Upload profile images during onboarding for a complete record

### For Managers
- Keep employment status current—it's the master access switch
- Review and update leave approver assignments when roles change
- Use the org chart to verify reporting relationships

### Data Quality
- Use consistent naming conventions across all records
- Ensure joining dates are accurate for leave calculations
- Link employees to the correct school for proper scoping
- Update Employee History promptly when staff change roles

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Create user accounts promptly after hiring.</Do>
  <Do>Record all position changes in Employee History.</Do>
  <Do>Update employment status immediately when staff leave.</Do>
  <Do>Use professional emails that match your organization's domain.</Do>
  <Dont>Delete employee records—use status changes instead.</Dont>
  <Dont>Manually edit the full name field (it's auto-generated).</Dont>
  <Dont>Skip Employee History for role changes.</Dont>
</DoDont>


## Common Questions

**Q: Can an employee belong to multiple schools?**
A: An employee has one primary school, but Employee History can track assignments across schools over time.

**Q: What happens when an employee's designation changes?**
A: Update the Employee History table with the new position. The system automatically recalculates roles and permissions for the linked user.

**Q: Can I reactivate a former employee?**
A: Yes. Change their employment status back to Active. Their user account will be re-enabled and roles restored based on current designation and history.

**Q: Why can't I see certain employees in the list?**
A: Check your organization and school scope. HR users see employees in their organization tree. Academic Admins see employees in their school scope. If an employee has no organization set, only HR roles can see them.

**Q: How do I fix a broken profile image?**
A: Re-upload the image through the governed upload action on the employee form. The system will regenerate all variants automatically.

## Related Docs

<RelatedDocs
  slugs="designation,staff-calendar,leave-application,professional-development"
  title="Continue With HR Docs"
/>


## Technical Notes (IT)

- **DocType**: `Employee` — Located in HR module
- **Autoname**: `HR-EMP-####` format (auto-generated)
- **NestedSet**: Used for reporting tree (`reports_to`, `lft`, `rgt`)
- **Linked Doctypes**: User, Contact, Address, Designation, Department
- **Image Governance**: Governed upload through `ifitwala_ed.utilities.governed_uploads.upload_employee_image`
- **User Sync**: `sync_user_access_from_employee` computes roles from history + designation
