// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Enrollment Trend Report"] = {
  filters: [
    {
      fieldname: "school",
      label: __("School"),
      fieldtype: "Link",
      options: "School",
      reqd: 0
    }
  ]
};
