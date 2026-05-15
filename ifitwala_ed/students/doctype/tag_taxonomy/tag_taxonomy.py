# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/tag_taxonomy/tag_taxonomy.py

import frappe
from frappe import _
from frappe.model.document import Document


class TagTaxonomy(Document):
    def validate(self):
        if self.school and not self.organization:
            self.organization = frappe.db.get_value("School", self.school, "organization")
        if self.school and not self.organization:
            frappe.throw(_("Organization is required when school is set."))
