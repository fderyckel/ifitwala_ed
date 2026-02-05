# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import frappe.share


def delete_events(ref_type, ref_name):
	events = (
		frappe.db.sql_list(
			""" SELECT
			distinct `tabEvent`.name
		from
			`tabEvent`, `tabEvent Participants`
		where
			`tabEvent`.name = `tabEvent Participants`.parent
			and `tabEvent Participants`.reference_doctype = %s
			and `tabEvent Participants`.reference_docname = %s
		""",
			(ref_type, ref_name),
		)
		or []
	)

	if events:
		frappe.delete_doc("Event", events, for_reload=True)