# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/page/student_group_cards/student_group_cards.py

import os
import frappe
from ifitwala_ed.utilities.image_utils import slugify


def _authorized_for_group(student_group: str, user: str) -> bool:
	"""Allow:
	- Counselor / Counsellor / Counselors / Academic Admin / System Manager / Administrator
	- OR user is an instructor on the SG via either child.user_id or linked Instructor record
	- OR (optional) employee mapping if your child table stores employee
	"""
	if not user:
		return False
	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))
	triage_roles = {"Counselor", "Academic Admin"}
	if roles & triage_roles:
		return True

	# direct user_id on child
	if frappe.db.exists("Student Group Instructor", {"parent": student_group, "user_id": user}):
		return True

	# via linked Instructor(s)
	ins_ids = frappe.get_all("Instructor", filters={"linked_user_id": user}, pluck="name")
	if ins_ids and frappe.db.exists("Student Group Instructor", {"parent": student_group, "instructor": ["in", ins_ids]}):
		return True

	# optional: via Employee mapping if you store it on child
	emp_id = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	if emp_id and frappe.db.exists("Student Group Instructor", {"parent": student_group, "employee": emp_id}):
		return True

	return False



def get_student_group_students(student_group, start=0, page_length=25):
	# Base roster slice
	student_rows = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group},
		fields=["student", "student_name"],
		start=start,
		page_length=page_length,
		as_list=True,
	)
	if not student_rows:
		return []

	student_ids = [s[0] for s in student_rows]

	# Student core fields (single batched fetch)
	student_details = frappe.db.get_values(
		"Student",
		{"name": ("in", student_ids)},
		["name", "student_full_name", "student_preferred_name", "student_image", "student_date_of_birth"],
		as_dict=True,
	)
	by_id = {s["name"]: s for s in (student_details or [])}

	# Optional health note (batched)
	health_rows = frappe.db.get_values(
		"Student Patient",
		{"student": ["in", student_ids]},
		["student", "medical_info"],
		as_dict=True,
	)
	for r in (health_rows or []):
		if r.medical_info:
			by_id.setdefault(r.student, {})["medical_info"] = r.medical_info

	# Viewer authorization (gate support-guidance lookups if not authorized)
	user = frappe.session.user
	is_authorized = _authorized_for_group(student_group, user)

	# Compute has_ssg per student with ONE batched SQL (only if authorized)
	students_with_ssg = set()
	if is_authorized and student_ids:
		rows = frappe.db.sql(
			"""
			SELECT rc.student
			FROM `tabReferral Case` rc
			JOIN `tabReferral Case Entry` e ON e.parent = rc.name
			WHERE rc.student IN %(students)s
			  AND IFNULL(rc.case_status, 'Open') != 'Closed'
			  AND e.entry_type = 'Student Support Guidance'
			  AND IFNULL(e.is_published, 0) = 1
			  AND IFNULL(e.status, 'Open') IN ('Open','In Progress')
			GROUP BY rc.student
			""",
			{"students": tuple(student_ids)},
		) or []
		students_with_ssg = {r[0] for r in rows if r and r[0]}

	# Thumbnails base dir (exists check once)
	thumb_dir = frappe.get_site_path("public", "files", "gallery_resized", "student")
	thumb_dir_exists = os.path.isdir(thumb_dir)

	# Build response
	out = []
	for sid, fallback_name in student_rows:
		info = by_id.get(sid, {})
		img = info.get("student_image") or ""

		# Prefer pre-rendered thumbnail if available
		if img and img.startswith("/files/student/") and thumb_dir_exists:
			filename = img.rsplit("/", 1)[-1]
			name = slugify(filename)
			thumb_filename = f"thumb_{name}.webp"
			if os.path.exists(os.path.join(thumb_dir, thumb_filename)):
				img = f"/files/gallery_resized/student/{thumb_filename}"

		# Support-guidance flag exposed only to authorized viewers
		has_ssg = bool(sid in students_with_ssg) if is_authorized else False

		out.append({
			"student": sid,
			"student_name": info.get("student_full_name", fallback_name),
			"preferred_name": info.get("student_preferred_name", ""),
			"student_image": img or "/assets/ifitwala_ed/images/default_student_image.png",
			"medical_info": info.get("medical_info", ""),
			"birth_date": info.get("student_date_of_birth"),
			"has_ssg": has_ssg,
		})

	return out


@frappe.whitelist()
def fetch_student_groups(program=None, course=None, cohort=None):
	filters = {}
	if program:
		filters["program"] = program
	if course:
		filters["course"] = course
	if cohort:
		filters["cohort"] = cohort
	return frappe.get_all("Student Group", filters=filters, fields=["name", "student_group_name"])


@frappe.whitelist()
def fetch_students(student_group, start=0, page_length=25):
	students = get_student_group_students(student_group, start, page_length)
	total = frappe.db.count("Student Group Student", {"parent": student_group})

	group = frappe.get_doc("Student Group", student_group)
	group_info = {"name": group.name, "program": group.program, "course": group.course, "cohort": group.cohort}

	return {"students": students, "start": start + page_length, "total": total, "group_info": group_info}


@frappe.whitelist()
def reset_student_fetch(student_group):
	return {
		"students": get_student_group_students(student_group, start=0, page_length=25),
		"start": 25,
		"total": frappe.db.count("Student Group Student", {"parent": student_group}),
	}
