frappe.query_reports["Student Attribution"] = {
	filters: [
		{
			fieldname: "organization",
			label: __("Organization"),
			fieldtype: "Link",
			options: "Organization",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student",
		},
		{
			fieldname: "account_holder",
			label: __("Account Holder"),
			fieldtype: "Link",
			options: "Account Holder",
		},
	],
};
