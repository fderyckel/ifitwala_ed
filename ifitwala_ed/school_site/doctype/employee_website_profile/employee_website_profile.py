# ifitwala_ed/school_site/doctype/employee_website_profile/employee_website_profile.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.website.public_people import (
    WORKFLOW_TRANSITIONS,
    compute_employee_profile_status,
    invalidate_public_people_cache,
    normalize_workflow_state,
)


class EmployeeWebsiteProfile(Document):
    def validate(self):
        self._ensure_workflow_state()
        self._sync_school_from_employee()
        self._sync_status_from_employee()
        self._validate_unique_profile()
        self._validate_employee_scope()

    def on_update(self):
        invalidate_public_people_cache()

    def after_insert(self):
        invalidate_public_people_cache()

    def on_trash(self):
        invalidate_public_people_cache()

    def _ensure_workflow_state(self):
        self.workflow_state = normalize_workflow_state(self.workflow_state)

    def _sync_school_from_employee(self):
        if self.school or not self.employee:
            return
        employee_school = frappe.db.get_value("Employee", self.employee, "school")
        if employee_school:
            self.school = employee_school

    def _sync_status_from_employee(self):
        employee_is_public = False
        if self.employee:
            row = frappe.db.get_value(
                "Employee",
                self.employee,
                ["show_on_website", "school"],
                as_dict=True,
            )
            employee_is_public = bool(
                row and int(row.get("show_on_website") or 0) == 1 and (row.get("school") or "") == (self.school or "")
            )

        self.status = compute_employee_profile_status(
            employee_is_public=employee_is_public,
            workflow_state=self.workflow_state,
        )

    def _validate_unique_profile(self):
        exists = frappe.db.exists(
            "Employee Website Profile",
            {
                "employee": self.employee,
                "school": self.school,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(
                _("An Employee Website Profile already exists for this Employee and School."),
                frappe.ValidationError,
            )

    def _validate_employee_scope(self):
        if not self.employee or not self.school:
            return

        employee_school = frappe.db.get_value("Employee", self.employee, "school")
        if not employee_school:
            frappe.throw(
                _("Employee must belong to a School before website publication."),
                frappe.ValidationError,
            )
        if employee_school != self.school:
            frappe.throw(
                _("Employee Website Profile school must match the Employee school."),
                frappe.ValidationError,
            )

    def _get_employee_publication_readiness(self) -> bool:
        if not self.employee or not self.school:
            return False

        row = frappe.db.get_value(
            "Employee",
            self.employee,
            ["show_on_website", "school"],
            as_dict=True,
        )
        if not row:
            return False
        return bool(int(row.get("show_on_website") or 0) == 1 and (row.get("school") or "") == self.school)

    def _assert_transition_allowed(self, action: str) -> str:
        action_key = (action or "").strip()
        transition = WORKFLOW_TRANSITIONS.get(action_key)
        if not transition:
            frappe.throw(
                _("Unknown workflow action: {0}").format(action_key or _("(empty)")),
                frappe.ValidationError,
            )

        current_state = normalize_workflow_state(self.workflow_state)
        if current_state not in transition["from_states"]:
            frappe.throw(
                _("Cannot run '{0}' from workflow state '{1}'.").format(action_key, current_state),
                frappe.ValidationError,
            )

        user_roles = set(frappe.get_roles())
        allowed_roles = set(transition["roles"])
        if not user_roles.intersection(allowed_roles):
            frappe.throw(
                _("You do not have permission to run workflow action: {0}.").format(action_key),
                frappe.PermissionError,
            )

        return action_key

    def apply_workflow_action(self, action: str):
        action_key = self._assert_transition_allowed(action)
        target_state = WORKFLOW_TRANSITIONS[action_key]["to_state"]
        if target_state == "Published" and not self._get_employee_publication_readiness():
            frappe.throw(
                _("Cannot publish until the Employee is assigned to this School and Show on Website is enabled."),
                frappe.ValidationError,
            )

        self.workflow_state = target_state
        self._sync_status_from_employee()


@frappe.whitelist()
def transition_workflow_state(name: str, action: str) -> dict:
    doc = frappe.get_doc("Employee Website Profile", name)
    if not frappe.has_permission(doc=doc, ptype="write"):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    doc.apply_workflow_action(action)
    doc.save()
    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "status": doc.status,
    }
