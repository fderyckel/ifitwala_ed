# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import unicode_literals, division
import frappe
from frappe import _
from frappe.utils import getdate, today

class OverlapError(frappe.ValidationError): pass

def validate_overlap_for(doc, doctype, fieldname, value=None):
	"""Checks overlap for specified field.
	:param fieldname: Checks Overlap for this field
	"""

	existing = get_overlap_for(doc, doctype, fieldname, value)
	if existing:
		frappe.throw(_("This {0} conflicts with {1} for {2} {3}").format(doc.doctype, existing.name,
			doc.meta.get_label(fieldname) if not value else fieldname , value or doc.get(fieldname)), OverlapError)

def get_overlap_for(doc, doctype, fieldname, value=None):
	"""Returns overlaping document for specified field.
	:param fieldname: Checks Overlap for this field
	"""

	existing = frappe.db.sql("""select name, from_time, to_time from `tab{0}`
		where `{1}`=%(val)s and schedule_date = %(schedule_date)s and
		(
			(from_time > %(from_time)s and from_time < %(to_time)s) or
			(to_time > %(from_time)s and to_time < %(to_time)s) or
			(%(from_time)s > from_time and %(from_time)s < to_time) or
			(%(from_time)s = from_time and %(to_time)s = to_time))
		and name!=%(name)s and docstatus!=2""".format(doctype, fieldname),
		{
			"schedule_date": doc.schedule_date,
			"val": value or doc.get(fieldname),
			"from_time": doc.from_time,
			"to_time": doc.to_time,
			"name": doc.name or "No Name"
		}, as_dict=True)

	return existing[0] if existing else None

def validate_duplicate_student(students):
	unique_students = []
	for stud in students:
		if stud.student in unique_students:
			frappe.throw(_("Student {0} - {1} appears Multiple times in row {2} & {3}")
				.format(stud.student, stud.student_name, unique_students.index(stud.student)+1, stud.idx))
		else:
			unique_students.append(stud.student)

	return None

## For the student portal - course page. 
def get_current_courses():
    """
    Returns a list of courses the current logged-in student is enrolled in.
    Each course record is merged with details from the Course doctype.
    Optimized to use frappe.db.get_values() for better performance.
    """
    # Validate the user
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this page."), frappe.PermissionError)
    
    # Fetch the student record using the session email
    student = frappe.db.get_value("Student", {"student_email": frappe.session.user}, "name")
    if not student:
        frappe.throw(_("Student profile not found. Please contact the administrator."))
    
    # Fetch current course enrollments for the student using get_values
    enrollments = frappe.db.get_values(
        "Course Enrollment",
        filters={"student": student, "current": 1},
        fieldname=["name", "course"],
        as_dict=True
    )
    
    if not enrollments:
        return []  # Return empty list if no enrollments found

    # Efficiently fetch Course details including course_group and course_image
    course_ids = [enrollment.get("course") for enrollment in enrollments]
    courses = frappe.db.get_values(
        "Course",
        filters={"name": ["in", course_ids]},
        fieldname=["name", "course_name", "course_group", "course_image"],
        as_dict=True
    )
    
    # Map Course details by course id for fast lookup
    course_map = {course["name"]: course for course in courses}
    
    # Merge enrollment and course data
    current_courses = []
    for enrollment in enrollments:
        course_detail = course_map.get(enrollment["course"], {})
        course_info = {
            "enrollment_id": enrollment["name"],
            "course": enrollment["course"],
            "course_name": course_detail.get("course_name") or enrollment["course"],
            "course_group": course_detail.get("course_group"),
            "course_image": course_detail.get("course_image")
        }
        current_courses.append(course_info)
    
    return current_courses

