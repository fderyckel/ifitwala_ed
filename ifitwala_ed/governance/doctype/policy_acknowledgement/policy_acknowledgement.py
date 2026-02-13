# ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from ifitwala_ed.governance.policy_utils import (
	has_guardian_role,
	has_student_role,
	has_staff_role,
	has_admissions_applicant_role,
	is_system_manager,
)
from ifitwala_ed.governance.policy_scope_utils import is_policy_organization_applicable_to_context


ACK_CONTEXT_MAP = {
	"Applicant": ("Student Applicant",),
	"Student": ("Student",),
	"Guardian": ("Guardian",),
	"Staff": ("Employee",),
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

		allowed_contexts = ACK_CONTEXT_MAP.get(self.acknowledged_for)
		if allowed_contexts and self.context_doctype not in allowed_contexts:
			frappe.throw(_("Context DocType does not match acknowledged_for."))

		self._validate_policy_scope_for_context()

	def _validate_policy_scope_for_context(self):
		policy = frappe.db.get_value(
			"Policy Version", self.policy_version, "institutional_policy"
		)
		policy_org = frappe.db.get_value("Institutional Policy", policy, "organization")
		if not policy_org:
			return

		context_orgs = self._resolve_context_organizations()
		if not context_orgs:
			debug_payload = {
				"policy_version": self.policy_version,
				"policy_organization": policy_org,
				"acknowledged_for": self.acknowledged_for,
				"context_doctype": self.context_doctype,
				"context_name": self.context_name,
			}
			frappe.log_error(
				message=frappe.as_json(debug_payload),
				title="Policy acknowledgement scope resolution failed",
			)
			frappe.throw(_("Could not resolve Organization scope for acknowledgement context."))

		if any(
			is_policy_organization_applicable_to_context(
				policy_organization=policy_org,
				context_organization=context_org,
			)
			for context_org in context_orgs
		):
			return

		frappe.throw(_("Policy does not apply to this acknowledgement context organization."))

	def _resolve_context_organizations(self) -> list[str]:
		if self.context_doctype == "Student Applicant":
			org = frappe.db.get_value("Student Applicant", self.context_name, "organization")
			return [org] if org else []

		if self.context_doctype == "Employee":
			org = frappe.db.get_value("Employee", self.context_name, "organization")
			return [org] if org else []

		if self.context_doctype == "Student":
			return self._organizations_for_students([self.context_name])

		if self.context_doctype == "Guardian":
			student_names = frappe.get_all(
				"Student Guardian",
				filters={"guardian": self.context_name},
				pluck="parent",
			)
			if not student_names:
				return []
			return self._organizations_for_students(student_names)

		return []

	def _organizations_for_students(self, student_names: list[str]) -> list[str]:
		if not student_names:
			return []

		rows = frappe.get_all(
			"Student",
			filters={"name": ["in", student_names]},
			fields=["anchor_school", "student_applicant"],
		)

		orgs: list[str] = []
		seen = set()
		for row in rows:
			anchor_school = row.get("anchor_school")
			if anchor_school:
				org = frappe.db.get_value("School", anchor_school, "organization")
				if org and org not in seen:
					seen.add(org)
					orgs.append(org)

			student_applicant = row.get("student_applicant")
			if student_applicant:
				org = frappe.db.get_value("Student Applicant", student_applicant, "organization")
				if org and org not in seen:
					seen.add(org)
					orgs.append(org)

		return orgs

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

	def _guardian_name_for_user(self) -> str | None:
		return frappe.db.get_value("Guardian", {"user": frappe.session.user}, "name")

	def _guardian_linked_to_student(self, guardian_name: str, student_name: str) -> bool:
		return bool(
			frappe.db.exists(
				"Student Guardian",
				{
					"parent": student_name,
					"parenttype": "Student",
					"parentfield": "guardians",
					"guardian": guardian_name,
				},
			)
		)

	def _is_applicant_user_for_context(self) -> bool:
		if self.context_doctype != "Student Applicant":
			return False
		applicant_user = frappe.db.get_value(
			"Student Applicant", self.context_name, "applicant_user"
		)
		return bool(applicant_user and applicant_user == frappe.session.user)

	def _role_validation_error(self) -> str | None:
		if self.acknowledged_for == "Applicant":
			if not has_admissions_applicant_role():
				return _("Only Admissions Applicants can acknowledge Applicant policies.")
			if not self._is_applicant_user_for_context():
				return _("You do not have permission to acknowledge policies for this Applicant.")
			return None
		if self.acknowledged_for == "Student":
			if has_student_role():
				return None
			if has_guardian_role():
				guardian_name = self._guardian_name_for_user()
				if not guardian_name:
					return _("Guardian account is not linked to a Guardian record.")
				if not self._guardian_linked_to_student(guardian_name, self.context_name):
					return _("You are not a guardian of this student.")
				return None
			return _("You do not have permission to acknowledge student policies.")
		if self.acknowledged_for == "Guardian":
			if not has_guardian_role():
				return _("Only Guardians can acknowledge Guardian policies.")
			guardian_name = self._guardian_name_for_user()
			if not guardian_name:
				return _("Guardian account is not linked to a Guardian record.")
			if self.context_name != guardian_name:
				return _("Guardians may only acknowledge policies for themselves.")
			return None
		if self.acknowledged_for == "Staff":
			if has_staff_role():
				return None
			return _("Only Staff may acknowledge Staff policies.")
		return _("Invalid acknowledgement context.")

	def _is_role_allowed_for_ack(self) -> bool:
		return self._role_validation_error() is None

	def _validate_role_for_acknowledgement(self):
		error = self._role_validation_error()
		if not error:
			return
		if is_system_manager():
			return
		frappe.throw(error)
