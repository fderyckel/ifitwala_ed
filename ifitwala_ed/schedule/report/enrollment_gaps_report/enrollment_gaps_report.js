frappe.query_reports["Enrollment Gaps — Missing Program or Group"] = {
  filters: [
    {
      fieldname: "academic_year",
      label: __("Academic Year"),
      fieldtype: "Link",
      options: "Academic Year",
      reqd: 1
    }
  ]
};
