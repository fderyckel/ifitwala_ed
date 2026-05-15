# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PGPPlan(Document):
    def before_save(self):
        # Ensure the PGP Template is set before attempting to populate stakeholders
        if not self.pgp_template:
            frappe.throw(_("A PGP Template is required to populate stakeholders."))

        # Clear existing stakeholders (to avoid duplicates on update)
        self.pgp_plan_stakeholders = []

        # Fetch stakeholders directly from the template using frappe.get_values (efficient lookup)
        template_stakeholders = frappe.get_values(
            "PGP Template Stakeholder",
            filters={"parent": self.pgp_template},
            fieldname=[
                "name",
                "stakeholder_role",
                "eligible_designation",
                "eligible_department",
                "primary_stakeholder",
                "rating_required",
                "feedback_required",
                "comments_required",
            ],
            as_dict=True,
        )

        # Append each stakeholder to the plan
        for stakeholder in template_stakeholders:
            self.append(
                "pgp_plan_stakeholders",
                {
                    "stakeholder_role": stakeholder["stakeholder_role"],
                    "primary_stakeholder": stakeholder["primary_stakeholder"],
                    "rating_required": stakeholder["rating_required"],
                    "feedback_required": stakeholder["feedback_required"],
                    "comments_required": stakeholder["comments_required"],
                    "pgp_template_stakeholder": stakeholder["name"],
                },
            )

        # Inform the user that stakeholders have been updated
        frappe.msgprint(_("PGP Plan Stakeholders have been updated based on the linked PGP Template."))
