# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet


class Organization(NestedSet):
    pass


@frappe.whitelist()
def get_children(doctype, parent=None, organization=None, is_root=False):
	if parent is None or parent == "All Organizations":
		parent = ""

	return frappe.db.sql(
		f"""
		select
			name as value,
			is_group as expandable
		from
			`tabOrganization` org
		where
			ifnull(parent_organization, "")={frappe.db.escape(parent)}
		""",
		as_dict=1,
	)
   



@frappe.whitelist()
def add_node():
    from frappe.desk.treeview import make_tree_args
    
    args = frappe.form_dict 
    args = make_tree_args(**args) 
    
    if args.parent_organization == "All Organizations":
        args.parent_organization = None 
        
    frappe.get_doc(args).insert()   