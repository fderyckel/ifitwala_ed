# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from ifitwala_ed.hr.professional_development_utils import validate_professional_development_theme


class ProfessionalDevelopmentTheme(Document):
    def validate(self):
        validate_professional_development_theme(self)


def on_doctype_update():
    frappe.db.add_index(
        "Professional Development Theme",
        ["organization", "school", "is_active"],
        index_name="idx_pd_theme_scope_active",
    )
