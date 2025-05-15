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

# This utility function is used to fetch the current courses for a student on the portal.
def get_current_courses():
    """
    Optimized version: Fetch enrolled courses for the logged-in student
    using direct SQL joins. Avoids multiple roundtrips and ORM overhead.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this page."), frappe.PermissionError)

    student = frappe.db.get_value("Student", {"student_email": frappe.session.user}, "name")
    if not student:
        frappe.throw(_("Student profile not found. Please contact the administrator."))

    query = """
        SELECT
            pec.name AS enrollment_id,
            pec.course AS course,
            c.course_name,
            c.course_group,
            c.course_image
        FROM `tabProgram Enrollment Course` pec
        INNER JOIN `tabProgram Enrollment` pe ON pe.name = pec.parent
        INNER JOIN `tabCourse` c ON c.name = pec.course
        WHERE pe.student = %s
          AND pe.status = 1
          AND pec.status = 'Enrolled'
    """
    results = frappe.db.sql(query, (student,), as_dict=True)
    return results
