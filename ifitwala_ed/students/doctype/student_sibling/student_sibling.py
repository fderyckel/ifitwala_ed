# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StudentSibling(Document):
    pass


def on_doctype_update():
    # speed up reverse lookups and parent scans after the child table exists
    frappe.db.add_index("Student Sibling", ["student"])
    frappe.db.add_index("Student Sibling", ["parent"])
