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
			fieldname: "account_holder",
			label: __("Account Holder"),
			fieldtype: "Link",
			options: "Account Holder",
		},
	],
};
