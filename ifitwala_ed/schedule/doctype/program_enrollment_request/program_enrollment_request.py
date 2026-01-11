# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.schedule.enrollment_request_utils import validate_program_enrollment_request


class ProgramEnrollmentRequest(Document):
	def validate(self):
		"""
		Server-side guardrails for override workflow.
		- Only Academic Admin / Curriculum Coordinator / Admission Manager can approve overrides.
		- Approval requires a reason + stamps who/when.
		- If request doesn't require override, it cannot be approved.
		"""
		APPROVE_ROLES = {"Academic Admin", "Curriculum Coordinator", "Admission Manager"}

		def _user_has_any_role(roles: set[str]) -> bool:
			return bool(set(frappe.get_roles(frappe.session.user)) & roles)

		requires_override = int(self.requires_override or 0)
		override_approved = int(self.override_approved or 0)

		# If not required, approval cannot be set
		if not requires_override and override_approved:
			frappe.throw(_("Override Approved cannot be set when Requires Override is not checked."))

		# If approving, enforce roles + reason + stamps
		if override_approved:
			if not _user_has_any_role(APPROVE_ROLES):
				frappe.throw(_("Only Academic Admin, Curriculum Coordinator, or Admission Manager can approve overrides."))

			if not (self.override_reason or "").strip():
				frappe.throw(_("Override Reason is required to approve an override."))

			# Stamp who/when (idempotent)
			if not self.override_by:
				self.override_by = frappe.session.user
			if not self.override_on:
				self.override_on = now_datetime()

	def on_submit(self):
		validate_program_enrollment_request(self.name, force=1)


@frappe.whitelist()
def get_offering_catalog(program_offering):
	if not program_offering:
		frappe.throw(_("Program Offering is required."))

	rows = frappe.get_all(
		"Program Offering Course",
		filters={
			"parent": program_offering,
			"parenttype": "Program Offering",
		},
		fields=[
			"course",
			"course_name",
			"required",
			"elective_group",
			"capacity",
			"waitlist_enabled",
			"reserved_seats",
			"grade_scale",
		],
		order_by="idx asc",
	)

	return rows


@frappe.whitelist()
def validate_enrollment_request(request_name):
	return validate_program_enrollment_request(request_name, force=1)
