# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet


class Organization(NestedSet):
    pass


@frappe.whitelist()
def get_children(doctype, parent=None, organization=None, is_root=False):
	# Use the explicit root label to avoid recursion
	if is_root or parent == "All Organizations" or not parent:
		parent_filter = ""
	else:
		parent_filter = parent

	# Fetch child organizations
	return frappe.db.sql(
        """
        SELECT
            name as value,
            organization_name as title,
            is_group as expandable
        FROM
            `tabOrganization`
        WHERE
            ifnull(parent_organization, '') = %s
        ORDER BY
            name
        """,
        (parent_filter,),
        as_dict=True
    )
   



@frappe.whitelist()
def add_node():
    from frappe.desk.treeview import make_tree_args
    
    args = frappe.form_dict 
    args = make_tree_args(**args) 
    
    if args.parent_organization == "All Organizations":
        args.parent_organization = None 
        
    frappe.get_doc(args).insert()   