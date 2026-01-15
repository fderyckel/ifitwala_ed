# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus.py

import frappe
from frappe import _

STUDENT_LOG_DOCTYPE = "Student Log"
FOLLOW_UP_DOCTYPE = "Student Log Follow Up"

# Focus action types (v1)
ACTION_MODE = {
	"student_log.follow_up.act.submit": "assignee",
	"student_log.follow_up.review.decide": "author",
}

# ---------------------------------------------------------------------
# ID helpers (deterministic)
# ---------------------------------------------------------------------
def build_focus_item_id(
	workflow: str,
	reference_doctype: str,
	reference_name: str,
	action_type: str,
	user: str,
) -> str:
	"""
	Deterministic FocusItem id.

	NOTE:
	- This is *the* stable contract between focus.list() and focus.get_context().
	- Do not change the format without a migration plan (it breaks deep links).
	"""
	return f"{workflow}::{reference_doctype}::{reference_name}::{action_type}::{user}"


def _parse_focus_item_id(focus_item_id: str) -> dict:
	parts = (focus_item_id or "").split("::")
	if len(parts) != 5:
		frappe.throw(_("Invalid focus item id."), frappe.ValidationError)

	workflow, reference_doctype, reference_name, action_type, user = parts
	return {
		"workflow": workflow,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"action_type": action_type,
		"user": user,
	}


def _resolve_mode(action_type: str | None, log_doc) -> str:
	"""
	Server remains authoritative for mode.
	- If action_type is provided, it must be known and maps to the mode.
	- Otherwise infer from the log + session user.
	"""
	if action_type:
		mode = ACTION_MODE.get(action_type)
		if not mode:
			frappe.throw(_("Unknown Student Log action type."), frappe.ValidationError)
		return mode

	# fallback: infer from doc context
	if log_doc.follow_up_person and log_doc.follow_up_person == frappe.session.user:
		return "assignee"

	return "author"


# ---------------------------------------------------------------------
# Focus list (Phase 1: Student Log only)
# ---------------------------------------------------------------------
def _badge_from_due_date(due_date: str | None) -> str | None:
	if not due_date:
		return None
	try:
		today = frappe.utils.today()
		if due_date == today:
			return "Today"
		# "Due soon" = within next 2 days (cheap, deterministic)
		if frappe.utils.date_diff(due_date, today) in (1, 2):
			return "Due soon"
		# Keep calm: no "Overdue!" badge in v1
	except Exception:
		return None
	return None


def _can_read_student_log(name: str) -> bool:
	"""
	Cheap permission check without loading full doc.
	Avoid N+1 get_doc() calls in list().
	"""
	try:
		return bool(frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", docname=name))
	except Exception:
		return False


@frappe.whitelist()
def list_focus_items(open_only: int = 1, limit: int = 20, offset: int = 0):
	"""
	Return FocusItem[] for the current user.

	V1: Student Log only.
	- "action" items: ToDo allocated to user for Student Log follow-up work
	- "review" items: log owner, submitted follow-up exists, log not completed

	Performance:
	- No N+1 doc loads
	- Batched queries
	- Uses ToDo for assignee visibility (single-open ToDo policy)
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	limit = int(limit or 20)
	offset = int(offset or 0)
	limit = min(max(limit, 1), 50)
	offset = max(offset, 0)

	items: list[dict] = []

	# ------------------------------------------------------------
	# A) Assignee action items
	# ------------------------------------------------------------
	# Source: OPEN ToDo assigned to user for Student Log
	# NOTE:
	# - We page ToDo rows first (this is the staff "inbox" source of truth).
	# - After filtering, fewer than `limit` items may remain; that's fine in v1.
	todo_filters = {
		"allocated_to": user,
		"reference_type": STUDENT_LOG_DOCTYPE,
	}
	if frappe.utils.cint(open_only):
		todo_filters["status"] = "Open"

	todo_rows = frappe.get_all(
		"ToDo",
		filters=todo_filters,
		fields=["reference_name", "date"],
		order_by="date asc, modified desc",
		limit_start=offset,
		limit_page_length=limit,
	)

	log_names_action = [r.get("reference_name") for r in todo_rows if r.get("reference_name")]
	due_by_log = {
		r.get("reference_name"): (str(r.get("date")) if r.get("date") else None)
		for r in todo_rows
		if r.get("reference_name")
	}

	if log_names_action:
		log_rows = frappe.get_all(
			STUDENT_LOG_DOCTYPE,
			filters={"name": ["in", log_names_action]},
			fields=[
				"name",
				"student_name",
				"next_step",
				"requires_follow_up",
				"follow_up_status",
				"follow_up_person",
			],
			limit_page_length=1000,
		)

		log_by_name = {r["name"]: r for r in log_rows if r.get("name")}

		# submitted follow-ups by log (docstatus 1)
		submitted_logs = set(
			x.get("student_log")
			for x in frappe.get_all(
				FOLLOW_UP_DOCTYPE,
				filters={"student_log": ["in", log_names_action], "docstatus": 1},
				fields=["student_log"],
				limit_page_length=1000,
			)
			if x.get("student_log")
		)

		# next step titles (batched)
		next_step_names = sorted({r.get("next_step") for r in log_rows if r.get("next_step")})
		next_step_title_by_name = {}
		if next_step_names:
			ns = frappe.get_all(
				"Student Log Next Step",
				filters={"name": ["in", next_step_names]},
				fields=["name", "next_step_title"],
				limit_page_length=1000,
			)
			next_step_title_by_name = {x["name"]: x.get("next_step_title") for x in ns}

		# Preserve ToDo ordering (inbox order)
		for log_name in log_names_action:
			row = log_by_name.get(log_name)
			if not row:
				continue

			# must be follow-up required, not completed, and no submitted follow-up yet
			if not frappe.utils.cint(row.get("requires_follow_up")):
				continue
			if (row.get("follow_up_status") or "").lower() == "completed":
				continue
			if log_name in submitted_logs:
				continue

			# permission: must be able to read the log (cheap check)
			if not _can_read_student_log(log_name):
				continue

			due = due_by_log.get(log_name)
			badge = _badge_from_due_date(due)

			next_step_title = None
			if row.get("next_step"):
				next_step_title = next_step_title_by_name.get(row.get("next_step"))

			title = "Follow up"
			subtitle = f"{row.get('student_name') or log_name}"
			if next_step_title:
				subtitle = f"{subtitle} • Next step: {next_step_title}"

			action_type = "student_log.follow_up.act.submit"
			items.append(
				{
					"id": build_focus_item_id("student_log", STUDENT_LOG_DOCTYPE, log_name, action_type, user),
					"kind": "action",
					"title": title,
					"subtitle": subtitle,
					"badge": badge,
					"priority": 80,
					"due_date": due,
					"action_type": action_type,
					"reference_doctype": STUDENT_LOG_DOCTYPE,
					"reference_name": log_name,
					"payload": {
						"student_name": row.get("student_name"),
						"next_step": row.get("next_step"),
					},
					"permissions": {"can_open": True},
				}
			)

	# ------------------------------------------------------------
	# B) Author review items
	# ------------------------------------------------------------
	# Review item appears when:
	# - log owner == current user
	# - a submitted follow-up exists
	# - log not completed
	# - requires_follow_up = 1
	#
	# NOTE:
	# - This is Phase 1 and intentionally simple.
	# - We cap author logs to keep the query cheap.
	author_logs = frappe.get_all(
		STUDENT_LOG_DOCTYPE,
		filters={
			"owner": user,
			"follow_up_status": ["not in", ["Completed", "completed"]],
			"requires_follow_up": 1,
		},
		fields=["name", "student_name"],
		order_by="modified desc",
		limit_page_length=200,
	)

	author_log_names = [r.get("name") for r in author_logs if r.get("name")]
	if author_log_names:
		has_submitted = set(
			x.get("student_log")
			for x in frappe.get_all(
				FOLLOW_UP_DOCTYPE,
				filters={"student_log": ["in", author_log_names], "docstatus": 1},
				fields=["student_log"],
				limit_page_length=1000,
			)
			if x.get("student_log")
		)

		for r in author_logs:
			log_name = r.get("name")
			if not log_name or log_name not in has_submitted:
				continue

			# permission: must be able to read (cheap check)
			if not _can_read_student_log(log_name):
				continue

			action_type = "student_log.follow_up.review.decide"
			items.append(
				{
					"id": build_focus_item_id("student_log", STUDENT_LOG_DOCTYPE, log_name, action_type, user),
					"kind": "review",
					"title": "Review outcome",
					"subtitle": f"{r.get('student_name') or log_name} • Decide: close or continue follow-up",
					"badge": None,
					"priority": 70,
					"due_date": None,
					"action_type": action_type,
					"reference_doctype": STUDENT_LOG_DOCTYPE,
					"reference_name": log_name,
					"payload": {"student_name": r.get("student_name")},
					"permissions": {"can_open": True},
				}
			)

	# ------------------------------------------------------------
	# Sort + slice
	# ------------------------------------------------------------
	# Sort: action first, then priority desc, then due_date asc (cheap)
	def _sort_key(x):
		kind_rank = 0 if x.get("kind") == "action" else 1
		pr = x.get("priority") or 0
		due = x.get("due_date") or "9999-12-31"
		return (kind_rank, -pr, due)

	items.sort(key=_sort_key)
	return items[:limit]


# ---------------------------------------------------------------------
# Context endpoint (used by FocusRouterOverlay)
# ---------------------------------------------------------------------
@frappe.whitelist()
def get_context(
	focus_item_id: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	action_type: str | None = None,
):
	"""
	Return minimal routing + workflow context for a single focus item.

	- Accepts focus_item_id (preferred)
	- Or reference_doctype + reference_name (+ optional action_type)

	SECURITY:
	- If focus_item_id is provided, it must match frappe.session.user.
	"""
	if focus_item_id:
		parsed = _parse_focus_item_id(focus_item_id)
		reference_doctype = parsed["reference_doctype"]
		reference_name = parsed["reference_name"]
		action_type = parsed["action_type"]

		# Enforce: focus_item_id must match current session user (prevents leakage)
		if parsed.get("user") and parsed["user"] != frappe.session.user:
			frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

	if not reference_doctype or not reference_name:
		frappe.throw(_("Missing reference info."), frappe.ValidationError)

	if reference_doctype != STUDENT_LOG_DOCTYPE:
		frappe.throw(_("Only Student Log focus items are supported."), frappe.ValidationError)

	# Permission (doc-level) is mandatory
	if not frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", docname=reference_name):
		frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

	log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, reference_name)

	# Resolve mode (author vs assignee)
	mode = _resolve_mode(action_type, log_doc)

	# Minimal follow-up list (last 20)
	follow_up_rows = frappe.get_all(
		FOLLOW_UP_DOCTYPE,
		filters={"student_log": reference_name},
		fields=["name", "date", "follow_up_author", "follow_up", "docstatus"],
		order_by="modified desc",
		limit_page_length=20,
	)

	follow_ups = []
	for row in follow_up_rows:
		follow_ups.append(
			{
				"name": row.get("name"),
				"date": str(row.get("date")) if row.get("date") else None,
				"follow_up_author": row.get("follow_up_author"),
				"follow_up_html": row.get("follow_up") or "",
				"docstatus": row.get("docstatus"),
			}
		)

	return {
		"focus_item_id": focus_item_id,
		"action_type": action_type,
		"reference_doctype": STUDENT_LOG_DOCTYPE,
		"reference_name": reference_name,
		"mode": mode,
		"log": {
			"name": log_doc.name,
			"student_name": log_doc.student_name,
			"log_type": log_doc.log_type,
			"date": str(log_doc.date) if log_doc.date else None,
			"follow_up_status": log_doc.follow_up_status,
			"log_html": log_doc.log or "",
		},
		"follow_ups": follow_ups,
	}
