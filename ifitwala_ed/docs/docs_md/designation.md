---
title: "Designation: Manage Job Titles and Roles"
slug: designation
category: HR
doc_order: 7
version: "1.0.1"
last_change_date: "2026-04-25"
summary: "Learn how to create and manage designations, configure default role profiles, and look up employees by designation."
seo_title: "Designation: Manage Job Titles and Roles"
seo_description: "Guide to managing Designations in Ifitwala Ed—job titles, role profiles, organization scope, and employee lookup."

## What is a Designation?

A **Designation** is a job title or position role in your organization. It defines what someone does, what default access they receive, and how they appear in organizational structures. Designations are foundational to employee onboarding, permission management, and reporting.

<Callout type="info" title="Why Ifitwala Ed is different">
Designations in Ifitwala Ed are more than labels. They carry default role profiles that automatically provision system access when linked to employees. Change a designation, and the employee's permissions update automatically.
</Callout>


## Creating a Designation

<Steps title="Adding a New Designation">
  <Step title="Open Designations">
    Go to **HR > HR Settings > Designation** and click **New**.
  </Step>
  <Step title="Enter Name">
    Enter the designation name (e.g., "Classroom Teacher", "Department Head", "School Nurse").
  </Step>
  <Step title="Set Organization">
    Select the organization this designation belongs to. This is mandatory.
  </Step>
  <Step title="Set School (Optional)">
    Choose a specific school if this designation is campus-specific. Leave blank for organization-wide designations.
  </Step>
  <Step title="Configure Defaults">
    Set the default role profile, employment type, and other defaults.
  </Step>
  <Step title="Save">
    Save the designation. It is now available for assignment to employees.
  </Step>
</Steps>

<Callout type="warning" title="Organization required">
Every designation must belong to a real organization. `All Organizations` is not allowed on Designation records.
</Callout>


## Designation Fields Explained

| Field | What It's For | Tips |
|-------|---------------|------|
| **Designation Name** | Job title | Use clear, consistent naming |
| **Organization** | Owning organization | Mandatory; drives visibility scope |
| **School** | Campus scope | Optional; blank means organization-wide |
| **Default Role Profile** | Auto-assigned roles | Employees with this designation receive these roles |
| **Employment Type Default** | Typical employment type | Pre-fills on new employee records |
| **Department Default** | Typical department | Pre-fills on new employee records |
| **Description** | Role summary | Helpful for job postings and org charts |


## Default Role Profiles

The **Default Role Profile** on a designation determines what system access employees automatically receive when they are assigned this designation.

<Callout type="success" title="Automatic provisioning">
When an employee is created or their designation changes:
- The system reads the designation's default role profile
- Adds the corresponding roles to the linked user
- Always includes the baseline **Employee** role for active staff
- Shows HR a dialog listing the roles that were added
</Callout>

### Common Role Assignments by Designation

| Designation | Typical Roles |
|-------------|---------------|
| **Classroom Teacher** | Employee, Academic Staff |
| **Department Head** | Employee, Academic Staff, Academic Admin |
| **School Nurse** | Employee, Nurse |
| **HR Coordinator** | Employee, HR User |
| **Principal** | Employee, Academic Admin |
| **Admissions Officer** | Employee, Admission Officer |

<Callout type="tip" title="Pre-join access">
Employees can receive baseline role access before their joining date, but workspace assignment is deferred until they have an active history row.
</Callout>


## Viewing Employees by Designation

HR can quickly see all employees holding a specific designation.

<Steps title="Looking Up Employees">
  <Step title="Open the Designation">
    Navigate to the designation record.
  </Step>
  <Step title="Click View Employees">
    Click the **View Employees** button (available to HR Manager, HR User, System Manager, and Administrator).
  </Step>
  <Step title="Review Results">
    A modal shows all employees who currently hold this designation, either as their primary designation or through active Employee History rows.
  </Step>
</Steps>

<Callout type="info" title="Scope enforcement">
The employee lookup respects organization and school scope. You only see employees you are authorized to view.
</Callout>


## Designation Visibility

Who can see and manage designations depends on role and scope:

| Role | Visibility | Mutation |
|------|------------|----------|
| **HR Manager / HR User** | Organization + descendants + blank org | Full CRUD in their scope |
| **Academic Admin** | Read-only | Cannot create or edit |
| **Other Staff** | Organization + parents | Read only |

<Callout type="warning" title="School scope">
When a designation has a school set, it is only visible to users whose effective school matches or is in the same lineage. HR operators can manage school-scoped rows within their organization scope.
</Callout>


## Collaborate Settings

Some designations may have **Collaborate** settings that define how people in this role interact with others in the organization.

<Callout type="tip" title="Collaboration rules">
Use Designation Collaborate records to define cross-functional collaboration patterns, mentoring relationships, or review structures.
</Callout>


## Permission Matrix

| Role | What They Can Do | Typical User |
|------|------------------|--------------|
| **HR Manager** | Full designation management | Head of HR |
| **HR User** | Create and edit designations | HR Coordinator |
| **Academic Admin** | Read-only access | Principal |
| **System Manager** | Full access | IT Administrator |


## Best Practices

### For HR Setup
- Create designations before onboarding employees
- Use consistent naming conventions across the organization
- Set appropriate default role profiles for automatic access
- Define school-scoped designations only when truly campus-specific

### For Ongoing Management
- Review designations annually for relevance
- Update default roles when organizational structures change
- Use the employee lookup to audit designation assignments
- Archive obsolete designations rather than deleting

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Create designations before hiring season begins.</Do>
  <Do>Set meaningful default role profiles.</Do>
  <Do>Use organization-wide designations when possible.</Do>
  <Do>Review designation assignments regularly.</Do>
  <Dont>Create duplicate designations with similar names.</Dont>
  <Dont>Leave default role profiles empty.</Dont>
  <Dont>Delete designations that have employee history.</Dont>
</DoDont>


## Common Questions

**Q: Can an employee have multiple designations?**
A: An employee has one primary designation, but Employee History can track simultaneous or sequential positions with different designations.

**Q: What happens if I change a designation's default roles?**
A: Existing employees are not automatically updated. Changes apply to new employees or when Employee History is modified.

**Q: Why can't I see a designation?**
A: Check the designation's organization and school scope. It may be scoped to a different school or organization than your user defaults.

**Q: Can I rename a designation?**
A: Yes, designations support renaming. Existing links update automatically.

**Q: What's the difference between a designation and a department?**
A: Designation is the job title (what someone does). Department is the functional area (where they work). One person has one designation but works within a department.

## Related Docs

<RelatedDocs
  slugs="employee,professional-growth-plan,hr-settings"
  title="Continue With HR Docs"
/>


## Technical Notes (IT)

- **DocType**: `Designation`
- **Scope**: Organization mandatory; school optional
- **Visibility**: Server-side `permission_query_conditions` enforce scope
- **Employee Lookup**: `get_scoped_designation_employees()` in designation controller
- **Role Sync**: `Employee._apply_designation_role()` triggers on designation or history changes
