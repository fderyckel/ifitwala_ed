frappe.treeview_settings["Account"] = {
	title: __("Chart of Accounts"),
	breadcrumb: __("Accounting"),
	root_label: __("Chart of Accounts"),
	get_tree_root: false,
	get_tree_nodes: "frappe.desk.treeview.get_children",
	add_tree_node_url: "frappe.desk.treeview.add_node",
	filters: [
		{
			fieldname: "organization",
			fieldtype: "Link",
			label: __("Organization"),
			options: "Organization",
			reqd: 1,
		},
	],
};
