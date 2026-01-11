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
		Single enforcement point for PER workflow integrity.

		Rules:
		- If status becomes "Submitted" or "Under Review" or "Approved", we must have a fresh validation snapshot.
		- If engine says override_required, PER.requires_override must be 1.
		- If requires_override=1, status cannot be "Approved" unless override_approved=1.
		- Keep server/db efficient: validate only when needed (status change or basket change).
		"""
		target_status = (self.status or "").strip()
		needs_snapshot = target_status in {"Submitted", "Under Review", "Approved"}

		# Detect whether we must refresh validation
		status_changed = self.has_value_changed("status") if not self.is_new() else True
		basket_changed = self.has_value_changed("courses") if not self.is_new() else True

		# If we're not moving into a gate state, do nothing.
		if not needs_snapshot:
			return

		# If nothing relevant changed and we already have a Valid/Invalid snapshot, keep it.
		if not self.is_new() and not status_changed and not basket_changed and (self.validation_status or "").strip() in {"Valid", "Invalid"} and self.validation_payload:
			# still enforce override gate for Approved
			if target_status == "Approved" and int(self.requires_override or 0) == 1 and int(self.override_approved or 0) != 1:
				frappe.throw(_("This request requires an override and must be override-approved before it can be Approved."))
			return

		# Force validation refresh via whitelisted util (single truth)
		result = validate_program_enrollment_request(self.name, force=1) if self.name else None

		# If doc is new (no name yet), we can't call validate_program_enrollment_request (needs saved doc).
		# So we require user to save first before submitting/approving.
		if self.is_new():
			frappe.throw(_("Please save this request before submitting for validation."))

		# Pull flags from stored fields (validate_program_enrollment_request db_set's them)
		# and enforce final gates.
		if target_status == "Approved":
			if (self.validation_status or "").strip() != "Valid":
				frappe.throw(_("Request must be Valid before it can be Approved."))

			if int(self.requires_override or 0) == 1 and int(self.override_approved or 0) != 1:
				frappe.throw(_("This request requires an override and must be override-approved before it can be Approved."))



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
