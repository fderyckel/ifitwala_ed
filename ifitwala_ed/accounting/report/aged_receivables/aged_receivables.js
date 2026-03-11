frappe.query_reports["Aged Receivables"] = {
	filters: [
		{
			fieldname: "organization",
			label: __("Organization"),
			fieldtype: "Link",
			options: "Organization",
			reqd: 1,
		},
		{
			fieldname: "as_of_date",
			label: __("As of Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
		},
		{
			fieldname: "account_holder",
			label: __("Account Holder"),
			fieldtype: "Link",
			options: "Account Holder",
		},
		{
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School",
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program",
		},
	],
};
