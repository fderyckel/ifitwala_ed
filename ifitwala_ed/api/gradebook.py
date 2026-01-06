# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/gradebook.py

# Gradebook API controller (UI-facing).
# - Grid reads Task Outcome only
# - Drawer shows Outcome + Submission versions
# - Contribution / moderation workflows are stubs until those doctypes are finalized

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime


# ---------------------------
# Helpers
# ---------------------------

def _require(value, label):
	if not value:
		frappe.throw(_("{0} is required.").format(label))


def _has_role(*roles):
	user_roles = set(frappe.get_roles(frappe.session.user))
	return any(r in user_roles for r in roles)


def _is_academic_adminish():
	return _has_role("System Manager", "Academic Admin", "Admin Assistant", "Curriculum Coordinator")


def _can_write_gradebook():
	# Tighten later if needed (e.g. only instructors assigned to delivery).
	return _has_role("System Manager", "Academic Admin", "Curriculum Coordinator", "Instructor")


def _get_student_display_map(student_ids):
	"""
	One batched lookup for student labels, to avoid N+1 in grid.
	Adjust fields if your Student doctype differs.
	"""
	if not student_ids:
		return {}

	# Prefer "student_name" if present; fallback to "full_name"/"first_name last_name"
	meta = frappe.get_meta("Student")
	fields = ["name"]
	if meta.get_field("student_name"):
		fields.append("student_name")
	elif meta.get_field("full_name"):
		fields.append("full_name")
	else:
		if meta.get_field("first_name"):
			fields.append("first_name")
		if meta.get_field("last_name"):
			fields.append("last_name")

	rows = frappe.get_all(
		"Student",
		filters={"name": ["in", list(set(student_ids))]},
		fields=fields,
		limit_page_length=0,
	)

	out = {}
	for r in rows:
		label = r.get("student_name") or r.get("full_name")
		if not label:
			fn = (r.get("first_name") or "").strip()
			ln = (r.get("last_name") or "").strip()
			label = (fn + " " + ln).strip() or r["name"]
		out[r["name"]] = label

	return out


def _apply_default_filters(filters: dict) -> dict:
	"""
	Enforce that callers don't accidentally pull huge cross-school datasets.
	Your UI will pass these anyway; this just protects server load.
	"""
	filters = filters or {}

	# If you want to force school+AY always, enforce here.
	# For now: allow delivery-scoped calls without school/AY.
	return filters


# ---------------------------
# Public endpoints (UI)
# ---------------------------

@frappe.whitelist()
def get_gradebook_grid(task_delivery: str, include_students: int = 1):
	"""
	Grid = Task Outcome rows for a single Task Delivery.

	Returns:
	{
	  task_delivery,
	  task,
	  student_group,
	  grading_mode,
	  grade_scale,
	  rows: [{
	    outcome, student, student_label,
	    submission_status, grading_status, procedural_status,
	    has_submission, has_new_submission, is_stale, is_complete,
	    official_score, official_grade, official_grade_value
	  }]
	}
	"""
	_require(task_delivery, "Task Delivery")

	# Permissions: keep simple now; tighten once instructor-delivery linking is enforced everywhere.
	if not _can_write_gradebook() and not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	delivery = frappe.db.get_value(
		"Task Delivery",
		task_delivery,
		[
			"name", "task", "student_group",
			"delivery_mode", "grading_mode",
			"grade_scale", "max_points",
			"course", "academic_year", "school",
		],
		as_dict=True,
	)
	if not delivery:
		frappe.throw(_("Task Delivery not found."))

	outcome_fields = [
		"name as outcome",
		"student",
		"submission_status",
		"grading_status",
		"procedural_status",
		"has_submission",
		"has_new_submission",
		"is_stale",
		"is_complete",
		"official_score",
		"official_grade",
		"official_grade_value",
	]

	outcomes = frappe.get_all(
		"Task Outcome",
		filters={"task_delivery": task_delivery},
		fields=outcome_fields,
		order_by="student asc",
		limit_page_length=0,
	)

	student_map = {}
	if int(include_students) == 1:
		student_map = _get_student_display_map([r.get("student") for r in outcomes])

	for r in outcomes:
		r["student_label"] = student_map.get(r.get("student")) if student_map else None

	return {
		"task_delivery": delivery["name"],
		"task": delivery.get("task"),
		"student_group": delivery.get("student_group"),
		"delivery_mode": delivery.get("delivery_mode"),
		"grading_mode": delivery.get("grading_mode"),
		"grade_scale": delivery.get("grade_scale"),
		"max_points": delivery.get("max_points"),
		"course": delivery.get("course"),
		"academic_year": delivery.get("academic_year"),
		"school": delivery.get("school"),
		"rows": outcomes,
	}


@frappe.whitelist()
def get_grading_drawer(outcome: str):
	"""
	Drawer payload for a single cell.

	Returns:
	{
	  outcome: { ...Task Outcome fields... },
	  submissions: [ ...Task Submission versions... ],
	  contributions: [],   # TODO Step 6/peer review model
	  compare: { ... }     # TODO (moderator compare / history)
	}
	"""
	_require(outcome, "Task Outcome")

	if not _can_write_gradebook() and not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	out_doc = frappe.get_doc("Task Outcome", outcome)

	# Minimal Outcome payload (don’t dump the whole doc to avoid leaking new fields accidentally)
	outcome_payload = {
		"name": out_doc.name,
		"task_delivery": out_doc.task_delivery,
		"task": out_doc.task,
		"student": out_doc.student,
		"student_group": out_doc.student_group,
		"submission_status": out_doc.submission_status,
		"grading_status": out_doc.grading_status,
		"procedural_status": out_doc.procedural_status,
		"has_submission": out_doc.has_submission,
		"has_new_submission": out_doc.has_new_submission,
		"is_stale": out_doc.is_stale,
		"is_complete": out_doc.is_complete,
		"completed_on": out_doc.completed_on,
		"official_score": out_doc.official_score,
		"official_grade": out_doc.official_grade,
		"official_grade_value": out_doc.official_grade_value,
		"grade_scale": out_doc.grade_scale,
		"official_feedback": out_doc.official_feedback,
	}

	# Submission versions (Task Submission doctype assumed to exist — if not, this will raise loudly)
	# Adjust fields once you share Task Submission schema.
	submissions = frappe.get_all(
		"Task Submission",
		filters={"task_outcome": out_doc.name},
		fields=[
			"name",
			"version",
			"submitted_on",
			"submitted_by",
			"submission_type",
			"text_submission",
			"link_submission",
			"attachments",
			"status",
		],
		order_by="version desc",
		limit_page_length=50,
	)

	return {
		"outcome": outcome_payload,
		"submissions": submissions,
		"contributions": [],  # Step 6: “My contribution” + peer review data model pending
		"compare": None,      # Step 6: moderator compare/history pending
	}


@frappe.whitelist()
def save_outcome_draft(
	outcome: str,
	official_score=None,
	official_grade=None,
	official_feedback=None,
	procedural_status=None,
):
	"""
	Teacher “Save draft” action.
	Writes directly to Task Outcome for now (Contribution model plugs in later).

	Status rules (minimal now):
	- grading_status moves to "In Progress" when draft saved and previously Not Started.
	- has_new_submission is cleared when teacher interacts (optional; we keep it unless you want clearing).
	"""
	_require(outcome, "Task Outcome")
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	doc = frappe.get_doc("Task Outcome", outcome)

	# Optional fields
	if official_score is not None:
		doc.official_score = official_score
	if official_grade is not None:
		doc.official_grade = official_grade
	if official_feedback is not None:
		doc.official_feedback = official_feedback
	if procedural_status is not None:
		doc.procedural_status = procedural_status

	if (doc.grading_status or "").strip() in ("Not Started", "", None):
		doc.grading_status = "In Progress"

	doc.save(ignore_permissions=True)
	return {"ok": True, "outcome": doc.name, "grading_status": doc.grading_status}


@frappe.whitelist()
def submit_outcome_contribution(outcome: str):
	"""
	Teacher “Submit contribution” action.
	In Step 6 proper this will create/update a Contribution row and compute official.
	For now: bumps status to "Needs Review" (signals moderation/peer review stage).
	"""
	_require(outcome, "Task Outcome")
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	doc = frappe.get_doc("Task Outcome", outcome)

	# Minimal transition
	doc.grading_status = "Needs Review"
	doc.is_stale = 0
	doc.save(ignore_permissions=True)

	return {"ok": True, "outcome": doc.name, "grading_status": doc.grading_status}


@frappe.whitelist()
def moderator_action(outcome: str, action: str, note: str | None = None):
	"""
	Moderator actions (Step 6):
	- Approve -> grading_status = Moderated (or Finalized, depending on your policy)
	- Adjust  -> keeps Moderated but allows changes (UI will call save_outcome_draft first)
	- Return  -> grading_status = In Progress (back to grader)

	This is intentionally simple until you finalize moderation policy + audit.
	"""
	_require(outcome, "Task Outcome")
	_require(action, "Action")

	if not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	doc = frappe.get_doc("Task Outcome", outcome)

	action = (action or "").strip()
	if action == "Approve":
		doc.grading_status = "Moderated"
	elif action == "Finalize":
		doc.grading_status = "Finalized"
	elif action == "Release":
		doc.grading_status = "Released"
	elif action == "Return":
		doc.grading_status = "In Progress"
	else:
		frappe.throw(_("Unknown action: {0}").format(action))

	# Optional audit hook (timeline comment for now)
	if note:
		doc.add_comment("Comment", text=f"Moderator action: {action}\n{note}")

	doc.save(ignore_permissions=True)
	return {"ok": True, "outcome": doc.name, "grading_status": doc.grading_status}


@frappe.whitelist()
def mark_new_submission_seen(outcome: str):
	"""
	UI convenience: when teacher opens drawer, they can clear the 'new evidence' flag.
	This only flips has_new_submission; it does NOT change submission_status.
	"""
	_require(outcome, "Task Outcome")
	if not _can_write_gradebook() and not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	frappe.db.set_value("Task Outcome", outcome, "has_new_submission", 0, update_modified=True)
	return {"ok": True, "outcome": outcome, "has_new_submission": 0}
