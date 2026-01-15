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


@frappe.whitelist()
def list(open_only: int = 1, limit: int = 20, offset: int = 0):
	"""
	Return FocusItem[] for the current user.

	V1: Student Log only.
	- "action" items: assigned to user, requires follow-up, no submitted follow-up yet
	- "review" items: user is author (owner), submitted follow-up exists, not completed

	Performance:
	- No N+1: batched queries
	- Uses ToDo for assignee visibility (single-open ToDo policy)
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	limit = int(limit or 20)
	offset = int(offset or 0)
	limit = min(max(limit, 1), 50)

	items: list[dict] = []

	# -------------------------
	# A) Assignee action items
	# -------------------------
	# Source: OPEN ToDo assigned to user for Student Log
	todo_rows = frappe.get_all(
		"ToDo",
		filters={
			"allocated_to": user,
			"reference_type": STUDENT_LOG_DOCTYPE,
			"status": "Open",
		},
		fields=["reference_name", "date"],
		order_by="date asc, modified desc",
		limit_start=offset,
		limit_page_length=limit,
	)

	log_names_action = [r.get("reference_name") for r in todo_rows if r.get("reference_name")]
	due_by_log = {r.get("reference_name"): (str(r.get("date")) if r.get("date") else None) for r in todo_rows}

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
		)

		# which logs already have a SUBMITTED follow-up?
		submitted = set(
			[x.get("student_log") for x in frappe.get_all(
				FOLLOW_UP_DOCTYPE,
				filters={"student_log": ["in", log_names_action], "docstatus": 1},
				fields=["student_log"],
				limit_page_length=1000,
			)]
		)

		# next step titles (cheap, batched)
		next_step_names = list({r.get("next_step") for r in log_rows if r.get("next_step")})
		next_step_title_by_name = {}
		if next_step_names:
			ns = frappe.get_all(
				"Student Log Next Step",
				filters={"name": ["in", next_step_names]},
				fields=["name", "next_step_title"],
				limit_page_length=1000,
			)
			next_step_title_by_name = {x["name"]: x.get("next_step_title") for x in ns}

		# map for stable ordering same as todo_rows
		log_by_name = {r["name"]: r for r in log_rows if r.get("name")}

		for log_name in log_names_action:
			row = log_by_name.get(log_name)
			if not row:
				continue

			# must be follow-up required, not completed, and no submitted follow-up yet
			if not frappe.utils.cint(row.get("requires_follow_up")):
				continue
			if (row.get("follow_up_status") or "").lower() == "completed":
				continue
			if log_name in submitted:
				continue

			# permission: must be able to read the log
			try:
				log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, log_name)
				if not frappe.has_permission(STUDENT_LOG_DOCTYPE, doc=log_doc, ptype="read"):
					continue
			except Exception:
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
			items.append({
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
			})

	# -------------------------
	# B) Author review items
	# -------------------------
	# Review item appears when:
	# - log owner == current user
	# - a submitted follow-up exists
	# - log not completed
	# - (optional) requires_follow_up = 1
	author_logs = frappe.get_all(
		STUDENT_LOG_DOCTYPE,
		filters={
			"owner": user,
			"follow_up_status": ["!=", "Completed"],
			"requires_follow_up": 1,
		},
		fields=["name", "student_name"],
		order_by="modified desc",
		limit_page_length=200,  # small cap; still cheap
	)

	author_log_names = [r["name"] for r in author_logs if r.get("name")]
	if author_log_names:
		has_submitted = set(
			[x.get("student_log") for x in frappe.get_all(
				FOLLOW_UP_DOCTYPE,
				filters={"student_log": ["in", author_log_names], "docstatus": 1},
				fields=["student_log"],
				limit_page_length=1000,
			)]
		)

		# show only those with submitted follow-up
		for r in author_logs:
			log_name = r.get("name")
			if not log_name or log_name not in has_submitted:
				continue

			# permission: must be able to read
			try:
				log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, log_name)
				if not frappe.has_permission(STUDENT_LOG_DOCTYPE, doc=log_doc, ptype="read"):
					continue
			except Exception:
				continue

			action_type = "student_log.follow_up.review.decide"
			items.append({
				"id": build_focus_item_id("student_log", STUDENT_LOG_DOCTYPE, log_name, action_type, user),
				"kind": "review",
				"title": "Review outcome",
				"subtitle": f"{r.get('student_name') or log_name} • Decide: close or continue",
				"badge": None,
				"priority": 70,
				"due_date": None,
				"action_type": action_type,
				"reference_doctype": STUDENT_LOG_DOCTYPE,
				"reference_name": log_name,
				"payload": {"student_name": r.get("student_name")},
				"permissions": {"can_open": True},
			})

	# Sort: action first, then priority desc, then due_date asc (cheap)
	def _sort_key(x):
		kind_rank = 0 if x.get("kind") == "action" else 1
		pr = x.get("priority") or 0
		due = x.get("due_date") or "9999-12-31"
		return (kind_rank, -pr, due)

	items.sort(key=_sort_key)

	# Final page slice (because we merged two sources)
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
	Return minimal routing + header context for a single focus item.

	- Accepts focus_item_id (preferred)
	- Or reference_doctype + reference_name (+ optional action_type)
	"""
	parsed_user = None
	if focus_item_id:
		parsed = _parse_focus_item_id(focus_item_id)
		reference_doctype = parsed["reference_doctype"]
		reference_name = parsed["reference_name"]
		action_type = parsed["action_type"]
		parsed_user = parsed["user"]

		# Enforce: focus_item_id must match current session user (prevents leakage)
		if parsed_user and parsed_user != frappe.session.user:
			frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

	if not reference_doctype or not reference_name:
		frappe.throw(_("Missing reference info."), frappe.ValidationError)

	if reference_doctype != STUDENT_LOG_DOCTYPE:
		frappe.throw(_("Only Student Log focus items are supported."), frappe.ValidationError)

	log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, reference_name)
	if not frappe.has_permission(STUDENT_LOG_DOCTYPE, doc=log_doc, ptype="read"):
		frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

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
