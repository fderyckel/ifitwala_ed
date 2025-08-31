# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/referral_case/referral_case.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, strip_html, now_datetime
from frappe.desk.form.assign_to import add as assign_add

CASE_MANAGER_TAG = "[CASE_MANAGER]"
CASE_TASK_TAG = "[CASE_TASK]"

class ReferralCase(Document):
	def validate(self):
		# Prevent closing when child entries are still active
		if (self.case_status or "").strip() == "Closed":
			active = [row for row in (self.entries or []) if (row.status or "Open") in ("Open", "In Progress")]
			if active:
				frappe.throw(_("Cannot close case with open or in-progress entries."))

		# ONLY counselors can be case managers
		if self.case_manager and not frappe.db.exists("Has Role", {"parent": self.case_manager, "role": "Counselor"}):
			frappe.throw(_("Case Manager must be a user with the Counselor role."))

		# Keep native assignment in sync if manager changed via field
		if self.case_manager and (self.is_new() or self.case_manager != self.get_db_value("case_manager")):
			_assign_case_manager(self.name, self.case_manager, description="Updated via field", priority="Medium")

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
	row.entry_datetime = now_datetime()
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
	row.entry_datetime = now_datetime()
	row.author = frappe.session.user
	doc.save(ignore_permissions=True)

	manager = doc.case_manager or _pick_manager_from_assignments(name) or _pick_any_counselor()
	if manager:
		_assign_case_manager(name, manager, description="Mandated reporting flagged", priority="High")
	return {"ok": True}

# ── Helpers ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def set_manager(name: str, user: str):
	doc = frappe.get_doc("Referral Case", name)
	_ensure_case_action_permitted(doc)
	if not frappe.db.exists("Has Role", {"parent": user, "role": "Counselor"}):
		frappe.throw(_("Selected user must have the Counselor role."))
	_assign_case_manager(name, user, description="Assigned via action", priority="Medium")
	return {"ok": True}

def _ensure_case_action_permitted(doc: "ReferralCase"):
	"""Counselor/Admin/System Manager or the current case_manager can act."""
	user = frappe.session.user
	if user == "Administrator":
		return
	roles = set(frappe.get_roles(user))
	if {"Counselor", "Academic Admin", "System Manager"} & roles:
		return
	if doc.case_manager and doc.case_manager == user:
		return
	frappe.throw(_("You are not permitted to perform this action on the case."))

def _assign_case_manager(case_name: str, user: str, description: str = "Primary owner", priority: str = "Medium"):
	if not frappe.db.exists("Has Role", {"parent": user, "role": "Counselor"}):
		frappe.throw(_("Case Manager must have the Counselor role."))
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
		# referral_case is stamped on creation; safe to refresh if desired:
		# frappe.db.set_value("Student Referral", ref, "referral_case", case_name, update_modified=False)

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
	role = (filters or {}).get("role") or "Counselor"
	return frappe.db.sql("""
		SELECT u.name, u.full_name
		FROM `tabUser` u
		WHERE u.enabled = 1
		  AND u.name IN (SELECT parent FROM `tabHas Role` WHERE role=%(role)s)
		  AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.full_name, u.name
		LIMIT %(page_len)s OFFSET %(start)s
	""", {"role": role, "txt": f"%{txt or ''}%", "page_len": page_len, "start": start})

def on_doctype_update():
	frappe.db.add_index("Referral Case", ["case_manager"])
	frappe.db.add_index("Referral Case", ["student"])
	frappe.db.add_index("Referral Case", ["school"])
	# Optional: enforce one referral → one case
	# frappe.db.add_index("Referral Case", ["referral"], index_name="uniq_referral", unique=True)

