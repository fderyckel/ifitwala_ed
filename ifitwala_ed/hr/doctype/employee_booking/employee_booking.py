# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeBooking(Document):
	pass



def on_doctype_update():
	"""
	Ensure helpful indexes exist for fast conflict checks and source lookups.

	Called automatically by Frappe when the DocType is updated.
	"""
	# For conflict checks: employee + time window
	frappe.db.add_index(
		"Employee Booking",
		fields=["employee", "from_datetime", "to_datetime"],
		index_name="idx_employee_booking_window",
	)

	# For cleanup / upsert by source document
	frappe.db.add_index(
		"Employee Booking",
		fields=["source_doctype", "source_name"],
		index_name="idx_employee_booking_source",
	)
