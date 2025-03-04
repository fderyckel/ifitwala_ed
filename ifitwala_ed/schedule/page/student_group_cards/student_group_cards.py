# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint

@frappe.whitelist()
def get_student_groups_query(doctype, txt, searchfield, start, page_len, filters):
    """
    This method is called by the link field for Student Group.
    'filters' will have { "program": ..., "course": ..., "instructor": ... }.
    We only return 'Active' groups that match those filters.
    We also match 'txt' against name or student_group_name.
    The return format is a list of [name, label, ...].
    """

    program = filters.get("program")
    course = filters.get("course")
    instructor = filters.get("instructor")

    start = cint(start)
    page_len = cint(page_len)

    conditions = ["sg.status = 'Active'"]
    vals = {}

    if program:
        conditions.append("sg.program = %(program)s")
        vals["program"] = program

    if course:
        conditions.append("sg.course = %(course)s")
        vals["course"] = course

    instructor_join = ""
    if instructor:
        instructor_join = """
            INNER JOIN `tabStudent Group Instructor` sgi
                ON sgi.parent = sg.name
                AND sgi.instructor = %(instructor)s
        """
        vals["instructor"] = instructor

    if txt:
        conditions.append("(sg.name LIKE %(txt)s OR sg.student_group_name LIKE %(txt)s)")
        vals["txt"] = f"%{txt}%"

    where_clause = " AND ".join(conditions)

    data = frappe.db.sql(f"""
        SELECT
            sg.name, sg.student_group_name
        FROM `tabStudent Group` sg
        {instructor_join}
        WHERE {where_clause}
        ORDER BY sg.student_group_name ASC
        LIMIT {start}, {page_len}
    """, vals)

    # For a link query, we typically return a list of tuples [ [name, label], ... ]
    # "label" is what the user sees in the search dropdown.
    # data might look like [(SG-0001, "Grade 10 - Math"), (SG-0002, "Grade 11 - History"), ...]
    # We'll transform it so that name=SG-0001, label=Grade 10 - Math
    return [[d[0], d[1]] for d in data]


@frappe.whitelist()
def get_students_in_group(student_group):
    """
    Return a list of up to 25 active students in the given Student Group.
    (sgs.active=1, s.enabled=1).
    We'll fetch student_image, student_full_name, student_preferred_name.
    """

    if not student_group:
        return []

    students = frappe.db.sql("""
        SELECT
            s.student_image AS student_image,
            s.student_full_name AS student_full_name,
            s.student_preferred_name AS student_preferred_name
        FROM `tabStudent Group Student` sgs
        INNER JOIN `tabStudent` s
            ON sgs.student = s.name
        WHERE
            sgs.parent = %(group)s
            AND sgs.active = 1
            AND s.enabled = 1
        ORDER BY s.student_full_name
        LIMIT 25
    """, {"group": student_group}, as_dict=True)

    return students
