frappe.treeview_settings["Account"] = {
	title: __("Chart of Accounts"),
	breadcrumb: __("Accounting"),
	root_label: __("Chart of Accounts"),
	get_tree_root: false,
	get_tree_nodes: "ifitwala_ed.accounting.doctype.account.account.get_children",
	add_tree_node: "frappe.desk.treeview.add_node",
	show_expand_all: true,
	ignore_fields: ["parent_account"],
	filters: [
		{
			fieldname: "organization",
			fieldtype: "Link",
			label: __("Organization"),
			options: "Organization",
			reqd: 1,
		},
	],
	fields: [
		{ fieldtype: "Data", fieldname: "account_name", label: __("Account Name"), reqd: 1 },
		{ fieldtype: "Data", fieldname: "account_number", label: __("Account Number") },
		{ fieldtype: "Check", fieldname: "is_group", label: __("Is Group") },
		{
			fieldtype: "Select",
			fieldname: "root_type",
			label: __("Root Type"),
			options: ["Asset", "Liability", "Equity", "Income", "Expense"].join("\n"),
			depends_on: "eval:doc.is_group && !doc.parent_account",
		},
		{
			fieldtype: "Select",
			fieldname: "account_type",
			label: __("Account Type"),
			options: frappe.get_meta("Account").fields.find((field) => field.fieldname === "account_type")?.options || "",
		},
		{
			fieldtype: "Link",
			fieldname: "account_currency",
			label: __("Currency"),
			options: "Currency",
		},
	],
	onload(treeview) {
		treeview.make_tree();
	},
};
