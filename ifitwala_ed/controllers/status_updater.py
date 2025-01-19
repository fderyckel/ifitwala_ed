import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import comma_or, flt, get_link_to_form, getdate, now, nowdate


def validate_status(status, options):
	if status not in options:
		frappe.throw(_("Status must be one of {0}").format(comma_or(options)))

