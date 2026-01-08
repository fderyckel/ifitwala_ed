# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.schedule.enrollment.enrollment_request_api import (
	validate_program_enrollment_request,
)


class ProgramEnrollmentRequest(Document):
	pass


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
	return validate_program_enrollment_request(request_name)
