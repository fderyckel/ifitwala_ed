# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/page/student_group_cards/student_group_cards.py

import os
import frappe
from ifitwala_ed.utilities.image_utils import slugify


def _authorized_for_group(student_group: str, user: str) -> bool:
	"""User can see SSG badge on this page if:
	- Counselor / Academic Admin / System Manager, OR
	- user is an instructor (user_id) on the given Student Group.
	"""
	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))
	if {"Counselor", "Academic Admin", "System Manager"} & roles:
		return True

	instructor_users = set(frappe.get_all(
		"Student Group Instructor",
		filters={"parent": student_group},
		pluck="user_id"
	))
	return user in instructor_users


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

	# Viewer authorization (gate SSG lookups if not authorized)
	user = frappe.session.user
	is_authorized = _authorized_for_group(student_group, user)

	ssg_by_student = {}
	ack_pending_set = set()

	if is_authorized:
		# Resolve AY once (user default → system default)
		ay = frappe.defaults.get_user_default("academic_year") or frappe.db.get_default("academic_year")

		if ay:
			ssgs = frappe.get_all(
				"Student Support Guidance",
				filters={"student": ["in", student_ids], "academic_year": ay},
				fields=["name", "student"],
				limit=None,
			)
			ssg_by_student = {r.student: r.name for r in (ssgs or [])}

			# Open acknowledgements for current user across these SSGs (batched)
			ssg_names = [r.name for r in (ssgs or [])]
			if ssg_names:
				open_refs = frappe.get_all(
					"ToDo",
					filters={
						"reference_type": "Student Support Guidance",
						"reference_name": ["in", ssg_names],
						"allocated_to": user,
						"status": "Open",
					},
					pluck="reference_name",
				)
				ack_pending_set = set(open_refs or [])

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

		# Only expose SSG link/ack flag to authorized viewers
		ssg_name = ssg_by_student.get(sid) if is_authorized else None
		ack_pending = bool(ssg_name and ssg_name in ack_pending_set) if is_authorized else False

		out.append({
			"student": sid,
			"student_name": info.get("student_full_name", fallback_name),
			"preferred_name": info.get("student_preferred_name", ""),
			"student_image": img or "/assets/ifitwala_ed/images/default_student_image.png",
			"medical_info": info.get("medical_info", ""),
			"birth_date": info.get("student_date_of_birth"),
			"ssg_name": ssg_name,
			"ack_pending": ack_pending,
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
