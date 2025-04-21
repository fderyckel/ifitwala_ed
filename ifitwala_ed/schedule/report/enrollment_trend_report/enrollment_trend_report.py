# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict

def execute(filters=None):
    filters = filters or {}
    school_filter = filters.get("school")

    # Step 1: Query
    rows = frappe.db.sql("""
        SELECT
            pe.academic_year,
            pe.school,
            pe.program,
            COUNT(pe.name) as enrollment_count
        FROM `tabProgram Enrollment` pe
        LEFT JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
        {where_clause}
        GROUP BY pe.academic_year, {group_by}
        ORDER BY MIN(ay.year_start_date), {group_by}
    """.format(
        where_clause=f"WHERE pe.school = %(school)s" if school_filter else "",
        group_by="pe.program" if school_filter else "pe.school"
    ), filters, as_dict=True)

    # Step 2: Collect academic years in chronological order
    academic_years = sorted({r.academic_year for r in rows}, key=lambda y: frappe.db.get_value("Academic Year", y, "year_start_date"))

    # Step 3: Pivot map
    group_map = defaultdict(lambda: defaultdict(int))
    for r in rows:
        key = r.program if school_filter else r.school
        group_map[key][r.academic_year] = r.enrollment_count

    # Step 4: Chart datasets
    datasets = []
    for key, year_counts in group_map.items():
        datasets.append({
            "name": key,
            "values": [year_counts.get(y, 0) for y in academic_years]
        })

    # Step 5: Table Columns
    columns = [
        {"label": _("Academic Year"), "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 180}
    ]

    if school_filter:
        columns.append({"label": _("Program"), "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 200})
    else:
        columns.append({"label": _("School"), "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 200})

    columns.append({"label": _("Enrollment Count"), "fieldname": "enrollment_count", "fieldtype": "Int", "width": 120})

    # Step 6: Table rows
    data = []
    for r in rows:
        row = [r.academic_year]
        row.append(r.program if school_filter else r.school)
        row.append(r.enrollment_count)
        data.append(row)

    # Step 7: Chart
    chart = {
        "data": {
            "labels": academic_years,
            "datasets": datasets
        },
        "type": "line",
        "colors": ["#5e64ff", "#ff9f43", "#7cd6fd", "#28a745", "#ffa3ef", "#ff5858", "#6c5ce7"]
    }

    return columns, data, None, chart

