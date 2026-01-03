# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/hr/doctype/employee_booking/employee_booking.py

import frappe
from frappe.model.document import Document


class EmployeeBooking(Document):
	pass



def on_doctype_update():
	# For conflict checks: employee + time window
	frappe.db.add_index("Employee Booking", fields=["employee", "from_datetime", "to_datetime"])

	# For cleanup / upsert by source document
	frappe.db.add_index("Employee Booking", fields=["source_doctype", "source_name"])
