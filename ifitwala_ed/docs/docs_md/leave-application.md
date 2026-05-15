---
title: "Leave Application: Request and Approve Time Off"
slug: leave-application
category: HR
doc_order: 2
version: "1.0.1"
last_change_date: "2026-04-25"
summary: "Learn how staff apply for leave, check balances, and how managers approve or reject leave requests."
seo_title: "Leave Application: Request and Approve Time Off"
seo_description: "Step-by-step guide to applying for leave, understanding leave balances, and managing approvals in Ifitwala Ed."

## What is a Leave Application?

A **Leave Application** is how staff members request time off and how managers approve or reject those requests. It connects directly to leave allocations, balances, and the staff calendar—so you always know how much leave is available and whether requested days conflict with holidays or blocked dates.

<Callout type="info" title="Why Ifitwala Ed is different">
Leave applications in Ifitwala Ed are tightly integrated with Staff Calendars (not school calendars). This means holidays, weekends, and blocked days are calculated correctly for staff specifically—not mixed with student academic calendars.
</Callout>


## Applying for Leave

<Steps title="Submitting a Leave Request">
  <Step title="Open Leave Application">
    Go to **HR > Leave > Leave Application** and click **New**.
  </Step>
  <Step title="Select Employee">
    The employee field usually fills automatically for self-service users. HR users can select any employee in their scope.
  </Step>
  <Step title="Choose Leave Type">
    Select from available leave types: Annual Leave, Sick Leave, Personal Leave, etc.
  </Step>
  <Step title="Set Date Range">
    Enter the **From Date** and **To Date**. The system calculates total leave days automatically, excluding holidays and weekends.
  </Step>
  <Step title="Half Day (Optional)">
    Check **Half Day** if needed. If your range spans multiple days, you can specify which single day is a half day.
  </Step>
  <Step title="Add Reason">
    Enter a description or reason for the leave. This helps approvers understand the context.
  </Step>
  <Step title="Review Leave Balance">
    The form shows your **Leave Balance Before Application** so you know what's available.
  </Step>
  <Step title="Submit">
    Click **Save** to create the application. It starts in **Open** status and notifies your leave approver.
  </Step>
</Steps>

<Callout type="success" title="What happens automatically">
When you submit a leave application:
- Total leave days are calculated excluding Staff Calendar holidays
- Your current leave balance is displayed
- The leave approver is notified
- The application appears on the Leave Calendar
</Callout>


## Understanding Leave Balance

The **Leave Balance Before Application** field shows how many days you have available for the selected leave type. This is calculated from:

- Your **Leave Allocations** for the period
- Minus any already approved or taken leave
- Plus any carry-forward from previous periods (if configured)

<Callout type="warning" title="Balance can go negative">
Some leave types allow negative balances. Check with your HR team if you're unsure about your organization's policy.
</Callout>


## Leave Approval Workflow

Leave applications follow a simple but strict approval flow:

| Status | What It Means | Who Can Change It |
|--------|---------------|-------------------|
| **Open** | Submitted, awaiting decision | Employee, Approver, HR |
| **Approved** | Leave granted | Approver, HR override roles |
| **Rejected** | Leave denied | Approver, HR override roles |
| **Cancelled** | Withdrawn by employee | Employee (before approval) |

### Who Can Approve?

1. **Assigned Leave Approver** — The person set on your Employee record
2. **HR User** — Can approve for employees in their organization scope
3. **HR Manager** — Can approve for employees in their organization scope
4. **Academic Admin** — Can approve with override authority
5. **System Manager** — Full override authority

<Callout type="tip" title="Self-approval block">
Your organization may have **Prevent Self Leave Approval** enabled in HR Settings. If so, you cannot approve your own leave requests even if you have an override role.
</Callout>


## Approving or Rejecting Leave

<Steps title="Managing Leave Requests as an Approver">
  <Step title="View Pending Requests">
    Go to **HR > Leave > Leave Application** and filter by status **Open**.
  </Step>
  <Step title="Open the Request">
    Click on a leave application to review the details, dates, and reason.
  </Step>
  <Step title="Make a Decision">
    Change the **Status** to **Approved** or **Rejected**.
  </Step>
  <Step title="Save">
    Click **Save**. The employee is notified of the decision.
  </Step>
</Steps>

<Callout type="info" title="After approval">
When a leave application is approved:
- A **Leave Ledger Entry** is created (consumes leave balance)
- An **Employee Attendance** record is created for those dates
- The leave appears on calendars and reports
</Callout>


## Cancelling Leave

### Before Approval
Employees can cancel their own open leave applications by changing the status to **Cancelled** and saving.

### After Approval
Only approvers or HR roles can cancel approved leave. When approved leave is cancelled:
- The Leave Ledger Entry is reversed (balance is restored)
- The Employee Attendance record is removed
- The cancellation is deterministic and traceable


## Leave Application Fields Explained

| Field | What It's For | Tips |
|-------|---------------|------|
| **Employee** | Who is requesting leave | Auto-filled for self-service |
| **Leave Type** | Category of leave | Annual, Sick, Personal, etc. |
| **From Date / To Date** | Leave period | Holidays and weekends are excluded from calculations |
| **Half Day** | Request partial day | Only one half-day per multi-day range |
| **Total Leave Days** | Computed duration | Read-only; auto-calculated |
| **Reason** | Why leave is needed | Helpful for approvers |
| **Leave Balance** | Available days | Shows before-application balance |
| **Leave Approver** | Who decides | Set on the Employee record |
| **Status** | Current state | Open, Approved, Rejected, Cancelled |
| **Posting Date** | When recorded | Usually today |


## The Leave Calendar

Leave applications appear on the **Leave Calendar** so managers and HR can visualize staff availability at a glance.

<Callout type="tip" title="Calendar integration">
- Approved leave shows in calendar views
- Different leave types can have different colors
- The calendar respects Staff Calendar holidays
</Callout>


## Compensatory Leave

If your organization uses compensatory leave, staff can submit a **Compensatory Leave Request** when they work on holidays or extra hours.

<Steps title="Requesting Compensatory Leave">
  <Step title="Open Compensatory Leave Request">
    Go to **HR > Leave > Compensatory Leave Request**.
  </Step>
  <Step title="Select Work Date">
    Enter the date you worked that should be compensated.
  </Step>
  <Step title="Submit">
    Save the request. If approved, a leave allocation is created automatically.
  </Step>
</Steps>


## Permission Matrix

| Role | What They Can Do | Typical User |
|------|------------------|--------------|
| **Employee** | Create and view their own applications | Any staff member |
| **Leave Approver** | Approve/reject assigned employees' leave | Managers, Department Heads |
| **HR User** | Create, edit, approve in their org scope | HR Coordinator |
| **HR Manager** | Full access in their org scope | Head of HR |
| **Academic Admin** | Override approval authority | Principal |
| **System Manager** | Full access | IT Administrator |

<Callout type="info" title="Organization scope">
HR roles can only see and manage leave applications for employees within their organization subtree. Employees can only see their own applications.
</Callout>


## Best Practices

### For Employees
- Apply for leave as early as possible
- Always include a clear reason
- Check your leave balance before applying
- Cancel promptly if plans change

### For Approvers
- Review leave applications regularly
- Consider team coverage before approving
- Communicate rejections with context
- Check the calendar for overlapping requests

### For HR
- Ensure leave allocations are set up before the period starts
- Monitor balances to prevent unexpected negative balances
- Keep Staff Calendars up to date for accurate calculations

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Apply for leave in advance when possible.</Do>
  <Do>Include a reason to help approvers decide.</Do>
  <Do>Cancel unused leave promptly to free up team planning.</Do>
  <Do>Check the Leave Calendar before approving overlapping requests.</Do>
  <Dont>Approve your own leave if self-approval is blocked.</Dont>
  <Dont>Backdate leave applications without HR authorization.</Dont>
  <Dont>Ignore rejected applications without communicating why.</Dont>
</DoDont>


## Common Questions

**Q: Why is my leave balance showing zero?**
A: You may not have a Leave Allocation for this period, or the leave type may not be allocated to you. Contact HR.

**Q: Can I apply for leave spanning a holiday?**
A: Yes. Holidays and weekends are automatically excluded from the total leave days calculation.

**Q: What if my approver is on leave?**
A: HR Managers and Academic Admins can approve on behalf of the assigned approver.

**Q: Can I edit an already approved leave application?**
A: No. Approved applications cannot be edited. Cancel it and submit a new one.

**Q: Why was my leave application rejected?**
A: Common reasons: insufficient balance, conflicting with blocked dates, or team coverage concerns. Check with your approver.

**Q: How do half days work?**
A: Check the Half Day box. For single-day requests, that's a half day. For multi-day requests, specify which date is the half day.

## Related Docs

<RelatedDocs
  slugs="leave-management,employee,staff-calendar"
  title="Continue With Leave and HR Docs"
/>


## Technical Notes (IT)

- **DocType**: `Leave Application` — Located in HR module
- **Autoname**: `HR-LAP-.YYYY.-` format
- **Holiday Source**: Staff Calendar only (`Employee.current_holiday_lis`)
- **Approval**: Controller-owned transitions (no Frappe Workflow)
- **Side Effects**: Leave Ledger Entry, Employee Attendance on submit/cancel
- **Calendar**: Registered in `hooks.calendars`
