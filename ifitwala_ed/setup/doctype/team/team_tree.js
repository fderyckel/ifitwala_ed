// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/public/js/team_tree.js

frappe.treeview_settings["Team"] = {
	root_label: "All Teams",
	get_tree_nodes: "ifitwala_ed.setup.doctype.team.team.get_children",
	add_tree_node: "ifitwala_ed.setup.doctype.team.team.add_node",
	get_tree_root: false,
	breadcrumb: "School Settings",
	show_expand_all: true,

	// Extra fields shown in the built-in "Add Child" dialog.
	// Defaults are pulled from active filters so new nodes inherit Organization/School.
	fields: [
		{ fieldtype: "Data", fieldname: "team_name", label: __("Team Name"), reqd: 1 },
		{ fieldtype: "Data", fieldname: "team_code", label: __("Team Code") },
		{ fieldtype: "Check", fieldname: "is_group", label: __("Is Group") },
		{ fieldtype: "Link", fieldname: "organization", label: __("Organization"), options: "Organization" },
		{
			fieldtype: "Link",
			fieldname: "school",
			label: __("School"),
			options: "School",
			get_query: () => {
				const org = frappe.ui.treeview_filters?.Team?.organization?.get_value?.() || null;
				return org ? { filters: [["School", "organization", "=", org]] } : {};
			},
		},
	],

	toolbar: [
		{ toggle_btn: true },

		{
			label: __("Add Child"),
			// Only under root or group nodes
			condition: (node) => node && (node.is_root || node.data?.expandable),
			click: (node) => {
				const parent = node.is_root ? "All Teams" : node.data.value;
				const tv = frappe.treeview_settings["Team"]._tree;

				// Pull current filter values so the dialog defaults match the view
				const orgFilter = frappe.ui.treeview_filters?.Team?.organization?.get_value?.() || "";
				const schoolFilter = frappe.ui.treeview_filters?.Team?.school?.get_value?.() || "";

				frappe.prompt(
					[
						{ fieldtype: "Data", fieldname: "team_name", label: __("Team Name"), reqd: 1 },
						{ fieldtype: "Data", fieldname: "team_code", label: __("Team Code") },
						{ fieldtype: "Check", fieldname: "is_group", label: __("Is Group") },
						{ fieldtype: "Link", fieldname: "organization", label: __("Organization"), options: "Organization", default: orgFilter },
						{
							fieldtype: "Link",
							fieldname: "school",
							label: __("School"),
							options: "School",
							default: schoolFilter,
							get_query: () => {
								const org = frappe.ui.treeview_filters?.Team?.organization?.get_value?.() || orgFilter || null;
								return org ? { filters: [["School", "organization", "=", org]] } : {};
							},
						},
					],
					(values) => {
						values.parent_team = parent;
						frappe.call({
							method: "ifitwala_ed.setup.doctype.team.team.add_node",
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
			click: (node) => frappe.set_route("Form", "Team", node.data.value),
		},
	],

	// Filters shown above the tree (ERPNext pattern). These are passed to get_children(**kwargs).
	filters: [
		{
			fieldname: "organization",
			fieldtype: "Link",
			options: "Organization",
			label: __("Organization"),
		},
		{
			fieldname: "school",
			fieldtype: "Link",
			options: "School",
			label: __("School"),
			get_query: () => {
				const org =
					(frappe.ui.treeview_filters?.Team?.organization &&
						frappe.ui.treeview_filters.Team.organization.get_value()) ||
					null;
				return org ? { filters: [["School", "organization", "=", org]] } : {};
			},
		},
	],

	menu_items: [
		{
			label: __("New Team"),
			action: () => frappe.new_doc("Team", true),
			condition: 'frappe.boot.user.can_create.indexOf("Team") !== -1',
		},
	],

	onload(treeview) {
		// Keep handle for toolbar refresh and register filters object for query fns.
		frappe.treeview_settings["Team"]._tree = treeview;
		// Expose filter widgets for get_query lookups above
		frappe.ui.treeview_filters = frappe.ui.treeview_filters || {};
		frappe.ui.treeview_filters.Team = treeview.page && treeview.page.fields_dict ? treeview.page.fields_dict : {};
		treeview.make_tree();
	},
};
