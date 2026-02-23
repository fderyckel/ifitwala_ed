# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import comma_or


def validate_status(status, options):
    if status not in options:
        frappe.throw(_("Status must be one of {0}").format(comma_or(options)))
