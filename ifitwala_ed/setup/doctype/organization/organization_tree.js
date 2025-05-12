// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

frappe.treeview_settings["Organization"] = {
    root_label: "All Organizations", 
    get_tree_nodes: "frappe.desk.treeview.get_children",
    add_tree_node:  "frappe.desk.treeview.add_node",
    get_tree_root: false,
    breadcrumb: "School Settings",
    disable_add_node: false,
    show_expand_all: true,

    toolbar: [
        { toggle_btn: true },
        {
            label: __("Edit"),
            condition: node => !node.is_root,
            click: node => frappe.set_route("Form", "Organization", node.data.value)
        }
    ],

    
    filters: [
        {
            fieldname: "organization",
            fieldtype: "Link",
            options: "Organization",
            label: __("Organization"),
            get_query: function () {
                return {
                    filters: [["Organization", "is_group", "=", 1]],
                };
            },
        },
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

};
