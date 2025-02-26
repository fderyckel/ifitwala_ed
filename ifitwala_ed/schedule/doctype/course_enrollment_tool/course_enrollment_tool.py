# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_link_to_form, cint
from frappe.model.document import Document
from frappe.query_builder import DocType

class CourseEnrollmentTool(Document):

  @frappe.whitelist()
  def add_course_to_program_enrollment(self): 
    if self.program:
      # Check if the chosen course is part of the Program
      program_doc = frappe.get_doc("Program", self.program)
      valid_courses = {pc.course for pc in program_doc.courses}
      if self.course not in valid_courses:
        frappe.throw(_("{course} is not part of {program}. Please correct your selection."
          ).format(get_link_to_form("Course", self.course), get_link_to_form("Program", self.program)))

    for row in self.students: 
      if not row.program_enrollment:
        # If no Program Enrollment is linked in the child row, skip or handle differently
        continue

      pe_doc = frappe.get_doc("Program Enrollment", row.program_enrollment)
      # Check if course is already in this Program Enrollment
      already_exists = any(c.course == self.course for c in pe_doc.get("courses", []))
      if already_exists: 
        frappe.msgprint(_("Course {course} already exists in Program Enrollment {pe}."
          ).format(get_link_to_form("Course", self.course),get_link_to_form("Program Enrollment", pe_doc.name)))
      else:
        # Append the course to Program Enrollment child table
        pe_doc.append("courses", {"course": self.course})
        pe_doc.save()  # Save (not submit)
        frappe.msgprint(_( "Course {course} successfully added to Program Enrollment {pe}."
          ).format(get_link_to_form("Course", self.course, label=self.course), get_link_to_form("Program Enrollment", pe_doc.name)))

    # Finally, save the Course Enrollment Tool doc if anything changed
    self.save()
    frappe.msgprint(_("Done updating Program Enrollments."))


@frappe.whitelist()
def fetch_eligible_students(doctype, txt, searchfield, start, page_len, filters=None):
    """
    This method is designed for Link field queries in Frappe.

    Args:
        doctype (str): The DocType we are linking to (likely "Student").
        txt (str): The partial text typed by the user to filter.
        searchfield (str): Usually "name" or the field being searched in the link.
        start (int): For pagination, the starting row.
        page_len (int): Number of rows to return in one go.
        filters (dict): Additional filters from set_query().

    Returns:
        list: Each element is [value, label] for the Link field search results.
    """
    # 1) Convert start/page_len to integers
    start = cint(start)
    page_len = cint(page_len)	

    if not filters:
        filters = {}

    # 2) Extract custom filters
    academic_year = filters.get("academic_year")
    program = filters.get("program")
    term = filters.get("term")
    course = filters.get("course")

    if not academic_year:
      frappe.throw(_("Academic Year is required to fetch students."))
    if not course:
      frappe.throw(_("Course is required to fetch students."))	
      
    # 3) Build conditions and parameter list
    conditions = ["s.student_status = 'Active'", "pe.docstatus = 0"]
    values = []

    # Filter by academic_year if provided
    if academic_year:
        conditions.append("pe.academic_year = %s")
        values.append(academic_year)

    # Filter by program if provided
    if program:
        conditions.append("pe.program = %s")
        values.append(program)

    # Filter by term if provided
    if term:
        conditions.append("pe.term = %s")
        values.append(term)

    # Filter by course if provided
    # i.e. only programs that have this course in their Program Course child table
    if course:
        conditions.append("pc.course = %s")
        values.append(course)

    # Filter by txt, matching either student ID or student_name
    if txt:
        conditions.append("(s.name LIKE %s OR s.student_full_name LIKE %s)")
        values.append(f"%{txt}%")
        values.append(f"%{txt}%")

    where_clause = " AND ".join(conditions)

    # 4) Run a single SQL query with JOINs
    #    DISTINCT ensures we don't get duplicates if multiple PEs match for the same student
    results = frappe.db.sql(f"""
        SELECT DISTINCT s.name, s.student_full_name
        FROM `tabStudent` s
        JOIN `tabProgram Enrollment` pe ON pe.student = s.name
        JOIN `tabProgram` pr ON pr.name = pe.program
        JOIN `tabProgram Course` pc ON pc.parent = pr.name
        WHERE {where_clause}
        ORDER BY s.name
        LIMIT {start}, {page_len}
    """, values, as_dict=True)

    # 5) Transform results into the format [[value, label], ...]
    final = []
    for row in results:
        student_id = row["name"]
        student_label = row["student_name"] or ""
        # The label is displayed in the dropdown, so let's do: "STUD0001 - John Smith"
        label = f"{student_id} - {student_label}".strip(" -")
        final.append([student_id, label])

    return final



@frappe.whitelist()
def get_courses_for_program(doctype, txt, searchfield, start, page_len, filters=None):
    """
    Return a list of [value, label] for the "course" Link field,
    showing only courses that are in Program's child table "Program Course".
    
    - doctype: "Course" (the link doctype)
    - txt: user-typed text for partial matching
    - searchfield, start, page_len: for pagination
    - filters: dict with {'program': <program_name>}
    
    Steps:
      1) Check if 'program' is in filters.
      2) Query 'Program Course' joined to 'Course' if needed.
      3) Return [[course_name, "COURSE123 - Some Course Title"], ...].
    """

    start = cint(start)
    page_len = cint(page_len)

    if not filters:
        filters = {}

    program = filters.get("program")
    if not program:
        # No program chosen => No results or you might show all courses
        return []

    # We'll match partial text on the Course name or Course's course_name
    conditions = ["pc.parent = %s"]
    values = [program]

    if txt:
        conditions.append("(c.name LIKE %s OR c.course_name LIKE %s)")
        values.append(f"%{txt}%")
        values.append(f"%{txt}%")

    where_clause = " AND ".join(conditions)

    results = frappe.db.sql(f"""
        SELECT c.name, c.course_name
        FROM `tabProgram Course` pc
        JOIN `tabCourse` c ON c.name = pc.course
        WHERE {where_clause}
        ORDER BY c.name
        LIMIT {start}, {page_len}
    """, values, as_dict=True)

    final = []
    for row in results:
        course_id = row["name"]
        course_label = row["course_name"] or ""
        label = f"{course_id} - {course_label}".strip(" -")
        final.append([course_id, label])

    return final