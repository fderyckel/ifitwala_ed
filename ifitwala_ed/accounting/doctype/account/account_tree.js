frappe.treeview_settings["Account"] = {
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
