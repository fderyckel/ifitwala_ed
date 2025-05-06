// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt


frappe.treeview_settings["Organization"] = {
  get_tree_nodes: "ifitwala_ed.setup.doctype.organization.organization.get_children",
  filters: [
      {
          fieldname: "organization_type",
          fieldtype: "Select",
          options: ["All Types"].concat(
              frappe.meta.get_docfield("Organization", "organization_type").options.split("\n")
          ),
          label: __("Type"),
          default: "All Types"
      }
  ],
  breadcrumb: "Hr",
  disable_add_node: false,
  get_tree_root: false,
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
      // build the tree structure
      treeview.make_tree();
  },

  post_render(treeview) {
      // expand all nodes in the underlying Tree instance
      if (treeview.tree && typeof treeview.tree.open_all === "function") {
          treeview.tree.open_all();
      }
  }
};
