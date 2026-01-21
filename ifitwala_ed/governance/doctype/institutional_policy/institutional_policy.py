# ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.py

import frappe
from frappe import _
from frappe.model.document import Document
from ifitwala_ed.governance.policy_utils import ensure_policy_admin


class InstitutionalPolicy(Document):
	def before_insert(self):
		ensure_policy_admin()
		if not self.organization:
			frappe.throw(_("Organization is required."))
		self._validate_unique_policy_key()
		self._validate_school_organization()

	def before_save(self):
		ensure_policy_admin()
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if not before:
			return
		self._enforce_immutability(before)

	def before_delete(self):
		frappe.throw(_("Institutional Policies cannot be deleted. Deactivate instead."))

	def _validate_unique_policy_key(self):
		if not self.policy_key or not self.organization:
			return
		exists = frappe.db.exists(
			"Institutional Policy",
			{
				"policy_key": self.policy_key,
				"organization": self.organization,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(_("Policy Key must be unique within the Organization."))

	def _validate_school_organization(self):
		if not self.school:
			return
		org = frappe.db.get_value("School", self.school, "organization")
		if org and self.organization and org != self.organization:
			frappe.throw(_("School must belong to the same Organization as the policy."))

	def _enforce_immutability(self, before):
		for field in ("policy_key", "organization", "school"):
			if before.get(field) != self.get(field):
				frappe.throw(_("{0} is immutable once set.").format(field.replace("_", " ").title()))
