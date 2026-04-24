---
title: "Leave Management: Configure Policies and Allocations"
slug: leave-management
category: HR
doc_order: 3
version: "1.0.0"
last_change_date: "2026-04-24"
summary: "HR admin guide to setting up leave types, policies, allocations, periods, and the control panel for automated leave management."
seo_title: "Leave Management: Configure Policies and Allocations"
seo_description: "Learn how to configure leave types, create leave policies, assign allocations, and manage leave periods in Ifitwala Ed."
---

## What is Leave Management?

**Leave Management** is the administrative backbone of staff time-off in Ifitwala Ed. It covers everything HR teams need to configure before employees can apply for leave: leave types, policies, allocations, periods, and automated rules.

<Callout type="info" title="Why Ifitwala Ed is different">
Ifitwala Ed's leave system is built for schools, not generic offices. It uses Staff Calendars (not student academic calendars) for holiday calculations, supports organization-tree scoping for multi-campus groups, and connects leave to staff attendance automatically.
</Callout>

---

## Leave Types

**Leave Types** define the kinds of leave your organization offers. Fresh installs come with a baseline set.

### Default Leave Types

| Leave Type | Typical Use |
|------------|-------------|
| **Annual Leave** | Standard vacation entitlement |
| **Sick Leave** | Illness or medical appointments |
| **Personal Leave** | Personal matters |
| **School Related Activities** | School events, trips, conferences |
| **Bereavement Leave** | Death of a family member |
| **Maternity Leave** | Childbirth leave |
| **Paternity Leave** | Partner childbirth leave |
| **Family Care Leave** | Caring for family members |
| **Professional Development Leave** | Training and conferences |
| **Unpaid Leave** | Leave without pay |

<Callout type="tip" title="Leave Without Pay">
Only Unpaid Leave is created with `is_lwp = 1` by default. This means it reduces payable days when payroll is active.
</Callout>

### Configuring a Leave Type

<Steps title="Setting Up a Leave Type">
  <Step title="Open Leave Types">
    Go to **HR > Leave > Leave Type**.
  </Step>
  <Step title="Create or Edit">
    Click **New** or edit an existing type.
  </Step>
  <Step title="Set Allocation Rules">
    Configure maximum allowed, applicability period, and consecutive day limits.
  </Step>
  <Step title="Enable Features">
    Turn on carry forward, earned leave, compensatory, or encashment as needed.
  </Step>
  <Step title="Save">
    Click **Save**. The type is now available for policies and applications.
  </Step>
</Steps>

### Leave Type Options Explained

| Option | What It Does | When to Use |
|--------|--------------|-------------|
| **Max Leaves Allowed** | Caps annual allocation | Set a ceiling per period |
| **Applicable After** | Minimum working days before eligibility | For probation periods |
| **Max Continuous Days** | Longest single stretch allowed | Prevent excessive consecutive leave |
| **Is Carry Forward** | Unused days roll to next period | For annual leave typically |
| **Is Leave Without Pay** | Reduces payable days | Unpaid leave types |
| **Is Optional Leave** | Holidays that staff can optionally take | Religious or cultural holidays |
| **Allow Negative** | Lets balance go below zero | Emergency or trusted staff policies |
| **Include Holidays** | Counts holidays as leave days | Rare; usually disabled |
| **Is Compensatory** | Tracks extra work compensation | For holiday overtime |
| **Is Earned Leave** | Accrues over time | Monthly or quarterly accrual |

---

## Leave Policies

A **Leave Policy** bundles multiple leave types into a single package that can be assigned to employees.

<Steps title="Creating a Leave Policy">
  <Step title="Open Leave Policies">
    Go to **HR > Leave > Leave Policy** and click **New**.
  </Step>
  <Step title="Name and Scope">
    Enter a title and select the organization.
  </Step>
  <Step title="Add Leave Types">
    In the Leave Policy Details table, add rows for each leave type with its annual allocation.
  </Step>
  <Step title="Submit">
    Save and Submit the policy. Submitted policies cannot be edited (create a new version instead).
  </Step>
</Steps>

<Callout type="success" title="Policy example">
A "Standard Teaching Staff" policy might include:
- Annual Leave: 21 days
- Sick Leave: 10 days
- Personal Leave: 3 days
- Professional Development Leave: 5 days
</Callout>

---

## Leave Periods

**Leave Periods** define the time window for which leave is allocated (typically an academic or fiscal year).

<Steps title="Setting Up a Leave Period">
  <Step title="Open Leave Periods">
    Go to **HR > Leave > Leave Period** and click **New**.
  </Step>
  <Step title="Define Dates">
    Enter the from date and to date (e.g., 1 August to 31 July for an academic year).
  </Step>
  <Step title="Link to Calendar">
    Select the optional holiday list for optional leave validation.
  </Step>
  <Step title="Save">
    Save the period. It is now available for policy assignments.
  </Step>
</Steps>

---

## Leave Policy Assignment

**Leave Policy Assignment** connects an employee to a leave policy for a specific period.

<Steps title="Assigning a Leave Policy">
  <Step title="Open Assignments">
    Go to **HR > Leave > Leave Policy Assignment** and click **New**.
  </Step>
  <Step title="Select Employee">
    Choose the employee who should receive this policy.
  </Step>
  <Step title="Select Policy">
    Choose the leave policy to apply.
  </Step>
  <Step title="Select Period">
    Choose the leave period.
  </Step>
  <Step title="Submit">
    Save and Submit. Leave allocations are created automatically based on the policy details.
  </Step>
</Steps>

<Callout type="info" title="Automatic allocation">
When you submit a Leave Policy Assignment, the system creates Leave Allocation records for each leave type in the policy. These allocations feed into the balance calculations employees see when applying for leave.
</Callout>

---

## Leave Allocations

**Leave Allocations** represent the actual days available to an employee for a specific leave type in a period.

<Steps title="Creating a Manual Leave Allocation">
  <Step title="Open Allocations">
    Go to **HR > Leave > Leave Allocation** and click **New**.
  </Step>
  <Step title="Fill Details">
    Select employee, leave type, from date, to date, and enter the number of new days allocated.
  </Step>
  <Step title="Submit">
    Save and Submit. The allocation is now active and counts toward the employee's balance.
  </Step>
</Steps>

<Callout type="tip" title="Adjustments">
Use **Leave Adjustment** to add or remove days from an existing allocation without cancelling it. This is useful for corrections or special circumstances.
</Callout>

---

## Leave Control Panel

The **Leave Control Panel** lets HR bulk-assign leave policies to multiple employees at once.

<Steps title="Bulk Assigning Leave Policies">
  <Step title="Open Control Panel">
    Go to **HR > Leave > Leave Control Panel**.
  </Step>
  <Step title="Set Filters">
    Select department, designation, employment type, branch, or specific employees.
  </Step>
  <Step title="Choose Policy">
    Select the leave policy to assign.
  </Step>
  <Step title="Set Period">
    Choose the leave period.
  </Step>
  <Step title="Allocate">
    Click **Allocate Leave**. Policies are assigned to all matching employees.
  </Step>
</Steps>

<Callout type="warning" title="Use with care">
Bulk allocation affects many employees at once. Review your filters carefully before clicking Allocate Leave.
</Callout>

---

## Leave Block List

A **Leave Block List** prevents leave applications on specific dates—useful for blackout periods like exam weeks, orientation days, or critical school events.

<Steps title="Creating a Block List">
  <Step title="Open Block Lists">
    Go to **HR > Leave > Leave Block List** and click **New**.
  </Step>
  <Step title="Name It">
    Enter a name for the block list (e.g., "Exam Week Blackout").
  </Step>
  <Step title="Add Blocked Dates">
    In the Leave Block List Date child table, add each date that should be blocked.
  </Step>
  <Step title="Add Exceptions">
    In the Leave Block List Allow child table, add any employees who are exempt from these blocks.
  </Step>
  <Step title="Save">
    Save the block list. It is enforced automatically on new leave applications.
  </Step>
</Steps>

---

## Earned Leave

**Earned Leave** accrues over time rather than being granted all at once at the start of a period.

### How It Works
- Leave is earned monthly or based on a schedule
- The scheduler automatically creates allocations according to the earned leave frequency
- Employees see growing balances throughout the period

<Callout type="info" title="Scheduler control">
Earned leave processing is controlled by **HR Settings > Enable Earned Leave Scheduler**. When enabled, the system processes earned leave allocations daily in the background.
</Callout>

---

## Leave Encashment

**Leave Encashment** allows employees to convert unused leave into monetary value.

<Callout type="warning" title="Feature status">
Leave Encashment is imported for compatibility but is currently **disabled by default**. It requires both `enable_leave_encashment` and payroll mapping to be active before use. Contact your system administrator before enabling.
</Callout>

---

## HR Settings for Leave

Configure global leave behavior in **HR Settings**:

| Setting | What It Controls |
|---------|------------------|
| **Leave Approval Mandatory** | Requires approval for all leave |
| **Prevent Self Leave Approval** | Blocks approvers from approving their own requests |
| **Leave Status Notification** | Emails on status changes |
| **Leave Approver Mandatory** | Requires an approver to be set on Employee records |
| **Enable Earned Leave Scheduler** | Automatic earned leave processing |
| **Enable Leave Expiry Scheduler** | Automatic expiry of unused allocations |
| **Enable Leave Encashment** | Allows encashment functionality |
| **Auto Leave Encashment** | Automatic encashment generation |

---

## Permissions: Who Can Do What

| Role | What They Can Do | Typical User |
|------|------------------|--------------|
| **HR Manager** | Full leave configuration access | Head of HR |
| **HR User** | Create and manage policies, allocations | HR Coordinator |
| **System Manager** | All settings and configuration | IT Administrator |
| **Employee** | View their own allocations and balances | Any staff member |

---

## Best Practices

### For HR Setup
- Create leave policies before the start of each academic/fiscal year
- Use the Leave Control Panel for bulk assignments
- Set up Staff Calendars before leave periods begin
- Configure block lists for known blackout dates

### For Ongoing Management
- Monitor leave balances regularly
- Process leave adjustments promptly for corrections
- Review and update policies annually
- Keep earned leave scheduler enabled for accruing types

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Set up leave policies before employees need to apply.</Do>
  <Do>Use bulk assignment tools for large staff cohorts.</Do>
  <Do>Block critical dates well in advance.</Do>
  <Do>Review allocations at period boundaries.</Do>
  <Dont>Edit submitted leave policies—create new versions instead.</Dont>
  <Dont>Forget to set Staff Calendars before leave calculations begin.</Dont>
  <Dont>Enable encashment without payroll validation.</Dont>
</DoDont>

---

## Common Questions

**Q: Why can't an employee apply for a leave type?**
A: Check that they have a Leave Allocation for that type and period. Also verify the leave type's Applicable After setting.

**Q: How do carry-forward days work?**
A: If a leave type has carry forward enabled, unused days at period end roll into the next period, up to the maximum carry-forward limit.

**Q: Can I change a leave policy after submitting it?**
A: No. Submitted leave policies cannot be edited. Cancel it and create a new one, or use Leave Adjustment for individual cases.

**Q: What's the difference between Leave Policy Assignment and Leave Allocation?**
A: Policy Assignment is the high-level connection of employee to policy. Allocation is the actual day count available. Policy Assignments create Allocations automatically.

**Q: How often does earned leave accrue?**
A: This depends on the Earned Leave Frequency set on the leave type (Monthly, Quarterly, etc.). The scheduler processes it daily.

---

<RelatedDocs
  slugs="leave-application,employee,staff-calendar"
  title="Continue With Leave and HR Docs"
/>

---

## Technical Notes (IT)

- **DocTypes**: Leave Type, Leave Policy, Leave Policy Detail, Leave Period, Leave Policy Assignment, Leave Allocation, Leave Ledger Entry, Leave Control Panel, Leave Block List
- **Scheduler**: Daily dispatch for earned leave, expiry, and encashment
- **Tenancy**: Organization-first with descendant scope
- **Holiday Source**: Staff Calendar only; no School Calendar fallback
- **Encashment Gating**: `HR Settings.enable_leave_encashment` controls visibility and access
