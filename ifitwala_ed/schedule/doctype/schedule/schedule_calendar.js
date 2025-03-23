// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.views.calendar["Schedule"] = {
  field_map: {
      start: "start",
      end: "end",
      title: "title",
      color: "color",
      allDay: "allDay",
  },
  get_events_method: "ifitwala_ed.schedule.doctype.schedule.schedule.get_events",
  filters: [
      {
          fieldtype: "Link",
          fieldname: "academic_year",
          options: "Academic Year",
          label: __("Academic Year"),
          default: frappe.datetime.get_today()
      },
      {
          fieldtype: "Link",
          fieldname: "instructor",
          options: "Instructor",
          label: __("Instructor"),
          depends_on: 'eval: frappe.user.has_role("Academic Admin")'
      }
  ]
};
