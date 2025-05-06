// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

frappe.treeview_settings["Organization"] = {
    get_tree_nodes: "ifitwala_ed.setup.doctype.organization.organization.get_children",
    get_tree_root: false,
    breadcrumb: "School Settings",
    disable_add_node: false,

    toolbar: [
        { toggle_btn: true },
        {
            label: __("Edit"),
            condition: node => !node.is_root,
            click: node => frappe.set_route("Form", "Organization", node.data.value)
        }
    ],

    menu_items: [
        {
            label: __("New Organization"),
            action: () => frappe.new_doc("Organization", true),
            condition: 'frappe.boot.user.can_create.indexOf("Organization") !== -1'
        }
    ],

    onload(treeview) {
        treeview.make_tree();
    },

    post_render(treeview) {
        if (treeview.tree?.open_all) {
            treeview.tree.open_all();
        }
    }
};
