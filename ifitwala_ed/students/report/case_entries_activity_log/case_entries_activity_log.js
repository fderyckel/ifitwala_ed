// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/students/report/case_entry_activity_log/case_entry_activity_log.js

frappe.query_reports["Case Entry Activity Log"] = {
	filters: [
		{
			fieldname: "from_date", label: __("From Date"),
			fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			reqd: 1
		},
		{
			fieldname: "to_date", label: __("To Date"),
			fieldtype: "Date", default: frappe.datetime.get_today(),
			reqd: 1
		},
		{ fieldname: "student", label: __("Student"), fieldtype: "Link", options: "Student" },
		{ fieldname: "referral", label: __("Referral"), fieldtype: "Link", options: "Student Referral" },
		{ fieldname: "school", label: __("School"), fieldtype: "Link", options: "School" },
		{ fieldname: "program", label: __("Program"), fieldtype: "Link", options: "Program" },
		{ fieldname: "academic_year", label: __("Academic Year"), fieldtype: "Link", options: "Academic Year" },
		{ fieldname: "case_manager", label: __("Case Manager"), fieldtype: "Link", options: "User" },
		{ fieldname: "assignee", label: __("Assignee"), fieldtype: "Link", options: "User" },
		{
			fieldname: "entry_type", label: __("Entry Type"),
			fieldtype: "Select",
			options: ["", "Meeting", "Counseling Session", "Academic Support", "Check-in", "Family Contact", "External Referral", "Safety Plan", "Review", "Other"].join("\n")
		},
		{
			fieldname: "entry_status", label: __("Entry Status"),
			fieldtype: "Select", options: ["", "Open", "In Progress", "Done", "Cancelled"].join("\n")
		},
		{
			fieldname: "case_severity", label: __("Case Severity"),
			fieldtype: "Select", options: ["", "Low", "Moderate", "High", "Critical"].join("\n")
		},
		{
			fieldname: "case_status", label: __("Case Status"),
			fieldtype: "Select", options: ["", "Open", "In Progress", "On Hold", "Escalated", "Closed"].join("\n")
		}
	]
};
