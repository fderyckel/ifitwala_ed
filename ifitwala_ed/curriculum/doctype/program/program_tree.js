// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/curriculum/doctype/program/program_tree.js

frappe.treeview_settings["Program"] = {
	breadcrumb: "Curriculum",
	title: __("Program Tree"),
	root_label: "All Programs",
	get_tree_root: false, // NestedSet + parent_program drive the tree
	get_tree_nodes: "frappe.desk.treeview.get_children",
	add_tree_node: "frappe.desk.treeview.add_node",

	// Program is global (no School filter)
	fields: [
		{ fieldtype: "Data",  fieldname: "program_name", label: __("Program Name"), reqd: 1 },
		{ fieldtype: "Check", fieldname: "is_group",     label: __("Group Node") }
	],
	ignore_fields: ["parent_program"],

	// onload not needed
};

