# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    filters = filters or {}
    school_filter = filters.get("school")

    # Aggregate enrollment counts per academic year
    rows = frappe.db.sql("""
        SELECT
            pe.academic_year,
            COUNT(pe.name) as enrollment_count
        FROM `tabProgram Enrollment` pe
        {where_clause}
        GROUP BY pe.academic_year
        ORDER BY MIN(ay.year_start_date) ASC
    """.format(
        where_clause="""
        LEFT JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
        WHERE pe.status = 1 {school_cond}
        """.format(
            school_cond=f"AND pe.school = %(school)s" if school_filter else ""
        )
    ), filters, as_dict=True)

    data = [[r.academic_year, r.enrollment_count] for r in rows]

    columns = [
        {"label": _("Academic Year"), "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 200},
        {"label": _("Enrollment Count"), "fieldname": "enrollment_count", "fieldtype": "Int", "width": 150},
    ]

    chart = {
        "data": {
            "labels": [r.academic_year for r in rows],
            "datasets": [
                {
                    "name": _("Enrollment Count"),
                    "values": [r.enrollment_count for r in rows]
                }
            ]
        },
        "type": "line",
        "colors": ["#5e64ff"]
    }

    return columns, data, None, chart

