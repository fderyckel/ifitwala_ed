# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

MANDATORY_FILTERS = ("school", "academic_year", "from_date", "to_date")


def execute(filters=None):
    filters = frappe._dict(filters or {})

    # ------------------------------------------------------------------ #
    # 1. Validate & collect parameters                                    #
    # ------------------------------------------------------------------ #
    missing = [f for f in MANDATORY_FILTERS if not filters.get(f)]
    if missing:
        frappe.throw(f"Missing required filters: {', '.join(missing)}")

    params, where = {}, []

    params.update(
        {
            "from_date": getdate(filters.get("from_date")),
            "to_date": getdate(filters.get("to_date")),
        }
    )

    def add(cond, key=None):
        if key is not None and filters.get(key) is None:
            return
        where.append(cond)
        if key is not None:
            params[key] = filters.get(key)

    add("sa.school = %(school)s", "school")
    add("sa.academic_year = %(academic_year)s", "academic_year")
    add("sa.term = %(term)s", "term")
    add("sa.program = %(program)s", "program")
    add("sa.student_group = %(student_group)s", "student_group")
    if filters.get("whole_day"):
        where.append("sa.course IS NULL")
    else:
        add("sa.course = %(course)s", "course")
        where.append("sa.course IS NOT NULL")
    add("sa.instructor = %(instructor)s", "instructor")
    add("sa.student = %(student)s", "student")
    add("sa.attendance_date BETWEEN %(from_date)s AND %(to_date)s")

    condition_sql = " AND ".join(where)

    # ------------------------------------------------------------------ #
    # 2.  Get the attendance-code catalogue shown in reports              #
    # ------------------------------------------------------------------ #
    codes = frappe.get_all(
        "Student Attendance Code",
        filters={"show_in_reports": 1},
        fields=["name", "attendance_code", "count_as_present", "display_order"],
        order_by="display_order asc",
    )
    if not codes:
        frappe.throw(_("No Attendance Codes are flagged with 'Show in Reports'."))

    code_list = [c.attendance_code for c in codes]
    present_codes = [c.attendance_code for c in codes if c.count_as_present]

    # ------------------------------------------------------------------ #
    # 3. Build SQL (JOIN + conditional aggregates)                       #
    # ------------------------------------------------------------------ #
    code_columns_sql = ",\n".join(
        [
            f"SUM(CASE WHEN sac.attendance_code = {frappe.db.escape(code)} THEN 1 ELSE 0 END) AS `{code}`"
            for code in code_list
        ]
    )

    present_sum_sql = (
        " + ".join(
            [
                f"SUM(CASE WHEN sac.attendance_code = {frappe.db.escape(code)} THEN 1 ELSE 0 END)"
                for code in present_codes
            ]
        )
        or "0"
    )

    total_sum_sql = (
        " + ".join(
            [f"SUM(CASE WHEN sac.attendance_code = {frappe.db.escape(code)} THEN 1 ELSE 0 END)" for code in code_list]
        )
        or "1"
    )

    pct_sql = f"COALESCE(ROUND(({present_sum_sql}) / NULLIF(({total_sum_sql}), 0) * 100, 2), 0)"

    query = f"""
		SELECT
			sa.student                                          AS student,
			CONCAT(st.student_full_name, IF(st.student_preferred_name!='', CONCAT(' (',st.student_preferred_name,')'), '')) AS student_label,
			IF(sa.course IS NULL,'Whole Day','Course')          AS attendance_type,
			sa.course                                           AS course,
			sa.student_group                                    AS student_group,
			{code_columns_sql},
			{present_sum_sql} AS present_count_debug,
			{total_sum_sql} AS total_count_debug,
			{pct_sql} AS percentage_present
		FROM `tabStudent Attendance`        sa
		JOIN `tabStudent Attendance Code`   sac  ON sac.name  = sa.attendance_code
		JOIN `tabStudent`                   st   ON st.name   = sa.student
		WHERE {condition_sql}
		GROUP BY sa.student, student_label, attendance_type, sa.course, sa.student_group
		ORDER BY student_label, sa.course;
	"""
    data = frappe.db.sql(query, params, as_dict=True)

    # ------------------------------------------------------------------ #
    # 4.  Column definitions (dynamic)                                    #
    # ------------------------------------------------------------------ #
    columns = (
        [
            {"fieldname": "student_label", "label": "Student (Preferred)", "fieldtype": "Data", "width": 200},
            {"fieldname": "attendance_type", "label": "Type", "fieldtype": "Data", "width": 70},
            {"fieldname": "course", "label": "Course", "fieldtype": "Link", "options": "Course", "width": 120},
            {
                "fieldname": "student_group",
                "label": "Student Group",
                "fieldtype": "Link",
                "options": "Student Group",
                "width": 140,
            },
        ]
        + [{"fieldname": code, "label": code, "fieldtype": "Int", "width": 80} for code in code_list]
        + [
            {"fieldname": "present_count_debug", "label": "Total Present", "fieldtype": "Int", "width": 100},
            {"fieldname": "total_count_debug", "label": "Total Att.", "fieldtype": "Int", "width": 100},
            {"fieldname": "percentage_present", "label": "% Present", "fieldtype": "Percent", "width": 80},
        ]
    )

    return columns, data
