# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from ifitwala_ed.hr.professional_development_utils import validate_professional_development_outcome


class ProfessionalDevelopmentOutcome(Document):
    def validate(self):
        validate_professional_development_outcome(self)


def on_doctype_update():
    frappe.db.add_index(
        "Professional Development Outcome",
        ["employee", "academic_year"],
        index_name="idx_pd_outcome_employee_ay",
    )
