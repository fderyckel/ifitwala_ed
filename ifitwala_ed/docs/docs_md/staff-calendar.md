---
title: "Staff Calendar: Manage Staff Holidays and Working Days"
slug: staff-calendar
category: HR
doc_order: 6
version: "1.0.1"
last_change_date: "2026-04-25"
summary: "Learn how to create staff calendars, add holidays, configure weekly offs, and link calendars to employees for accurate leave calculations."
seo_title: "Staff Calendar: Manage Staff Holidays and Working Days"
seo_description: "Guide to setting up Staff Calendars in Ifitwala Ed—weekly holidays, local holidays, break periods, and employee linking."

## What is a Staff Calendar?

A **Staff Calendar** defines holidays, working days, and break periods for staff. It is the authoritative source for leave calculations, ensuring that staff time-off is computed correctly against their own holiday schedule—not the student academic calendar.

<Callout type="info" title="Why Ifitwala Ed is different">
Ifitwala Ed keeps Staff Calendars separate from School Calendars. This means staff can have different holidays than students (e.g., inset days, staff training days, or different term breaks), and leave calculations remain accurate for staff specifically.
</Callout>


## Creating a Staff Calendar

<Steps title="Setting Up a Staff Calendar">
  <Step title="Open Staff Calendars">
    Go to **HR > Staff Calendar** and click **New**.
  </Step>
  <Step title="Name the Calendar">
    Enter a descriptive name (e.g., "2026-2027 Teaching Staff Calendar").
  </Step>
  <Step title="Select Academic Year">
    Link the calendar to an academic year for scoping.
  </Step>
  <Step title="Set School">
    Choose the school this calendar applies to.
  </Step>
  <Step title="Set Date Range">
    Enter the from date and to date for the calendar period.
  </Step>
  <Step title="Assign Employee Group">
    Optionally select an employee group (e.g., "Teaching Staff", "Support Staff").
  </Step>
  <Step title="Save">
    Save the calendar. You can now add holidays.
  </Step>
</Steps>


## Adding Weekly Holidays

Most organizations have regular weekly days off (typically Saturday and Sunday).

<Steps title="Configuring Weekly Offs">
  <Step title="Open the Calendar">
    Navigate to the Staff Calendar you want to configure.
  </Step>
  <Step title="Select Weekly Off">
    In the **Add Weekly Holidays** section, select the day(s) of the week (e.g., Saturday, Sunday).
  </Step>
  <Step title="Choose Color">
    Pick a color for weekly holidays on the calendar view.
  </Step>
  <Step title="Generate Dates">
    Click **Get Weekly Off Dates**. The system populates all matching dates within the calendar range.
  </Step>
  <Step title="Review">
    Check the generated dates in the holidays table.
  </Step>
</Steps>

<Callout type="tip" title="Multiple weekly offs">
You can add multiple weekly offs (e.g., Friday and Saturday for some regions). Run the generator for each day.
</Callout>


## Adding Local Holidays

**Local Holidays** are public holidays specific to your country or region.

<Steps title="Importing Public Holidays">
  <Step title="Select Country">
    In the **Add Local Holiday** section, choose the country.
  </Step>
  <Step title="Select Subdivision (Optional)">
    Choose a state, province, or region for localized holidays.
  </Step>
  <Step title="Choose Color">
    Pick a color to distinguish local holidays from weekly offs.
  </Step>
  <Step title="Generate">
    Click **Get Country Holidays**. The system fetches and adds public holidays for the selected region within your date range.
  </Step>
</Steps>

<Callout type="info" title="Holiday coverage">
The system fetches holidays for the calendar's date range. Make sure your calendar spans the full period you need.
</Callout>


## Adding Break Periods

**Break Periods** are longer holidays like winter break, spring break, or summer vacation.

<Steps title="Configuring Break Periods">
  <Step title="Enter Break Details">
    In the **Add Longer Breaks** section, enter the break description.
  </Step>
  <Step title="Set Dates">
    Enter the start and end dates of the break.
  </Step>
  <Step title="Choose Color">
    Select a color for break period days.
  </Step>
  <Step title="Generate">
    Click **Get Break Holidays**. All days in the range are added to the holidays table.
  </Step>
</Steps>


## Managing the Holiday Table

The **Holidays** child table shows all days that are non-working. You can:

- Review all generated holidays
- Remove individual dates that don't apply
- Add manual holidays for special occasions
- Clear the entire table and regenerate if needed

<Callout type="warning" title="Clear with care">
The **Clear Table** button removes all holidays. Use it only if you need to regenerate the calendar from scratch.
</Callout>


## Linking Calendars to Employees

For leave calculations to work, employees must be linked to a Staff Calendar.

<Steps title="Assigning a Calendar to an Employee">
  <Step title="Open the Employee Record">
    Go to **HR > Employee** and select the staff member.
  </Step>
  <Step title="Set Holiday List">
    In the **Attendance and Leaves Details** section, select the **Current Holiday List** field.
  </Step>
  <Step title="Save">
    Save the employee. Leave calculations now use this calendar.
  </Step>
</Steps>

<Callout type="success" title="Auto-resolution">
If an employee's linked calendar becomes outdated or missing, the system can self-heal by resolving the effective Staff Calendar based on employee group, date window, and school lineage. However, explicitly setting the calendar is recommended for reliability.
</Callout>


## Calendar Resolution Priority

When determining which calendar to use for an employee, the system follows this order:

1. **Employee's linked Staff Calendar** (`current_holiday_lis`) if it overlaps the date range
2. **Staff Calendar match** by employee group and date window, resolved through school lineage
3. **School Calendar Holidays** — only if no Staff Calendar exists

<Callout type="info" title="School lineage">
Calendar resolution checks the employee's school, then parent schools, then grandparent schools. No sibling-school leakage occurs.
</Callout>


## Staff Calendar vs School Calendar

| Aspect | Staff Calendar | School Calendar |
|--------|---------------|-----------------|
| **Used for** | Leave calculations, staff attendance | Student attendance, academic scheduling |
| **Audience** | Employees, HR | Students, teachers, academic staff |
| **Holidays** | Staff inset days, staff-only holidays | Student holidays, term breaks |
| **Leave system** | Yes — primary source | No — fallback only |


## Permission Matrix

| Role | What They Can Do | Typical User |
|------|------------------|--------------|
| **HR Manager** | Full calendar management | Head of HR |
| **HR User** | Create and edit calendars | HR Coordinator |
| **Academic Admin** | Read access | Principal |
| **System Manager** | Full access | IT Administrator |


## Best Practices

### For HR Setup
- Create Staff Calendars before setting up leave periods
- Match calendar date ranges to your academic or fiscal year
- Use distinct colors for weekly offs, local holidays, and breaks
- Link calendars to employees promptly after creation

### For Ongoing Management
- Update calendars when public holiday announcements change
- Create separate calendars for different employee groups if needed
- Review and refresh calendars at year boundaries

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Create calendars before leave periods begin.</Do>
  <Do>Link calendars to all employees.</Do>
  <Do>Use employee groups for differentiated calendars.</Do>
  <Do>Review holidays annually for accuracy.</Do>
  <Dont>Use School Calendar as the primary holiday source for staff leave.</Dont>
  <Dont>Forget to update calendars when public holidays change.</Dont>
  <Dont>Leave employees without a linked calendar.</Dont>
</DoDont>


## Common Questions

**Q: Can one calendar apply to multiple schools?**
A: A calendar is linked to one school, but employees in child schools may resolve it through lineage if no closer match exists.

**Q: What if an employee changes groups mid-year?**
A: Update their Employee Group and Current Holiday List to match their new calendar.

**Q: Do I need to recreate the calendar every year?**
A: Yes. Create a new calendar for each academic year with updated dates.

**Q: Why are leave calculations wrong?**
A: Check that the employee has a Current Holiday List set, and that the calendar covers the requested date range.

**Q: Can I add a one-off holiday?**
A: Yes. Add it manually to the Holidays table, or use the break period generator for short ranges.

## Related Docs

<RelatedDocs
  slugs="leave-management,leave-application,employee"
  title="Continue With Leave and HR Docs"
/>


## Technical Notes (IT)

- **DocType**: `Staff Calendar` with child `Staff Calendar Holidays`
- **Employee Link**: `Employee.current_holiday_lis`
- **Resolution**: School lineage-based with employee group matching
- **Auto-refresh**: Staff Calendar writes re-sync affected Employee rows
- **Leave Integration**: Staff Calendar is the exclusive HR holiday source
