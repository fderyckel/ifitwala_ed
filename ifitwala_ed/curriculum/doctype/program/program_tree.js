// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.treeview_settings["Program"] = {
	breadcrumb: "Curriculum",
	title: __("Program Tree"),
	root_label: "All Programs",
	get_tree_root: false, // let frappe load based on is_group + parent_program
	get_tree_nodes: "frappe.desk.treeview.get_children",
	add_tree_node: "frappe.desk.treeview.add_node",
	filters: [
		{
			fieldname: "school",
			fieldtype: "Link",
			options: "School",
			label: __("School"),
			get_query: function () {
				return {
					filters: {
						name: ["in", frappe.boot.user.defaults.school || []]
					}
				};
			}
		}
	],
	fields: [
		{
			fieldtype: "Data",
			fieldname: "program_name",
			label: __("Program Name"),
			reqd: 1
		},
		{
			fieldtype: "Check",
			fieldname: "is_group",
			label: __("Group Node")
		},
	],
	ignore_fields: ["parent_program"],
	onload: function(treeview) {
		// optional callback
	}
};
