# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from ifitwala_ed.hr.professional_development_utils import validate_professional_development_budget


class ProfessionalDevelopmentBudget(Document):
    def validate(self):
        validate_professional_development_budget(self)


def on_doctype_update():
    frappe.db.add_index(
        "Professional Development Budget",
        ["organization", "school", "academic_year", "is_active"],
        index_name="idx_pd_budget_scope_active",
    )
    frappe.db.add_index(
        "Professional Development Budget",
        ["employee", "department", "program"],
        index_name="idx_pd_budget_targeting",
    )
