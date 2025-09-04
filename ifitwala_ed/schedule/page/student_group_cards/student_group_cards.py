# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import re
import os
from ifitwala_ed.utilities.image_utils import slugify

# ifitwala_ed/schedule/page/student_group_cards/student_group_cards.py

import frappe
import re
import os
from ifitwala_ed.utilities.image_utils import slugify

def get_student_group_students(student_group, start=0, page_length=25):
	student_data = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name"],
		start=start,
		page_length=page_length,
		as_list=True
	)

	student_ids = [s[0] for s in student_data]
	if not student_ids:
		return []

	student_details = frappe.db.get_values(
		"Student",
		{"name": ("in", student_ids)},
		["name", "student_full_name", "student_preferred_name", "student_image", "student_date_of_birth"],
		as_dict=True
	)
	student_dict = {s["name"]: s for s in student_details}

	# optional health note
	medical_info_data = frappe.db.get_values(
		"Student Patient",
		{"student": ["in", student_ids]},
		["student", "medical_info"],
		as_dict=True
	)
	for entry in medical_info_data:
		if entry.medical_info:
			student_dict[entry.student]["medical_info"] = entry.medical_info

	# resolve default academic year (user default → system default)
	ay = frappe.defaults.get_user_default("academic_year") or frappe.db.get_default("academic_year")

	# bulk fetch SSG for these students in this AY
	ssg_by_student = {}
	ack_pending_set = set()
	if ay:
		ssgs = frappe.get_all(
			"Student Support Guidance",
			filters={"student": ["in", student_ids], "academic_year": ay},
			fields=["name", "student"],
			limit=None
		)
		ssg_by_student = {r.student: r.name for r in ssgs}

		# bulk fetch open ToDos for the current user on those SSGs
		ssg_names = [r.name for r in ssgs] if ssgs else []
		if ssg_names:
			open_refs = frappe.get_all(
				"ToDo",
				filters={
					"reference_type": "Student Support Guidance",
					"reference_name": ["in", ssg_names],
					"allocated_to": frappe.session.user,
					"status": "Open",
				},
				pluck="reference_name"
			)
			ack_pending_set = set(open_refs or [])

	# thumbnail dir
	thumb_dir = frappe.get_site_path("public", "files", "gallery_resized", "student")

	# build final payload
	students = []
	for student_id, student_name in student_data:
		info = student_dict.get(student_id, {})
		orig_url = info.get("student_image", "") or ""

		if orig_url and orig_url.startswith("/files/student/") and os.path.isdir(thumb_dir):
			filename = orig_url.rsplit("/", 1)[-1]
			name, ext = os.path.splitext(filename)
			name = slugify(filename)
			thumb_filename = f"thumb_{name}.webp"
			thumb_path = os.path.join(thumb_dir, thumb_filename)
			if os.path.exists(thumb_path):
				orig_url = f"/files/gallery_resized/student/{thumb_filename}"

		ssg_name = ssg_by_student.get(student_id)
		ack_pending = bool(ssg_name and ssg_name in ack_pending_set)

		students.append({
			"student": student_id,
			"student_name": info.get("student_full_name", student_name),
			"preferred_name": info.get("student_preferred_name", ""),
			"student_image": orig_url or "/assets/ifitwala_ed/images/default_student_image.png",
			"medical_info": info.get("medical_info", ""),
			"birth_date": info.get("student_date_of_birth"),
			"ssg_name": ssg_name,
			"ack_pending": ack_pending,
		})

	return students


@frappe.whitelist()
def fetch_student_groups(program=None, course=None, cohort=None):
    filters = {}
    if program:
        filters["program"] = program
    if course:
        filters["course"] = course
    if cohort:
        filters["cohort"] = cohort

    student_groups = frappe.get_all("Student Group", filters=filters, fields=["name", "student_group_name"])
    return student_groups

@frappe.whitelist()
def fetch_students(student_group, start=0, page_length=25):
    students = get_student_group_students(student_group, start, page_length)
    total_students = frappe.db.count("Student Group Student", {"parent": student_group})
    group_doc = frappe.get_doc("Student Group", student_group)
    group_info = {
        "name": group_doc.name,
        "program": group_doc.program,
        "course": group_doc.course,
        "cohort": group_doc.cohort
    }
    return {
        "students": students,
        "start": start + page_length,
        "total": total_students,
        "group_info": group_info
    }

@frappe.whitelist()
def reset_student_fetch(student_group):
    return {
        "students": get_student_group_students(student_group, start=0, page_length=25), 
        "start": 25, 
        "total": frappe.db.count("Student Group Student", {"parent": student_group})
    }
