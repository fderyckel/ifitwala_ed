# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

@frappe.whitelist()
def get_student_groups(program=None, course=None, instructor=None, text=""):
    """
    Return a list of Student Groups that match the given filters (program, course, instructor)
    and contain 'text' in their name (for autocomplete).
    We only want the groups for which there's at least one Instructor match (if instructor given).
    """

    # Build conditions
    conditions = ["sg.status = 'Active'"]  # only active groups
    values = {}

    # Program filter
    if program:
        conditions.append("sg.program = %(program)s")
        values["program"] = program

    # Course filter
    if course:
        conditions.append("sg.course = %(course)s")
        values["course"] = course

    # If we filter by instructor, we need to check the child table "Student Group Instructor"
    # to see if that instructor is part of the group.
    instructor_join = ""
    if instructor:
        instructor_join = """
            INNER JOIN `tabStudent Group Instructor` sgi
                ON sgi.parent = sg.name
                AND sgi.instructor = %(instructor)s
        """
        values["instructor"] = instructor

    # If text is provided, match it against the student_group_name or name (wildcard search).
    if text:
        conditions.append("(sg.student_group_name LIKE %(text)s OR sg.name LIKE %(text)s)")
        values["text"] = f"%{text}%"

    where_clause = " AND ".join(conditions)

    # Query
    data = frappe.db.sql(f"""
        SELECT
            sg.name,
            sg.student_group_name
        FROM `tabStudent Group` sg
        {instructor_join}
        WHERE {where_clause}
        ORDER BY sg.student_group_name ASC
        LIMIT 50
    """, values=values, as_dict=True)

    return data


@frappe.whitelist()
def get_students_in_group(student_group):
    """
    Return a list of active students in the given Student Group.
    We only want child rows with active=1 and the linked Student doc is also enabled=1.
    We'll fetch student_image, student_full_name, and student_preferred_name.
    """
    if not student_group:
        return []

    # Query the child table and join the Student doc
    # to get the student's image, full name, etc.
    students = frappe.db.sql("""
        SELECT
            s.student_image AS student_image,
            s.student_full_name AS student_full_name,
            s.student_preferred_name AS student_preferred_name
        FROM `tabStudent Group Student` sgs
        INNER JOIN `tabStudent` s
            ON sgs.student = s.name
        WHERE
            sgs.parent = %(student_group)s
            AND sgs.active = 1
            AND s.enabled = 1
        ORDER BY s.student_full_name
        LIMIT 25
    """, {"student_group": student_group}, as_dict=True)

    return students
