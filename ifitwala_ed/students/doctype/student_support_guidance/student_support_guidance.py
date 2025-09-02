# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate, today, cstr, escape_html, cint

PARENT_DTYPE = "Student Support Guidance"
CHILD_DTYPE = "Support Guidance Item"

TEACHER_SCOPE = "Teachers-of-student"
CASE_TEAM_SCOPE = "Case team only"
GUIDANCE_ACK_TAG = "[GUIDANCE_ACK]"

class StudentSupportGuidance(Document):
	def on_update(self):
		# Opportunistic refresh; heavy rebuilds should be explicit
		try:
			_rebuild_snapshot(self)
		except Exception:
			pass

def on_doctype_update():
	frappe.db.add_index(PARENT_DTYPE, ["student"])
	frappe.db.add_index(PARENT_DTYPE, ["academic_year"])
	try:
		frappe.db.add_unique(PARENT_DTYPE, ["student", "academic_year"])
	except Exception:
		pass

# ─────────────────────────────────────────────────────────────────────────────
# Teacher-facing APIs (no direct doctype perms required)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_support_snapshot(student: str, academic_year: str) -> dict:
	_require_user_can_view_teacher_snapshot(student, academic_year)

	name = frappe.db.get_value(PARENT_DTYPE, {"student": student, "academic_year": academic_year}, "name")
	if not name:
		return {
			"snapshot_html": _render_empty_snapshot(student, academic_year),
			"published_item_count": 0,
			"high_priority_count": 0,
			"last_published_on": None,
		}

	doc = frappe.get_doc(PARENT_DTYPE, name)
	if not doc.snapshot_html:
		_rebuild_snapshot(doc)
	return {
		"snapshot_html": doc.snapshot_html or _render_empty_snapshot(student, academic_year),
		"published_item_count": doc.published_item_count or 0,
		"high_priority_count": doc.high_priority_count or 0,
		"last_published_on": doc.last_published_on,
	}

@frappe.whitelist()
def get_ack_status(student: str, academic_year: str) -> dict:
	"""
	Return current acknowledgment status for the *current user*:
	- ack_required: whether there is an active ack cycle (ack_version > 0 and items > 0)
	- has_open_todo: whether the current user still has an OPEN ToDo for this cycle
	- counts and version for UI badges
	"""
	_require_user_can_view_teacher_snapshot(student, academic_year)

	row = frappe.db.get_value(
		PARENT_DTYPE,
		{"student": student, "academic_year": academic_year},
		["name", "ack_version", "ack_required_count"],
		as_dict=True,
	)
	if not row:
		return {"ack_required": False, "has_open_todo": False, "ack_version": 0, "ack_required_count": 0}

	ack_version = cint(row.ack_version or 0)
	ack_count = cint(row.ack_required_count or 0)
	if ack_version <= 0 or ack_count <= 0:
		return {"ack_required": False, "has_open_todo": False, "ack_version": ack_version, "ack_required_count": ack_count}

	prefix = f"{GUIDANCE_ACK_TAG} v{ack_version}"
	has_open = bool(frappe.get_all(
		"ToDo",
		filters={
			"reference_type": PARENT_DTYPE,
			"reference_name": row.name,
			"allocated_to": frappe.session.user,
			"status": "Open",
		},
		pluck="name",
	))
	if has_open:
		# verify it is the current cycle (prefix match); if not current, treat as no-open
		open_rows = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": PARENT_DTYPE,
				"reference_name": row.name,
				"allocated_to": frappe.session.user,
				"status": "Open",
			},
			fields=["name", "description"],
		)
		has_open = any(((r.description or "").strip().startswith(prefix)) for r in open_rows)

	return {
		"ack_required": True,
		"has_open_todo": has_open,
		"ack_version": ack_version,
		"ack_required_count": ack_count,
	}

@frappe.whitelist()
def acknowledge_current_guidance(student: str, academic_year: str) -> dict:
	"""
	Close the current user's OPEN GUIDANCE_ACK ToDo(s) for the active ack_version on the SSG.
	Idempotent: safe to call multiple times.
	Permission: same as read snapshot (teacher-of-record or counselor/admin/system manager).
	"""
	_require_user_can_view_teacher_snapshot(student, academic_year)

	row = frappe.db.get_value(
		PARENT_DTYPE,
		{"student": student, "academic_year": academic_year},
		["name", "ack_version", "ack_required_count"],
		as_dict=True,
	)
	if not row:
		return {"ok": True, "changed": 0, "message": _("No guidance record found.")}

	ack_version = cint(row.ack_version or 0)
	ack_count = cint(row.ack_required_count or 0)
	if ack_version <= 0 or ack_count <= 0:
		return {"ok": True, "changed": 0, "message": _("No acknowledgment required.")}

	prefix = f"{GUIDANCE_ACK_TAG} v{ack_version}"
	open_rows = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": PARENT_DTYPE,
			"reference_name": row.name,
			"allocated_to": frappe.session.user,
			"status": "Open",
		},
		fields=["name", "description"],
	) or []

	changed = 0
	for r in open_rows:
		desc = (r.description or "").strip()
		if desc.startswith(prefix):
			frappe.db.set_value("ToDo", r.name, "status", "Closed", update_modified=False)
			changed += 1

	return {"ok": True, "changed": changed, "ack_version": ack_version}

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rebuild_snapshot(doc: "StudentSupportGuidance"):
	if not (doc.student and doc.academic_year):
		return

	items = frappe.get_all(
		CHILD_DTYPE,
		filters={"parent": doc.name, "parenttype": PARENT_DTYPE, "confidentiality": TEACHER_SCOPE},
		fields=["name", "item_type", "teacher_text", "high_priority", "effective_from", "expires_on"],
		order_by="high_priority desc, modified desc"
	)

	today_d = getdate(today())
	def _is_effective(it):
		start_ok = (not it.get("effective_from")) or (getdate(it["effective_from"]) <= today_d)
		end_ok = (not it.get("expires_on")) or (getdate(it["expires_on"]) >= today_d)
		return start_ok and end_ok

	effective = [it for it in items if _is_effective(it)]

	high_cnt = sum(1 for it in effective if cstr(it.get("high_priority")) in ("1", "Yes", "True", "true"))
	pub_cnt = len(effective)

	alerts = [it for it in effective if (it.get("item_type") or "").strip() == "Safety Alert"]
	non_alerts = [it for it in effective if (it.get("item_type") or "").strip() != "Safety Alert"]

	top_bucket_types = {"Accommodation", "Strategy"}
	top_candidates = [it for it in non_alerts if (it.get("item_type") or "") in top_bucket_types]
	top_three = top_candidates[:3]

	def _li(it):
		txt = escape_html(it.get("teacher_text") or "").replace("\n", "<br>")
		return f"<li>{txt}</li>"

	html_parts = []
	html_parts.append(f"<div class='ssg-snap'><div class='ssg-head'><strong>{escape_html(doc.student)}</strong> • {escape_html(doc.academic_year)}</div>")

	if alerts:
		html_parts.append("<div class='ssg-sec'><div class='ssg-title' style='color:#b91c1c;'>⚠️ Safety Alerts</div><ul>")
		html_parts.extend(_li(it) for it in alerts)
		html_parts.append("</ul></div>")

	if top_three:
		html_parts.append("<div class='ssg-sec'><div class='ssg-title'>Top classroom supports</div><ul>")
		html_parts.extend(_li(it) for it in top_three)
		html_parts.append("</ul></div>")

	if non_alerts:
		grouped = {}
		for it in non_alerts:
			grouped.setdefault(it.get("item_type") or "Other", []).append(it)
		html_parts.append("<div class='ssg-sec'><div class='ssg-title'>All published guidance</div>")
		for typ in sorted(grouped.keys()):
			html_parts.append(f"<div class='ssg-sub'>{escape_html(typ)}</div><ul>")
			html_parts.extend(_li(it) for it in grouped[typ])
			html_parts.append("</ul>")
		html_parts.append("</div>")

	if not effective:
		html_parts.append(_render_empty_snapshot(doc.student, doc.academic_year))

	html_parts.append("</div>")

	doc.snapshot_html = "".join(html_parts)
	doc.high_priority_count = high_cnt
	doc.published_item_count = pub_cnt
	doc.last_published_on = now_datetime() if pub_cnt else None
	doc.db_update()

def _render_empty_snapshot(student: str, ay: str) -> str:
	return f"""
		<div class='ssg-snap'>
			<div class='ssg-head'><strong>{escape_html(student)}</strong> • {escape_html(ay)}</div>
			<div class='ssg-sec'><em>{_('No published guidance yet for classroom view.')}</em></div>
		</div>
	"""

def _require_user_can_view_teacher_snapshot(student: str, academic_year: str):
	user = frappe.session.user
	if user == "Administrator":
		return
	roles = set(frappe.get_roles(user))
	if {"Counselor", "Academic Admin", "System Manager"} & roles:
		return
	if _is_teacher_of_student(user, student, academic_year):
		return
	frappe.throw(_("You are not permitted to view this guidance."))

def _is_teacher_of_student(user: str, student: str, ay: str) -> bool:
	try:
		ok = frappe.db.sql("""
			SELECT 1
			FROM `tabProgram Enrollment` pe
			JOIN `tabProgram Enrollment Course` pec ON pec.parent = pe.name
			JOIN `tabStudent Group Student` sgs ON sgs.student = pe.student
			JOIN `tabStudent Group` sg ON sg.name = sgs.parent
			JOIN `tabStudent Group Instructor` sgi ON sgi.parent = sg.name
			WHERE pe.student = %(student)s
			  AND pe.academic_year = %(ay)s
			  AND sg.academic_year = pe.academic_year
			  AND (sg.course = pec.course OR pec.course = sg.course)
			  AND sgi.user = %(user)s
			LIMIT 1
		""", {"student": student, "ay": ay, "user": user})
		if ok:
			return True
	except Exception:
		pass

	try:
		ok = frappe.db.sql("""
			SELECT 1
			FROM `tabStudent Group Student` sgs
			JOIN `tabStudent Group` sg ON sg.name = sgs.parent
			JOIN `tabStudent Group Instructor` sgi ON sgi.parent = sg.name
			WHERE sgs.student = %(student)s
			  AND sg.academic_year = %(ay)s
			  AND sgi.user = %(user)s
			LIMIT 1
		""", {"student": student, "ay": ay, "user": user})
		return bool(ok)
	except Exception:
		return False
