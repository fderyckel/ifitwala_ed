# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/referral_case/referral_case.py

import frappe
from frappe.model.document import Document
from frappe.utils import cint, today, strip_html, cstr
from frappe.desk.form.assign_to import add as assign_add
from frappe import _

# Import snapshot rebuilder from SSG controller
from ifitwala_ed.students.doctype.student_support_guidance.student_support_guidance import (
	_rebuild_snapshot as ssg_rebuild_snapshot
)

CASE_MANAGER_TAG = "[CASE_MANAGER]"
CASE_TASK_TAG = "[CASE_TASK]"
GUIDANCE_ACK_TAG = "[GUIDANCE_ACK]"

# Constants reused from SSG module (keep strings here to avoid tight coupling)
SSG_PARENT = "Student Support Guidance"
SSG_CHILD = "Support Guidance Item"
TEACHER_SCOPE = "Teachers-of-student"
CASE_TEAM_SCOPE = "Case team only"

ALLOWED_ITEM_TYPES = {"Accommodation", "Strategy", "Trigger", "Safety Alert", "FYI"}

class ReferralCase(Document):
	def validate(self):
		# Prevent closing when child entries are still active
		if (self.case_status or "").strip() == "Closed":
			active = [row for row in (self.entries or []) if (row.status or "Open") in ("Open", "In Progress")]
			if active:
				frappe.throw(_("Cannot close case with open or in-progress entries."))

		# Case manager must be Counselor or Academic Admin
		if self.case_manager:
			allowed = ("Counselor", "Academic Admin")
			has_allowed = frappe.db.count("Has Role", {"parent": self.case_manager, "role": ["in", allowed]})
			if not has_allowed:
				frappe.throw(_("Case Manager must have either the Counselor or Academic Admin role."))

		# Keep native assignment in sync if manager changed via field
		if self.case_manager and (self.is_new() or self.case_manager != self.get_db_value("case_manager")):
			_assign_case_manager(self.name, self.case_manager, description="Updated via field", priority="Medium")

		# Enforce: assignee must be Academic Staff (when set)
		for r in (self.entries or []):
			if r.assignee:
				has_role = frappe.db.count(
					"Has Role",
					{"parent": r.assignee, "role": ["in", ("Academic Staff",)]}
				)
				if not has_role:
					frappe.throw(_("Entry assignee must have the Academic Staff role: {0}").format(r.assignee))


@frappe.whitelist()
def quick_update_status(name: str, new_status: str):
	doc = frappe.get_doc("Referral Case", name)
	_ensure_case_action_permitted(doc)
	if new_status not in ("Open", "In Progress", "On Hold", "Escalated", "Closed"):
		frappe.throw(_("Invalid status."))
	if new_status == "Closed":
		active = [row for row in (doc.entries or []) if (row.status or "Open") in ("Open", "In Progress")]
		if active:
			frappe.throw(_("Cannot close case with open or in-progress entries."))
	doc.case_status = new_status
	doc.save(ignore_permissions=True)
	return {"ok": True}

@frappe.whitelist()
def add_entry(name: str, entry_type: str, summary: str, assignee: str | None = None,
              status: str = "Open", attachment: str | None = None, create_todo: int = 1, due_date: str | None = None):
	doc = frappe.get_doc("Referral Case", name)
	_ensure_case_action_permitted(doc)

	row = doc.append("entries", {})
	row.entry_type = entry_type
	row.summary = summary
	row.assignee = assignee
	row.status = status or "Open"
	row.author = frappe.session.user 
	if attachment:
		row.attachments = attachment
	doc.save(ignore_permissions=True)

	# Optional ToDo for the assignee (task-level), tagged separately from manager ToDo
	if assignee and cint(create_todo):
		clean = strip_html(summary or "")[:120]
		payload = {
			"doctype": "Referral Case",
			"name": name,
			"assign_to": [assignee],
			"priority": "Medium",
			"description": f"{CASE_TASK_TAG} {entry_type}: {clean}",
		}
		if due_date:
			payload["date"] = due_date
		assign_add(payload)
	return {"ok": True}

@frappe.whitelist()
def escalate(name: str, severity: str, note: str = ""):
	doc = frappe.get_doc("Referral Case", name)
	_ensure_case_action_permitted(doc)

	if severity not in ("High", "Critical"):
		frappe.throw(_("Severity must be High or Critical."))
	doc.severity = severity
	doc.case_status = "Escalated" if (doc.case_status or "Open") != "Closed" else doc.case_status
	doc.save(ignore_permissions=True)

	manager = doc.case_manager or _pick_manager_from_assignments(name) or _pick_any_counselor()
	if manager:
		_assign_case_manager(name, manager, description=f"Escalated to {severity}. {note or ''}".strip(), priority="High")
	return {"ok": True}

@frappe.whitelist()
def flag_mandated_reporting(name: str, referral: str | None = None):
	doc = frappe.get_doc("Referral Case", name)
	_ensure_case_action_permitted(doc)

	row = doc.append("entries", {})
	row.entry_type = "Other"
	row.summary = "Mandated reporting completed/triggered."
	row.status = "Done"
	doc.save(ignore_permissions=True)

	manager = doc.case_manager or _pick_manager_from_assignments(name) or _pick_any_counselor()
	if manager:
		_assign_case_manager(name, manager, description="Mandated reporting flagged", priority="High")
	return {"ok": True}

# ─────────────────────────────────────────────────────────────────────────────
# Promote a case entry to teacher-facing guidance (with versioned ack)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def promote_entry_to_guidance(
	case_name: str,
	entry_rowname: str,
	item_type: str,
	teacher_text: str,
	high_priority: int = 0,
	requires_ack: int = 0,
	effective_from: str | None = None,
	expires_on: str | None = None,
	confidentiality: str = TEACHER_SCOPE,
	publish: int = 1
):
	"""
	Create or update a Student Support Guidance record for the student+AY and append a Guidance Item.
	- Enforces action permission (counselor/admin/system manager/case manager).
	- Rebuilds snapshot after change.
	- Issues/upserts native `assign_to` ToDos on the SSG parent, per teacher-of-record, versioned by ack_version.
	"""
	# Guards
	doc = frappe.get_doc("Referral Case", case_name)
	_ensure_case_action_permitted(doc)

	if item_type not in ALLOWED_ITEM_TYPES:
		frappe.throw(_("Invalid item type."))

	if confidentiality not in (TEACHER_SCOPE, CASE_TEAM_SCOPE):
		frappe.throw(_("Invalid confidentiality scope."))

	# Resolve parent SSG doc (student + AY)
	ssg = _get_or_create_support_guidance(doc.student, doc.academic_year, publish=cint(publish))

	# Append child item
	row = ssg.append("items", {})
	row.item_type = item_type
	row.teacher_text = teacher_text
	row.confidentiality = confidentiality
	row.high_priority = cint(high_priority)
	row.requires_ack = cint(requires_ack)
	if effective_from:
		row.effective_from = effective_from
	if expires_on:
		row.expires_on = expires_on
	row.source_case = case_name
	row.source_entry = entry_rowname
	try:
		row.author = frappe.session.user
	except Exception:
		pass

	# Persist parent + children
	ssg.status = "Published" if cint(publish) else (ssg.status or "Draft")
	ssg.save(ignore_permissions=True)

	# Rebuild denormalized snapshot (fast teacher reads)
	try:
		ssg = frappe.get_doc(SSG_PARENT, ssg.name)  # rehydrate
		ssg_rebuild_snapshot(ssg)
	except Exception:
		pass

	# Create/update acknowledgment assignments (teacher-visible & currently effective items only)
	if cint(requires_ack) and confidentiality == TEACHER_SCOPE:
		ack_count = _count_effective_teacher_ack_items(ssg.name)
		if ack_count > 0:
			# bump ack_version and store counters (no modified bump)
			curr_ver = cint(frappe.db.get_value(SSG_PARENT, ssg.name, "ack_version") or 0)
			new_ver = curr_ver + 1
			frappe.db.set_value(SSG_PARENT, ssg.name, {"ack_version": new_ver, "ack_required_count": ack_count})

			# determine priority for assignment
			assign_priority = "High" if (item_type == "Safety Alert" or cint(high_priority)) else "Medium"

			# upsert per-teacher ToDos for this version; close older ones
			teachers = _get_teachers_of_record(doc.student, doc.academic_year)
			_ensure_ack_assignments(ssg.name, new_ver, ack_count, teachers, assign_priority)

	return {"ok": True, "support_guidance": ssg.name, "item_rowname": row.name}

# ── Helpers for promotion/ack ────────────────────────────────────────────────

def _count_effective_teacher_ack_items(ssg_name: str) -> int:
	"""Count items on the SSG that are teacher-visible, require ack, and are effective today."""
	rows = frappe.get_all(
		SSG_CHILD,
		filters={"parent": ssg_name, "parenttype": SSG_PARENT, "confidentiality": TEACHER_SCOPE, "requires_ack": 1},
		fields=["name", "effective_from", "expires_on"]
	)
	if not rows:
		return 0
	today_str = today()
	def eff(r):
		start_ok = not r.get("effective_from") or cstr(r["effective_from"]) <= today_str
		end_ok = not r.get("expires_on") or cstr(r["expires_on"]) >= today_str
		return start_ok and end_ok
	return sum(1 for r in rows if eff(r))

def _ensure_ack_assignments(ssg_name: str, ack_version: int, ack_required_count: int, teachers: list[str], priority: str = "Medium"):
	"""
	For the given SSG + version, ensure each teacher has exactly one OPEN ToDo like:
	[GUIDANCE_ACK vX] N guidance item(s) to review
	Close any older GUIDANCE_ACK ToDos on the same SSG.
	"""
	if not teachers:
		return

	# Fetch existing open ToDos for this SSG
	open_todos = frappe.get_all(
		"ToDo",
		filters={"reference_type": SSG_PARENT, "reference_name": ssg_name, "status": "Open"},
		fields=["name", "allocated_to", "description"]
	) or []

	current_prefix = f"{GUIDANCE_ACK_TAG} v{ack_version}"
	current_holders = set()

	for td in open_todos:
		desc = (td.description or "").strip()
		if desc.startswith(current_prefix):
			if td.allocated_to:
				current_holders.add(td.allocated_to)
		elif desc.startswith(GUIDANCE_ACK_TAG):
			# Close older ack cycles
			frappe.db.set_value("ToDo", td.name, "status", "Closed", update_modified=False)

	# Create missing ToDos for this version
	label = f"{current_prefix} — {ack_required_count} guidance item(s) to review"
	for user in teachers:
		if user in current_holders:
			continue
		assign_add({
			"doctype": SSG_PARENT,
			"name": ssg_name,
			"assign_to": [user],
			"priority": priority,
			"description": label,
			"notify": 1
		})

def _get_or_create_support_guidance(student: str, academic_year: str, publish: int = 1):
	name = frappe.db.get_value(SSG_PARENT, {"student": student, "academic_year": academic_year}, "name")
	if name:
		return frappe.get_doc(SSG_PARENT, name)
	# Create lean parent
	doc = frappe.new_doc(SSG_PARENT)
	doc.student = student
	doc.academic_year = academic_year
	doc.status = "Published" if cint(publish) else "Draft"
	doc.insert(ignore_permissions=True)
	return doc

def _get_teachers_of_record(student: str, ay: str) -> list[str]:
	"""
	Teachers are instructors of the student's groups in the AY.
	Single SQL with JOINs; returns distinct users.
	"""
	users = frappe.db.sql("""
		SELECT DISTINCT sgi.user
		FROM `tabStudent Group Student` sgs
		JOIN `tabStudent Group` sg ON sg.name = sgs.parent
		JOIN `tabStudent Group Instructor` sgi ON sgi.parent = sg.name
		WHERE sgs.student = %(student)s
		  AND sg.academic_year = %(ay)s
		  AND IFNULL(sgi.user, '') != ''
	""", {"student": student, "ay": ay})
	return [u[0] for u in users or []]

# ─────────────────────────────────────────────────────────────────────────────
# Existing helpers
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def set_manager(name: str, user: str):
	doc = frappe.get_doc("Referral Case", name)
	_ensure_case_action_permitted(doc)

	allowed = ("Counselor", "Academic Admin")
	if not frappe.db.count("Has Role", {"parent": user, "role": ["in", allowed]}):
		frappe.throw(_("Selected user must have either the Counselor or Academic Admin role."))

	_assign_case_manager(name, user, description="Assigned via action", priority="Medium")
	return {"ok": True}


def _ensure_case_action_permitted(doc: "ReferralCase"):
	"""Only Counselor / Academic Admin OR the current case_manager may act.
	System Manager intentionally excluded for safeguarding privacy."""
	user = frappe.session.user
	roles = set(frappe.get_roles(user))

	# Authorised roles
	if {"Counselor", "Academic Admin"} & roles:
		return

	# Case manager can always act on their case
	if doc.case_manager and doc.case_manager == user:
		return

	frappe.throw(_("You are not permitted to perform this action on the case."))


def _assign_case_manager(case_name: str, user: str, description: str = "Primary owner", priority: str = "Medium"):
	allowed = ("Counselor", "Academic Admin")
	if not frappe.db.count("Has Role", {"parent": user, "role": ["in", allowed]}):
		frappe.throw(_("Case Manager must have either the Counselor or Academic Admin role."))

	_close_manager_todos_only(case_name)
	assign_add({
		"doctype": "Referral Case",
		"name": case_name,
		"assign_to": [user],
		"priority": priority,
		"description": f"{CASE_MANAGER_TAG} {description}",
	})
	frappe.db.set_value("Referral Case", case_name, "case_manager", user, update_modified=False)
	ref = frappe.db.get_value("Referral Case", case_name, "referral")
	if ref:
		frappe.db.set_value("Student Referral", ref, "assigned_case_manager", user, update_modified=False)


def _close_manager_todos_only(case_name: str):
	rows = frappe.get_all(
		"ToDo",
		filters={"reference_type": "Referral Case", "reference_name": case_name, "status": "Open"},
		fields=["name", "description"]
	)
	for r in rows:
		desc = (r.description or "").strip()
		if desc.startswith(CASE_MANAGER_TAG):
			frappe.db.set_value("ToDo", r.name, "status", "Closed", update_modified=False)

def _pick_manager_from_assignments(case_name: str) -> str | None:
	td = frappe.get_all(
		"ToDo",
		filters={"reference_type": "Referral Case", "reference_name": case_name, "status": "Open"},
		fields=["allocated_to", "description"]
	)
	for r in td:
		if (r.description or "").strip().startswith(CASE_MANAGER_TAG):
			return r.allocated_to
	return None

def _pick_any_counselor() -> str | None:
	cands = frappe.get_all("Has Role", filters={"role": "Counselor"}, fields=["parent"]) or []
	users = [c.parent for c in cands]
	if not users:
		return None
	enabled = frappe.get_all("User", filters={"name": ["in", users], "enabled": 1}, pluck="name")
	return enabled[0] if enabled else None

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def users_with_role(doctype, txt, searchfield, start, page_len, filters):
	params = filters or {}
	roles = params.get("roles") or params.get("role") or ["Counselor"]
	# normalize roles to a list
	if isinstance(roles, str):
		roles = [r.strip() for r in roles.split(",") if r.strip()] or ["Counselor"]

	return frappe.db.sql("""
		SELECT u.name, u.full_name
		FROM `tabUser` u
		WHERE u.enabled = 1
		  AND EXISTS (
		      SELECT 1 FROM `tabHas Role` hr
		      WHERE hr.parent = u.name AND hr.role IN %(roles)s
		  )
		  AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.full_name, u.name
		LIMIT %(page_len)s OFFSET %(start)s
	""", {"roles": tuple(roles), "txt": f"%{txt or ''}%", "page_len": page_len, "start": start})


def on_doctype_update():
	frappe.db.add_index("Referral Case", ["case_manager"])
	frappe.db.add_index("Referral Case", ["student"])
	frappe.db.add_index("Referral Case", ["school"])
