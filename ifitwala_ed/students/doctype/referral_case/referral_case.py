# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/referral_case/referral_case.py

import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.desk.form.assign_to import add as assign_add

CASE_MANAGER_TAG = "[CASE_MANAGER]"
CASE_TASK_TAG = "[CASE_TASK]"

class ReferralCase(Document):
	def validate(self):
		# Prevent closing when child entries are still active
		if (self.case_status or "").strip() == "Closed":
			active = [row for row in (self.entries or []) if (row.status or "Open") in ("Open", "In Progress")]
			if active:
				frappe.throw("Cannot close case with open or in-progress entries.")

		# Keep native assignment in sync if manager changed via field
		if self.case_manager and (self.is_new() or self.case_manager != self.get_db_value("case_manager")):
			_assign_case_manager(self.name, self.case_manager, description="Updated via field", priority="Medium")

@frappe.whitelist()
def quick_update_status(name: str, new_status: str):
	doc = frappe.get_doc("Referral Case", name)
	if new_status not in ("Open", "In Progress", "On Hold", "Escalated", "Closed"):
		frappe.throw("Invalid status.")
	# Guard close
	if new_status == "Closed":
		active = [row for row in (doc.entries or []) if (row.status or "Open") in ("Open", "In Progress")]
		if active:
			frappe.throw("Cannot close case with open or in-progress entries.")
	doc.case_status = new_status
	doc.save(ignore_permissions=True)
	return {"ok": True}

@frappe.whitelist()
def set_manager(name: str, user: str):
	_assign_case_manager(name, user, description="Assigned via action", priority="Medium")
	return {"ok": True}

@frappe.whitelist()
def add_entry(name: str, entry_type: str, summary: str, assignee: str | None = None,
              status: str = "Open", attachment: str | None = None, create_todo: int = 1, due_date: str | None = None):
	doc = frappe.get_doc("Referral Case", name)
	row = doc.append("entries", {})
	row.entry_type = entry_type
	row.summary = summary
	row.assignee = assignee
	row.status = status or "Open"
	if attachment:
		row.attachments = attachment
	doc.save(ignore_permissions=True)

	# Optional ToDo for the assignee (task-level), tagged separately from manager ToDo
	if assignee and cint(create_todo):
		payload = {
			"doctype": "Referral Case",
			"name": name,
			"assign_to": [assignee],
			"priority": "Medium",
			"description": f"{CASE_TASK_TAG} {entry_type}: {summary[:120]}",
		}
		if due_date:
			payload["date"] = due_date
		assign_add(payload)
	return {"ok": True}

@frappe.whitelist()
def escalate(name: str, severity: str, note: str = ""):
	if severity not in ("High", "Critical"):
		frappe.throw("Severity must be High or Critical.")
	doc = frappe.get_doc("Referral Case", name)
	doc.severity = severity
	doc.case_status = "Escalated" if (doc.case_status or "Open") != "Closed" else doc.case_status
	doc.save(ignore_permissions=True)

	# Bump manager assignment to High priority (re-create manager ToDo)
	manager = doc.case_manager or _pick_manager_from_assignments(name) or _pick_any_counselor()
	if manager:
		_assign_case_manager(name, manager, description=f"Escalated to {severity}. {note or ''}".strip(), priority="High")
	return {"ok": True}

@frappe.whitelist()
def flag_mandated_reporting(name: str, referral: str | None = None):
	# Log a case entry and bump priority to High
	doc = frappe.get_doc("Referral Case", name)
	row = doc.append("entries", {})
	row.entry_type = "Other"
	row.summary = "Mandated reporting completed/triggered."
	row.status = "Done"
	doc.save(ignore_permissions=True)

	manager = doc.case_manager or _pick_manager_from_assignments(name) or _pick_any_counselor()
	if manager:
		_assign_case_manager(name, manager, description="Mandated reporting flagged", priority="High")
	return {"ok": True}

# ── Helpers ─────────────────────────────────────────────────────────────────

def _assign_case_manager(case_name: str, user: str, description: str = "Primary owner", priority: str = "Medium"):
	_close_manager_todos_only(case_name)
	assign_add({
		"doctype": "Referral Case",
		"name": case_name,
		"assign_to": [user],
		"priority": priority,
		"description": f"{CASE_MANAGER_TAG} {description}",
	})
	frappe.db.set_value("Referral Case", case_name, "case_manager", user, update_modified=False)

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

def on_doctype_update():
	frappe.db.add_index("Referral Case", ["case_manager"])
	frappe.db.add_index("Referral Case", ["student"])
	frappe.db.add_index("Referral Case", ["school"])
