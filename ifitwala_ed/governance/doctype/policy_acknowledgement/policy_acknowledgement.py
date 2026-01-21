# ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from ifitwala_ed.governance.policy_utils import (
	has_guardian_role,
	has_student_role,
	has_staff_role,
	is_system_manager,
)


ACK_CONTEXT_MAP = {
	"Applicant": "Student Applicant",
	"Student": "Student",
	"Staff": "Employee",
}


class PolicyAcknowledgement(Document):
	def before_insert(self):
		self._validate_policy_version()
		self._validate_acknowledged_by()
		self._validate_context()
		self._validate_role_for_acknowledgement()
		self._validate_unique_acknowledgement()
		self.acknowledged_at = now_datetime()

	def before_save(self):
		if not self.is_new():
			frappe.throw(_("Policy Acknowledgements are append-only and cannot be edited."))

	def before_delete(self):
		frappe.throw(_("Policy Acknowledgements cannot be deleted."))

	def after_insert(self):
		if is_system_manager() and not self._is_role_allowed_for_ack():
			self.add_comment(
				"Comment",
				text=_(
					"System Manager override acknowledgement by {0} on {1}."
				).format(frappe.bold(frappe.session.user), now_datetime()),
			)

	def _validate_policy_version(self):
		if not self.policy_version:
			frappe.throw(_("Policy Version is required."))
		is_active = frappe.db.get_value("Policy Version", self.policy_version, "is_active")
		if not is_active:
			frappe.throw(_("Policy Version must be active to acknowledge."))

	def _validate_acknowledged_by(self):
		if self.acknowledged_by != frappe.session.user:
			frappe.throw(_("Acknowledged By must match the current user."))

	def _validate_context(self):
		if not self.context_doctype or not self.context_name:
			frappe.throw(_("Context DocType and Context Name are required."))

		if not frappe.db.exists("DocType", self.context_doctype):
			frappe.throw(_("Invalid context DocType."))

		if not frappe.db.exists(self.context_doctype, self.context_name):
			frappe.throw(_("Context record does not exist."))

		expected = ACK_CONTEXT_MAP.get(self.acknowledged_for)
		if expected and self.context_doctype != expected:
			frappe.throw(_("Context DocType does not match acknowledged_for."))

		if self.acknowledged_for == "Applicant":
			self._validate_applicant_policy_scope()

	def _validate_applicant_policy_scope(self):
		student_org = frappe.db.get_value(
			"Student Applicant", self.context_name, "organization"
		)
		if not student_org:
			return
		policy = frappe.db.get_value(
			"Policy Version", self.policy_version, "institutional_policy"
		)
		policy_org = frappe.db.get_value("Institutional Policy", policy, "organization")
		if policy_org and student_org and policy_org != student_org:
			frappe.throw(_("Policy does not match Applicant organization."))

	def _validate_unique_acknowledgement(self):
		exists = frappe.db.exists(
			"Policy Acknowledgement",
			{
				"policy_version": self.policy_version,
				"acknowledged_by": self.acknowledged_by,
				"context_doctype": self.context_doctype,
				"context_name": self.context_name,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(_("This acknowledgement already exists for the same context."))

	def _is_role_allowed_for_ack(self) -> bool:
		if self.acknowledged_for == "Applicant":
			return has_guardian_role()
		if self.acknowledged_for == "Student":
			return has_student_role()
		if self.acknowledged_for == "Staff":
			return has_staff_role()
		return False

	def _validate_role_for_acknowledgement(self):
		if self._is_role_allowed_for_ack():
			return
		if is_system_manager():
			return
		frappe.throw(_("You do not have permission to acknowledge this policy."))
