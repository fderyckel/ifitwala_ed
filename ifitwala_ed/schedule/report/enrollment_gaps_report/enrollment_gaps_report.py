# Copyright (c) 2025, François de Ryckel and contributors
# License: MIT. See license.txt

# ifitwala_ed/schedule/report/enrollment_gaps_report/enrollment_gaps_report.py

import frappe

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		SELECT name
		FROM `tabAcademic Year`
		WHERE name LIKE %(txt)s
		ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
		LIMIT %(start)s, %(page_len)s
	""", {
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len
	})


def execute(filters=None):
    return []