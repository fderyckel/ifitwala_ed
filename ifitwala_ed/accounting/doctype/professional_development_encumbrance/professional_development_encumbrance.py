# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from ifitwala_ed.hr.professional_development_utils import validate_professional_development_encumbrance


class ProfessionalDevelopmentEncumbrance(Document):
    def validate(self):
        validate_professional_development_encumbrance(self)


def on_doctype_update():
    frappe.db.add_index(
        "Professional Development Encumbrance",
        ["organization", "school", "status"],
        index_name="idx_pd_encumbrance_scope_status",
    )
