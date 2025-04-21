# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict

import frappe
from frappe import _
from collections import defaultdict

def execute(filters=None):
    filters = filters or {}
    school_filter = filters.get("school")

    # 🎯 CASE 1: No school selected → One line per school
    if not school_filter:
        rows = frappe.db.sql("""
            SELECT
                pe.academic_year,
                pe.school,
                COUNT(pe.name) as enrollment_count
            FROM `tabProgram Enrollment` pe
            LEFT JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
            GROUP BY pe.academic_year, pe.school
            ORDER BY MIN(ay.year_start_date), pe.school
        """, as_dict=True)

        group_key = "school"
    else:
        # 🎯 CASE 2: School selected → One line per program in that school
        rows = frappe.db.sql("""
            SELECT
                pe.academic_year,
                pe.program,
                COUNT(pe.name) as enrollment_count
            FROM `tabProgram Enrollment` pe
            LEFT JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
            WHERE pe.school = %(school)s
            GROUP BY pe.academic_year, pe.program
            ORDER BY MIN(ay.year_start_date), pe.program
        """, filters, as_dict=True)

        group_key = "program"

    # Return empty safely
    if not rows:
        return [], [], None, {}

    # 🔁 Academic years sorted chronologically
    academic_years = sorted({r.academic_year for r in rows}, key=lambda y: frappe.db.get_value("Academic Year", y, "year_start_date"))

    # 🧠 Pivot map
    group_map = defaultdict(lambda: defaultdict(int))
    for r in rows:
        group_map[r[group_key]][r.academic_year] += r.enrollment_count

    # 📊 Datasets
    datasets = []
    for key, year_counts in group_map.items():
        datasets.append({
            "name": key,
            "values": [year_counts.get(y, 0) for y in academic_years]
        })

    # 📄 Columns
    columns = [
        {"label": _("Academic Year"), "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 180},
        {
            "label": _("Program") if school_filter else _("School"),
            "fieldname": group_key,
            "fieldtype": "Link",
            "options": "Program" if school_filter else "School",
            "width": 200
        },
        {"label": _("Enrollment Count"), "fieldname": "enrollment_count", "fieldtype": "Int", "width": 120}
    ]

    # 📋 Data
    data = []
    for r in rows:
        row = [r.academic_year, r[group_key], r.enrollment_count]
        data.append(row)

    # 📈 Chart
    chart = {
        "data": {
            "labels": academic_years,
            "datasets": datasets
        },
        "type": "line",
        "colors": ["#5e64ff", "#ff9f43", "#7cd6fd", "#28a745", "#ffa3ef", "#ff5858", "#6c5ce7"]
    }

    return columns, data, None, chart
