// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.views.calendar["Staff Calendar"] = {
  field_map: {
    start: "holiday_date",
    // Let Frappe synthesize the exclusive all-day end from the holiday date.
    id: "name",
    title: "description",
    allDay: "allDay",
  },
  order_by: "from_date",
  get_events_method: "ifitwala_ed.hr.doctype.staff_calendar.staff_calendar.get_events",
  filters: [
    {
      fieldtype: "Link",
      fieldname: "staff_calendar",
      options: "Staff Calendar",
      label: __("Staff Calendar"),
    },
    {
      fieldtype: "Link",
      fieldname: "academic_year",
      options: "Academic Year",
      label: __("Academic Year"),
    },
    {
      fieldtype: "Link",
      fieldname: "school",
      options: "School",
      label: __("School"),
    },
    {
      fieldtype: "Link",
      fieldname: "employee_group",
      options: "Employee Group",
      label: __("Employee Group"),
    },
  ],
};
