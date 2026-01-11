# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_log.py

import os
import frappe
from frappe import _
from frappe.utils import strip_html
from frappe.utils import cint, nowdate, nowtime
from frappe.utils.nestedset import get_descendants_of

LOG_DOCTYPE = "Student Log"
PAGE_LENGTH_DEFAULT = 20

def _resolve_current_student():
    """Securely map the logged-in portal user to a Student record."""
    user_id = frappe.session.user
    if user_id == "Guest":
        frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

    user_email = frappe.db.get_value("User", user_id, "email") or user_id
    student_name = frappe.db.get_value("Student", {"student_email": user_email}, "name")

    if not student_name:
        frappe.throw(_("No Student record found for your account."), frappe.PermissionError)

    return student_name

@frappe.whitelist()
def get_student_logs(start: int = 0, page_length: int = PAGE_LENGTH_DEFAULT):
	"""Fetch a paginated list of student logs visible to the current student (lean SQL)."""
	student_name = _resolve_current_student()

	# NOTE: Using raw SQL here for performance and to bypass DocType perms;
	# we enforce strict filters (student + visible_to_student) and only return minimal columns.
	rows = frappe.db.sql(
		"""
		SELECT
			l.name,
			l.date,
			l.time,
			l.log_type,
			l.author_name,
			l.follow_up_status,
			l.log,
			CASE WHEN rr.reference_name IS NULL THEN 1 ELSE 0 END AS is_unread
		FROM `tabStudent Log` l
		LEFT JOIN (
			SELECT DISTINCT reference_name
			FROM `tabPortal Read Receipt`
			WHERE user = %(user)s
			  AND reference_doctype = %(ref_dt)s
		) rr
		ON rr.reference_name = l.name
		WHERE l.student = %(student)s
		  AND l.visible_to_student = 1
		ORDER BY l.date DESC, l.time DESC, l.name DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{
			"user": frappe.session.user,
			"ref_dt": LOG_DOCTYPE,
			"student": student_name,
			"limit": int(page_length),
			"offset": int(start),
		},
		as_dict=True,
	)

	# rows already shaped for the UI
	# Build a lightweight, HTML-free preview and drop the full body from list payload
	PREVIEW_LEN = 200
	for r in rows:
		body_html = r.pop("log", "") or ""
		body_text = strip_html(body_html).strip()
		r["preview"] = (body_text[:PREVIEW_LEN] + "…") if len(body_text) > PREVIEW_LEN else body_text
	return rows


@frappe.whitelist()
def get_student_log_detail(log_name: str):
	"""Fetch a single student log (minimal fields) and mark it as read."""
	# Resolve the current student (raises if not a logged-in student)
	student_name = _resolve_current_student()

	# Fetch only what the portal needs (faster than get_doc)
	fields = [
		"name",
		"student",
		"visible_to_student",
		"date",
		"time",
		"log_type",
		"author_name",
		"log",  # the rich text / HTML body
	]
	log = frappe.db.get_value("Student Log", log_name, fields, as_dict=True)
	if not log:
		frappe.throw(_("Log not found."), frappe.DoesNotExistError)

	# Security: student must own the log and it must be visible on portal
	if log.student != student_name or not log.visible_to_student:
		frappe.throw(_("You do not have permission to view this log."), frappe.PermissionError)

	# Mark as read with a lightweight existence check
	rr_filters = {
		"user": frappe.session.user,
		"reference_doctype": "Student Log",
		"reference_name": log_name,
	}
	if not frappe.db.exists("Portal Read Receipt", rr_filters):
		try:
			frappe.get_doc({"doctype": "Portal Read Receipt", **rr_filters}).insert(ignore_permissions=True)
			# No manual commit: Frappe handles request transactions
		except Exception as e:
			# Harmless if a parallel request inserted first; log and continue
			frappe.log_error(f"Read receipt create failed for {log_name}: {e}", "Student Log API")

	return log




ALLOWED_OPTIONS_KEYS = {"student"}
ALLOWED_SEARCH_STUDENT_KEYS = {"query", "limit"}
ALLOWED_ASSIGNEE_KEYS = {"next_step", "student", "query", "limit"}
ALLOWED_SUBMIT_KEYS = {
	"student",
	"log_type",
	"log",
	"requires_follow_up",
	"next_step",
	"follow_up_person",
	"visible_to_student",
	"visible_to_guardians",
}


def _validate_keys(payload: dict, allowed: set[str]):
	if not isinstance(payload, dict):
		frappe.throw(_("Payload must be a dict."))
	unknown = set(payload.keys()) - allowed
	if unknown:
		frappe.throw(_("Unexpected keys: {0}").format(", ".join(sorted(list(unknown)))))


def _get_employee_school_for_session_user() -> str | None:
	user = frappe.session.user
	if not user or user == "Guest":
		return None
	return frappe.db.get_value("Employee", {"user_id": user}, "school")


def _get_student_school(student: str) -> str | None:
	return frappe.db.get_value("Student", student, "anchor_school")


def _get_parent_school(school: str | None) -> str | None:
	if not school:
		return None
	return frappe.db.get_value("School", school, "parent_school")


def _allowed_next_step_schools(student_school: str | None) -> list[str]:
	# Policy: student school + parent (+1). No siblings.
	if not student_school:
		return []
	parent = _get_parent_school(student_school)
	out = [student_school]
	if parent and parent != student_school:
		out.append(parent)
	return out


def _thumb_url(original_url: str | None) -> str | None:
	"""
	Return thumb_* variant url when it exists, else original.
	image_utils generates: /files/<doctype_folder>/thumb_<base>.webp
	For Student: doctype_folder = 'student'
	"""
	if not original_url:
		return None
	filename = os.path.basename(original_url)
	base, _ext = os.path.splitext(filename)

	# If already a generated variant, keep it
	if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
		return original_url

	variant = f"/files/student/thumb_{base}.webp"
	if frappe.db.get_value("File", {"file_url": variant}, "name"):
		return variant
	return original_url


@frappe.whitelist()
def get_form_options(**payload):
	_validate_keys(payload, ALLOWED_OPTIONS_KEYS)

	student = payload.get("student")
	if not student:
		frappe.throw(_("Student is required."))

	student_school = _get_student_school(student)
	allowed_schools = _allowed_next_step_schools(student_school)

	log_types = frappe.get_all(
		"Student Log Type",
		fields=["name as value", "log_type as label"],
		order_by="log_type asc",
	)

	next_steps = []
	if allowed_schools:
		next_steps = frappe.get_all(
			"Student Log Next Step",
			filters={"school": ["in", allowed_schools]},
			fields=["name as value", "next_step as label", "associated_role as role", "school"],
			order_by="next_step asc",
		)

	return {
		"log_types": log_types,
		"next_steps": next_steps,
		"student_school": student_school,
		"allowed_next_step_schools": allowed_schools,
	}

@frappe.whitelist()
def search_students(**payload):
	_validate_keys(payload, ALLOWED_SEARCH_STUDENT_KEYS)

	query = (payload.get("query") or "").strip()
	limit = cint(payload.get("limit") or 10)

	if not query or len(query) < 2:
		return []

	# Scope by current user's Employee.school (+ descendants) to avoid sibling leakage.
	emp_school = _get_employee_school_for_session_user()
	if not emp_school:
		# Safe: if no employee school, return nothing rather than leaking data
		return []

	schools = [emp_school] + (get_descendants_of("School", emp_school) or [])

	rows = frappe.get_all(
		"Student",
		fields=["name", "student_full_name", "student_preferred_name", "student_image", "anchor_school"],
		filters={
			"anchor_school": ["in", schools],
			"enabled": 1,  # ✅ active students only
		},
		or_filters=[
			["Student", "student_full_name", "like", f"%{query}%"],
			["Student", "student_preferred_name", "like", f"%{query}%"],
			["Student", "name", "like", f"%{query}%"],
		],
		limit_page_length=limit,
	)

	out = []
	for r in rows:
		label = (r.get("student_preferred_name") or r.get("student_full_name") or r.get("name") or "").strip()
		meta = r.get("student_full_name") if r.get("student_preferred_name") else None
		out.append({
			"student": r.get("name"),
			"label": label or r.get("name"),
			"meta": meta,
			"image": _thumb_url(r.get("student_image")),
		})
	return out


@frappe.whitelist()
def search_follow_up_users(**payload):
	_validate_keys(payload, ALLOWED_ASSIGNEE_KEYS)

	next_step = payload.get("next_step")
	student = payload.get("student")
	query = (payload.get("query") or "").strip()
	limit = cint(payload.get("limit") or 10)

	if not next_step:
		frappe.throw(_("Next step is required."))
	if not student:
		frappe.throw(_("Student is required."))
	if not query or len(query) < 2:
		return []

	ns = frappe.db.get_value(
		"Student Log Next Step",
		next_step,
		["associated_role", "school"],
		as_dict=True
	)
	if not ns:
		frappe.throw(_("Next step not found."))

	role = (ns.get("associated_role") or "").strip() or None

	student_school = _get_student_school(student)
	allowed_schools = _allowed_next_step_schools(student_school)
	if not allowed_schools:
		return []

	# Employee is source of truth for school + user_id
	# Role constraint via Has Role on User
	params = {
		"schools": tuple(allowed_schools),
		"q": f"%{query}%",
		"limit": limit,
	}

	if role:
		sql = """
			SELECT
				u.name AS user_id,
				u.full_name AS full_name,
				e.school AS school
			FROM `tabEmployee` e
			INNER JOIN `tabUser` u ON u.name = e.user_id
			INNER JOIN `tabHas Role` hr ON hr.parent = u.name
			WHERE
				e.user_id IS NOT NULL
				AND e.school IN %(schools)s
				AND hr.role = %(role)s
				AND (
					u.full_name LIKE %(q)s
					OR u.name LIKE %(q)s
				)
			ORDER BY u.full_name ASC
			LIMIT %(limit)s
		"""
		params["role"] = role
	else:
		sql = """
			SELECT
				u.name AS user_id,
				u.full_name AS full_name,
				e.school AS school
			FROM `tabEmployee` e
			INNER JOIN `tabUser` u ON u.name = e.user_id
			WHERE
				e.user_id IS NOT NULL
				AND e.school IN %(schools)s
				AND (
					u.full_name LIKE %(q)s
					OR u.name LIKE %(q)s
				)
			ORDER BY u.full_name ASC
			LIMIT %(limit)s
		"""

	rows = frappe.db.sql(sql, params, as_dict=True)

	out = []
	for r in rows:
		label = (r.get("full_name") or r.get("user_id") or "").strip()
		out.append({
			"value": r.get("user_id"),
			"label": label or r.get("user_id"),
			"meta": r.get("school"),
		})
	return out


@frappe.whitelist()
def submit_student_log(**payload):
	_validate_keys(payload, ALLOWED_SUBMIT_KEYS)

	student = payload.get("student")
	log_type = payload.get("log_type")
	log = payload.get("log")
	requires_follow_up = cint(payload.get("requires_follow_up") or 0)

	if not student:
		frappe.throw(_("Student is required."))
	if not log_type:
		frappe.throw(_("Log type is required."))
	if not log or not str(log).strip():
		frappe.throw(_("Log text is required."))

	next_step = payload.get("next_step")
	follow_up_person = payload.get("follow_up_person")

	if requires_follow_up:
		if not next_step:
			frappe.throw(_("Next step is required."))
		if not follow_up_person:
			frappe.throw(_("Follow-up person is required."))

	doc = frappe.new_doc("Student Log")
	doc.student = student
	doc.log_type = log_type
	doc.log = log
	doc.date = nowdate()
	doc.time = nowtime(with_seconds=False)
	doc.visible_to_student = cint(payload.get("visible_to_student") or 0)
	doc.visible_to_guardians = cint(payload.get("visible_to_guardians") or 0)

	doc.requires_follow_up = requires_follow_up
	if requires_follow_up:
		doc.next_step = next_step
		doc.follow_up_person = follow_up_person

	doc.insert(ignore_permissions=False)
	doc.submit()

	return {"name": doc.name}
