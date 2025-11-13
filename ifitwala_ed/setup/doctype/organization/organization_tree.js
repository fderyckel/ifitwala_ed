// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

// ifitwala_ed/public/js/organization_tree.js

frappe.treeview_settings["Organization"] = {
	root_label: "All Organizations",
	get_tree_nodes: "ifitwala_ed.setup.doctype.organization.organization.get_children",
	add_tree_node: "ifitwala_ed.setup.doctype.organization.organization.add_node",
	get_tree_root: false,
	breadcrumb: "School Settings",
	disable_add_node: false,
	show_expand_all: true,

	fields: [
		{ fieldtype: "Data", fieldname: "organization_name", label: __("Organization Name"), reqd: 1 },
		{ fieldtype: "Data", fieldname: "abbr", label: __("Organization Abbreviation"), reqd: 1 },
		{ fieldtype: "Check", fieldname: "is_group", label: __("Is Group") },
	],

	toolbar: [
		{ toggle_btn: true },
		{
			label: __("Add Child"),
			condition: (node) => node && (node.is_root || node.data?.expandable),
			click: (node) => {
				const parent = node.is_root ? "All Organizations" : node.data.value;
				const tv = frappe.treeview_settings["Organization"]._tree;

				frappe.prompt(
					[
						{ fieldtype: "Data", fieldname: "organization_name", label: __("Organization Name"), reqd: 1 },
						{ fieldtype: "Data", fieldname: "abbr", label: __("Organization Abbreviation"), reqd: 1 },
						{ fieldtype: "Check", fieldname: "is_group", label: __("Is Group") },
					],
					(values) => {
						values.parent_organization = parent;
						frappe.call({
							method: "ifitwala_ed.setup.doctype.organization.organization.add_node",
							args: values,
							callback: () => tv && tv.make_tree(),
						});
					},
					__("Add Child under {0}", [parent]),
					__("Create")
				);
			},
		},
		{
			label: __("Edit"),
			condition: (node) => !node.is_root,
			click: (node) => frappe.set_route("Form", "Organization", node.data.value),
		},
	],

	filters: [
		{
			fieldname: "organization",
			fieldtype: "Link",
			options: "Organization",
			label: __("Organization"),
			get_query() {
				return { filters: [["Organization", "is_group", "=", 1]] };
			},
		},
	],

	menu_items: [
		{
			label: __("New Organization"),
			action: () => frappe.new_doc("Organization", true),
			condition: 'frappe.boot.user.can_create.indexOf("Organization") !== -1',
		},
	],

	onload(treeview) {
		frappe.treeview_settings["Organization"]._tree = treeview;
		treeview.make_tree();
	},
};

