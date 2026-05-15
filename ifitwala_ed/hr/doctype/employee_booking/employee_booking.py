# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/hr/doctype/employee_booking/employee_booking.py

import frappe
from frappe.model.document import Document


def _invalidate_staff_calendar_for_booking(doc, *, include_previous: bool = False) -> None:
    employees = {
        (getattr(doc, "employee", None) or "").strip(),
    }
    if include_previous and hasattr(doc, "get_doc_before_save"):
        previous = doc.get_doc_before_save()
        if previous:
            employees.add((getattr(previous, "employee", None) or "").strip())

    from ifitwala_ed.api.calendar_invalidation import invalidate_staff_calendar_for_employees

    invalidate_staff_calendar_for_employees(employees)


class EmployeeBooking(Document):
    def after_insert(self):
        _invalidate_staff_calendar_for_booking(self)

    def on_update(self):
        _invalidate_staff_calendar_for_booking(self, include_previous=True)

    def on_cancel(self):
        _invalidate_staff_calendar_for_booking(self)

    def on_trash(self):
        _invalidate_staff_calendar_for_booking(self)


def on_doctype_update():
    # For conflict checks: employee + time window
    frappe.db.add_index("Employee Booking", fields=["employee", "from_datetime", "to_datetime"])

    # For cleanup / upsert by source document
    frappe.db.add_index("Employee Booking", fields=["source_doctype", "source_name"])
    frappe.db.add_index("Employee Booking", fields=["location", "from_datetime", "to_datetime"])
