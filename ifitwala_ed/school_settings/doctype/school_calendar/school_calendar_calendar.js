// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.views.calendar["School Calendar"] = {
  field_map: {
    start: "holiday_date",
    end: "holiday_date",
    id: "name",
    title: "description",
    allDay: "allDay",
  },
  gantt: false,
  filters: [
    {
      fieldtype: "Link",
      fieldname: "school_calendar",
      options: "School Calendar",
      label: __("School Calendar"),
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
  ],
  get_events_method:
    "ifitwala.school_settings.doctype.school_calendar.school_calendar.get_events",
};
