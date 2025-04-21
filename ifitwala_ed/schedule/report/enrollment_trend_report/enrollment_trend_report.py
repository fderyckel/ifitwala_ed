# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict

def execute(filters=None):
    filters = filters or {}
    school_filter = filters.get("school")

    # Step 1: Query data
    rows = frappe.db.sql("""
        SELECT
            pe.academic_year,
            pe.school,
            COUNT(pe.name) as enrollment_count
        FROM `tabProgram Enrollment` pe
        LEFT JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
        {where_clause}
        GROUP BY pe.academic_year, pe.school
        ORDER BY MIN(ay.year_start_date), pe.school
    """.format(
        where_clause=f"WHERE pe.school = %(school)s" if school_filter else ""
    ), filters, as_dict=True)

    # Step 2: Get unique sorted academic years
    academic_years = sorted({r.academic_year for r in rows}, key=lambda y: frappe.db.get_value("Academic Year", y, "year_start_date"))
    
    # Step 3: Pivot school → { year → count }
    school_map = defaultdict(lambda: defaultdict(int))
    for r in rows:
        school_map[r.school][r.academic_year] = r.enrollment_count

    # Step 4: Build chart datasets
    datasets = []
    for school, year_counts in school_map.items():
        datasets.append({
            "name": school,
            "values": [year_counts.get(y, 0) for y in academic_years]
        })

    columns = [
        {"label": _("Academic Year"), "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 150},
        {"label": _("School"), "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 250},
        {"label": _("Enrollment Count"), "fieldname": "enrollment_count", "fieldtype": "Int", "width": 100},
    ]

    # For table output — optional (flat view, not charted)
    data = [[r.academic_year, r.school, r.enrollment_count] for r in rows]

    chart = {
        "data": {
            "labels": academic_years,
            "datasets": datasets
        },
        "type": "line",
        "colors": ["#5e64ff", "#ff9f43", "#7cd6fd", "#28a745", "#ffa3ef", "#ff5858"]
    }

    return columns, data, None, chart
