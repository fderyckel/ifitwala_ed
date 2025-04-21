# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_root_of(doctype):
	"""Get root element of a DocType with a tree structure"""
	result = frappe.db.sql_list("""select name from `tab%s` where lft=1 and rgt=(select max(rgt) from `tab%s` where docstatus < 2)""" %
		(doctype, doctype))
	return result[0] if result else None

def get_ancestors_of(doctype, name):
	"""Get ancestor elements of a DocType with a tree structure"""
	lft, rgt = frappe.db.get_value(doctype, name, ["lft", "rgt"])
	result = frappe.db.sql_list("""select name from `tab%s` where lft<%s and rgt>%s order by lft desc""" % (doctype, "%s", "%s"), (lft, rgt))
	return result or []


def insert_record(records):
	for r in records:
		doc = frappe.new_doc(r.get("doctype"))
		doc.update(r)
		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError as e:
			# pass DuplicateEntryError and continue
			if e.args and e.args[0]==doc.doctype and e.args[1]==doc.name:
				# make sure DuplicateEntryError is for the exact same doc and not a related doc
				pass
			else:
				raise
