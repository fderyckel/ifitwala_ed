# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from ifitwala_ed.hr.professional_development_utils import validate_professional_development_request


class ProfessionalDevelopmentRequest(Document):
    def validate(self):
        validate_professional_development_request(self)


def on_doctype_update():
    frappe.db.add_index(
        "Professional Development Request",
        ["employee", "academic_year", "status"],
        index_name="idx_pd_request_employee_ay_status",
    )
    frappe.db.add_index(
        "Professional Development Request",
        ["organization", "school", "status"],
        index_name="idx_pd_request_scope_status",
    )
