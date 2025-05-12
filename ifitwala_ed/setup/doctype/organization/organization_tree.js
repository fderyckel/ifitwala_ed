// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

frappe.treeview_settings["Organization"] = {
    ignore_fields: ["parent_organization"],
    get_tree_nodes: "ifitwala_ed.setup.doctype.organization.organization.get_children",
    add_tree_node: "ifitwala_ed.setup.doctype.organization.organization.add_node",
    root_label: "All Organizations",
    get_tree_root: false,
    breadcrumb: "School Settings",
    
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
            action: function () {
                frappe.new_doc("Organization", true);
            },
            condition: 'frappe.boot.user.can_create.indexOf("Organization") !== -1',
        },
    ],

    onload: function (treeview) {
        treeview.make_tree();
    },
};
