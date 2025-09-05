# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student_support_guidance/student_support_guidance.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, cint, strip_html_tags
from frappe.desk.form.assign_to import add as assign_add

SSG = "Student Support Guidance"
SG = "Student Group"
SGS = "Student Group Student"
SGI = "Student Group Instructor"

ACK_TAG = "[ACK] Student Support Guidance"

class StudentSupportGuidance(Document):
	"""Lightweight lifecycle: publishing + snapshot caching is handled here."""

	def validate(self):
		# Keep counters defensively up to date (cheap – uses in-memory rows)
		self.high_priority_count = _has_any_high_priority(self)
		self.ack_required_count = _count_ack_required_items(self)

	def on_update(self):
		"""If the doc transitions to Published, ensure publish bookkeeping is applied.
		Note: counselors may also call publish(name) explicitly from the form button (recommended)."""
		prev_status = (frappe.db.get_value(SSG, self.name, "status") or "").strip() if not self.is_new() else ""
		if (self.status or "").strip() == "Published" and prev_status != "Published":
			_apply_publish(self, bump_version=True)

def on_doctype_update():
	frappe.db.add_index(SSG, ["student"])
	frappe.db.add_index(SSG, ["academic_year"])
	frappe.db.add_index("ToDo", ["reference_type", "reference_name", "allocated_to"])


# ─────────────────────────────────────────────────────────────────────────────
# Public API (whitelisted) used by Student modal
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_support_snapshot(student: str, academic_year: str) -> dict:
	ssg = _find_current_ssg(student, academic_year)
	if not ssg:
		# No SSG yet; return empty state (UI will show "No guidance yet.")
		return {"snapshot_html": ""}
	_enforce_view_permission(ssg)
	html = ssg.snapshot_html or _render_snapshot_html(ssg)
	return {"snapshot_html": html}

@frappe.whitelist()
def get_ack_status(student: str, academic_year: str) -> dict:
	ssg = _find_current_ssg(student, academic_year)
	if not ssg:
		return {"ack_required": False, "has_open_todo": False, "ack_required_count": 0, "ack_version": 0}
	_enforce_view_permission(ssg)
	# If there are no items that require acknowledgement, no ToDo is needed.
	need_ack = cint(ssg.ack_required_count) > 0 and (ssg.status or "") == "Published"
	if not need_ack:
		return {"ack_required": False, "has_open_todo": False, "ack_required_count": 0, "ack_version": cint(ssg.ack_version or 0)}

	user = frappe.session.user
	has_open = frappe.db.exists(
		"ToDo",
		{
			"reference_type": SSG,
			"reference_name": ssg.name,
			"allocated_to": user,
			"status": "Open",
		},
	)
	return {
		"ack_required": True,
		"has_open_todo": bool(has_open),
		"ack_required_count": cint(ssg.ack_required_count or 0),
		"ack_version": cint(ssg.ack_version or 0),
	}

@frappe.whitelist()
def acknowledge_current_guidance(student: str, academic_year: str) -> dict:
	ssg = _find_current_ssg(student, academic_year)
	if not ssg:
		frappe.throw(_("No current guidance is available to acknowledge."))
	_enforce_view_permission(ssg)

	# Close the current user's open ToDo (if any).
	user = frappe.session.user
	td = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": SSG,
			"reference_name": ssg.name,
			"allocated_to": user,
			"status": "Open",
		},
		fields=["name"],
		limit=5,
	)
	for r in td:
		frappe.db.set_value("ToDo", r.name, "status", "Closed", update_modified=False)

	return {"ok": True}

@frappe.whitelist()
def publish(name: str, notify: int = 1) -> dict:
	"""Explicit publish action counselors can call from a button on the SSG form."""
	doc = frappe.get_doc(SSG, name)
	# Only counselors / admins can publish
	roles = set(frappe.get_roles())
	if not ({"Counselor", "Academic Admin", "System Manager"} & roles):
		frappe.throw(_("You are not permitted to publish support guidance."))

	# Set publish state and apply full publish workflow (bump version, assign acks)
	doc.status = "Published"
	_apply_publish(doc, bump_version=True, notify=bool(cint(notify)))
	return {"ok": True, "ack_version": cint(doc.ack_version or 0)}


# ─────────────────────────────────────────────────────────────────────────────
# Core publish, snapshot & assignment logic
# ─────────────────────────────────────────────────────────────────────────────

def _apply_publish(doc: "StudentSupportGuidance", bump_version: bool = True, notify: bool = True):
	# 1) Stamp publish metadata
	if bump_version:
		doc.ack_version = cint(doc.ack_version or 0) + 1
	doc.last_published_on = now_datetime()
	doc.published_items = 1
	doc.high_priority_count = _has_any_high_priority(doc)
	doc.ack_required_count = _count_ack_required_items(doc)

	# 2) Render fresh snapshot into the cached HTML field
	doc.snapshot_html = _render_snapshot_html(doc)

	# 3) Save without re-triggering publish loops
	doc.save(ignore_permissions=True)

	# 4) Sync acknowledgment ToDos to current teacher-of-record recipients
	_sync_ack_assignments(doc, notify=notify)

def _sync_ack_assignments(doc: "StudentSupportGuidance", notify: bool = True):
	recipients = _teacher_userids_for_student_year(doc.student, doc.academic_year)

	# existing open ToDos for this SSG
	open_todos = frappe.get_all(
		"ToDo",
		filters={"reference_type": SSG, "reference_name": doc.name, "status": "Open"},
		fields=["name", "allocated_to"],
		limit=10000,
	)

	open_by_user = {r.allocated_to: r.name for r in open_todos}

	# If there are no items that require acknowledgement, close any remnants.
	if cint(doc.ack_required_count or 0) == 0 or (doc.status or "") != "Published":
		for name in open_by_user.values():
			frappe.db.set_value("ToDo", name, "status", "Closed", update_modified=False)
		return

	desc = f"{ACK_TAG} v{cint(doc.ack_version or 0)} – {doc.student} ({doc.academic_year})"

	# Add missing ToDos
	for user in recipients:
		if user not in open_by_user:
			payload = {
				"doctype": SSG,
				"name": doc.name,
				"assign_to": [user],
				"priority": "Medium",
				"description": desc,
			}
			if notify:
				payload["notify"] = 1
			assign_add(payload)

	# Close ToDos for users who are no longer recipients
	for user, todo_name in open_by_user.items():
		if user not in recipients:
			frappe.db.set_value("ToDo", todo_name, "status", "Closed", update_modified=False)


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot rendering (defensive against evolving child schema)
# ─────────────────────────────────────────────────────────────────────────────

def _render_snapshot_html(doc: "StudentSupportGuidance") -> str:
	"""Create a compact HTML snapshot suitable for teachers (no sensitive notes).
	We try common field names; if unavailable, we fall back to plain text."""
	items = doc.get("items") or []
	if not items:
		return '<div class="text-muted">' + _("No guidance yet.") + "</div>"

	lines = []
	for row in items:
		# Publish flag (if present)
		if _child_has(row, "publish") and not cint(getattr(row, "publish")):
			continue

		title = _first_present(row, ["title", "strategy", "headline", "label"]) or _("Guidance")
		# Prefer an explicit teacher-facing summary if provided
		raw = _first_present(row, ["teacher_summary", "summary_for_teacher", "summary", "notes"]) or ""
		text = strip_html_tags(raw) if raw else ""
		# Priority hint if present
		priority = _first_present(row, ["priority", "risk_level"]) or ""
		pr_badge = ""
		if priority and str(priority).lower() in {"high", "critical"}:
			pr_badge = f'<span class="badge bg-danger ms-1">{frappe.utils.escape_html(priority)}</span>'
		elif priority:
			pr_badge = f'<span class="badge bg-secondary ms-1">{frappe.utils.escape_html(priority)}</span>'

		lines.append(
			f'<li class="mb-1"><strong>{frappe.utils.escape_html(title)}</strong>{pr_badge}'
			f'{(": " + frappe.utils.escape_html(text)) if text else ""}</li>'
		)

	if not lines:
		return '<div class="text-muted">' + _("No guidance items are published.") + "</div>"

	return (
		'<div class="ssg-snapshot">'
		f'<ul class="ps-3 mb-0">{"".join(lines)}</ul>'
		"</div>"
	)

def _rebuild_snapshot(doc: "StudentSupportGuidance", save: bool = True) -> "StudentSupportGuidance":
	"""
	Lightweight rebuild used by external callers (e.g., Referral Case) after mutating items.
	- Recomputes counters (high_priority_count, ack_required_count)
	- Renders and caches snapshot_html
	- Does NOT bump ack_version
	- Does NOT (re)sync acknowledgment ToDos
	"""
	# Defensive: ensure we have a full doc
	ssg = frappe.get_doc(SSG, doc.name) if isinstance(doc, str) else doc

	# Recompute cheap counters from in-memory rows
	ssg.high_priority_count = _has_any_high_priority(ssg)
	ssg.ack_required_count = _count_ack_required_items(ssg)

	# Mark that we have published items if anything is present & published
	items = ssg.get("items") or []
	ssg.published_items = 1 if items else 0

	# Re-render teacher-facing snapshot HTML
	ssg.snapshot_html = _render_snapshot_html(ssg)

	if save:
		ssg.save(ignore_permissions=True)

	return ssg


# ─────────────────────────────────────────────────────────────────────────────
# Permission & audience helpers
# ─────────────────────────────────────────────────────────────────────────────

def _enforce_view_permission(doc_or_name):
	doc = frappe.get_doc(SSG, doc_or_name) if isinstance(doc_or_name, str) else doc_or_name
	user = frappe.session.user
	if user == "Administrator":
		return
	roles = set(frappe.get_roles(user))
	# Counselors & academic admins may view
	if {"Counselor", "Academic Admin", "System Manager"} & roles:
		return
	# Instructors must be teacher-of-record for this student & year
	teacher_ids = _teacher_userids_for_student_year(doc.student, doc.academic_year)
	if user in teacher_ids:
		return
	frappe.throw(_("You are not permitted to view this support snapshot."))

def _teacher_userids_for_student_year(student: str, academic_year: str) -> set[str]:
	"""Resolve instructor.user_id linked to Student Group(s) where this student is active in the given AY."""
	if not student or not academic_year:
		return set()
	# Join Student Group -> SGS -> SGI, constrained by AY & active membership
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT COALESCE(sgi.user_id, iu.user_id) AS user_id
		FROM `tabStudent Group` sg
		JOIN `tabStudent Group Student` sgs
		  ON sgs.parent = sg.name AND IFNULL(sgs.active,1)=1
		LEFT JOIN `tabStudent Group Instructor` sgi
		  ON sgi.parent = sg.name
		LEFT JOIN `tabInstructor` i
		  ON i.name = sgi.instructor
		LEFT JOIN `tabInstructor` iu
		  ON iu.name = sgi.instructor
		WHERE sg.academic_year = %(ay)s
		  AND sgs.student = %(student)s
		  AND IFNULL(sg.status, 'Active') = 'Active'
		""",
		{"ay": academic_year, "student": student},
		as_dict=True,
	) or []
	# Prefer user_id from child; if blank, try to derive later from Instructor.linked_user_id
	user_ids = {r.user_id for r in rows if r.user_id}
	if not user_ids:
		# Fallback pass: fetch instructors and then pull linked_user_id
		instructors = frappe.db.sql(
			"""
			SELECT DISTINCT sgi.instructor
			FROM `tabStudent Group` sg
			JOIN `tabStudent Group Student` sgs
			  ON sgs.parent = sg.name AND IFNULL(sgs.active,1)=1
			JOIN `tabStudent Group Instructor` sgi
			  ON sgi.parent = sg.name
			WHERE sg.academic_year = %(ay)s
			  AND sgs.student = %(student)s
			  AND IFNULL(sg.status, 'Active') = 'Active'
			""",
			{"ay": academic_year, "student": student},
			as_dict=True,
		) or []
		if instructors:
			link_map = frappe.get_all("Instructor", filters={"name": ["in", [x.instructor for x in instructors]]}, fields=["name", "linked_user_id"])
			for r in link_map:
				if r.linked_user_id:
					user_ids.add(r.linked_user_id)
	# Filter to enabled users only
	if not user_ids:
		return set()
	enabled = frappe.get_all("User", filters={"name": ["in", list(user_ids)], "enabled": 1}, pluck="name")
	return set(enabled or [])


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers (safe against evolving child schema)
# ─────────────────────────────────────────────────────────────────────────────

def _has_any_high_priority(doc: Document) -> int:
	items = doc.get("items") or []
	for row in items:
		if _child_has(row, "publish") and not cint(getattr(row, "publish")):
			continue
		if _child_has(row, "priority"):
			val = (getattr(row, "priority") or "").strip().lower()
			if val in {"high", "critical"}:
				return 1
	return 0

def _count_ack_required_items(doc: Document) -> int:
	items = doc.get("items") or []
	count = 0
	for row in items:
		if _child_has(row, "publish") and not cint(getattr(row, "publish")):
			continue
		# If the child has an explicit require_ack flag, honor it; else default to require ack for published items
		if _child_has(row, "require_ack"):
			if cint(getattr(row, "require_ack")):
				count += 1
		else:
			count += 1
	return count

def _child_has(row, fname: str) -> bool:
	try:
		return bool(getattr(row, "meta").get_field(fname))
	except Exception:
		# Row may not carry meta in some contexts; fallback to hasattr
		return hasattr(row, fname)

def _first_present(row, fields: list[str]) -> str | None:
	for f in fields:
		if hasattr(row, f) and getattr(row, f):
			return getattr(row, f)
	return None


# ─────────────────────────────────────────────────────────────────────────────
# Selection of the “current” SSG document for (student, AY)
# ─────────────────────────────────────────────────────────────────────────────

def _find_current_ssg(student: str, academic_year: str) -> Document | None:
	if not (student and academic_year):
		return None

	# Prefer Published, most recently published; else latest modified Draft
	published = frappe.get_all(
		SSG,
		filters={"student": student, "academic_year": academic_year, "status": "Published"},
		fields=["name"],
		order_by="COALESCE(last_published_on, modified) DESC",
		limit=1,
	)
	if published:
		return frappe.get_doc(SSG, published[0].name)

	latest = frappe.get_all(
		SSG,
		filters={"student": student, "academic_year": academic_year},
		fields=["name"],
		order_by="modified DESC",
		limit=1,
	)
	return frappe.get_doc(SSG, latest[0].name) if latest else None
