// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.treeview_settings["Employee"] = {
	get_tree_nodes: "ifitwala_ed.hr.doctype.employee.employee.get_children",
	get_tree_root: false,
	breadcrumb: "Hr",
	disable_add_node: true,

	toolbar: [
			{ toggle_btn: true },
			{
					label: __("Edit"),
					condition: node => !node.is_root,
					click: node => frappe.set_route("Form", "Employee", node.data.value)
			}
	],

	menu_items: [
			{
					label: __("New Employee"),
					action: () => frappe.new_doc("Employee", true),
					condition: 'frappe.boot.user.can_create.indexOf("Employee") !== -1'
			}
	],

	onload(treeview) {
			frappe.call({
					method: "ifitwala_ed.hr.doctype.employee.employee.get_all_organizations",
					callback: function (r) {
							const orgs = r.message || [];
							const filter_field = treeview.page.fields_dict.organization;
							filter_field.df.options = ["All Organizations"].concat(orgs);
							filter_field.refresh();
					}
			});

			treeview.make_tree();
	},

	post_render(treeview) {
			if (treeview.tree?.open_all) {
					treeview.tree.open_all();
			}
	}
};
