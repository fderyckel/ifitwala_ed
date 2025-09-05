# Copyright (c) 2025, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, nowdate, now, getdate
from frappe.desk.form.assign_to import add as add_assignment, remove as remove_assignment


def notify_admission_manager(doc):
	"""Realtime notify Admission Managers of a new inquiry (from webform)."""
	if frappe.flags.in_web_form and doc.workflow_state == "New Inquiry":
		user_ids = frappe.db.get_values("Has Role",
			{"role": "Admission Manager"}, "parent", as_dict=False
		)
		if not user_ids:
			return
		enabled = frappe.db.get_values("User",
			{"name": ["in", [u[0] for u in user_ids]], "enabled": 1}, "name", as_dict=False
		)
		for (user,) in enabled:
			frappe.publish_realtime(
				event="inbox_notification",
				message={
					"type": "Alert",
					"subject": "New Inquiry Submitted",
					"message": f"Inquiry {doc.name} has been submitted.",
					"reference_doctype": doc.doctype,
					"reference_name": doc.name,
				},
				user=user,
			)


def check_sla_breaches():
	"""
	Recompute SLA statuses using efficient SQL updates.
	Applies to Inquiry + Registration of Interest.
	"""
	logger = frappe.logger("sla_breaches", allow_site=True)

	contacted_states = ("Contacted", "Qualified", "Nurturing", "Accepted", "Unqualified")
	doc_types = ["Inquiry", "Registration of Interest"]

	for doctype in doc_types:
		if not frappe.db.table_exists(doctype):
			continue

		# 1) Mark Overdue
		frappe.db.sql(f"""
			UPDATE `tab{doctype}`
			   SET sla_status = '🔴 Overdue'
			 WHERE docstatus = 0
			   AND (
			     (workflow_state NOT IN {contacted_states}
			      AND first_contact_due_on IS NOT NULL
			      AND first_contact_due_on < CURDATE())
			     OR
			     (workflow_state = 'Assigned'
			      AND followup_due_on IS NOT NULL
			      AND followup_due_on < CURDATE())
			   )
			   AND sla_status != '🔴 Overdue'
		""")

		# 2) Mark Due Today
		frappe.db.sql(f"""
			UPDATE `tab{doctype}`
			   SET sla_status = '🟡 Due Today'
			 WHERE docstatus = 0
			   AND (
			     (workflow_state NOT IN {contacted_states}
			      AND first_contact_due_on = CURDATE())
			     OR
			     (workflow_state = 'Assigned'
			      AND followup_due_on = CURDATE())
			   )
			   AND sla_status != '🟡 Due Today'
		""")

		# 3) Mark Upcoming
		frappe.db.sql(f"""
			UPDATE `tab{doctype}`
			   SET sla_status = '⚪ Upcoming'
			 WHERE docstatus = 0
			   AND (
			     (workflow_state NOT IN {contacted_states}
			      AND first_contact_due_on > CURDATE())
			     OR
			     (workflow_state = 'Assigned'
			      AND followup_due_on > CURDATE())
			   )
			   AND sla_status != '⚪ Upcoming'
		""")

		# 4) Everything else = On Track
		frappe.db.sql(f"""
			UPDATE `tab{doctype}`
			   SET sla_status = '✅ On Track'
			 WHERE docstatus = 0
			   AND (
			     workflow_state IN {contacted_states}
			     OR (first_contact_due_on IS NULL AND followup_due_on IS NULL)
			   )
			   AND sla_status != '✅ On Track'
		""")

	frappe.db.commit()
	logger.info("SLA sweep done.")


def _create_native_assignment(doctype: str, name: str, user: str, description: str,
                              due_date: str, color: str | None = None) -> str | None:
	add_assignment({
		"assign_to": [user],
		"doctype": doctype,
		"name": name,
		"description": description,
		"date": due_date,
		"due_date": due_date,
		"notify": 1,
		"priority": "Medium",
	})
	todo_name = frappe.db.get_value(
		"ToDo",
		{"reference_type": doctype, "reference_name": name,
		 "allocated_to": user, "status": "Open"},
		"name", order_by="creation desc"
	)
	if color and todo_name:
		frappe.db.set_value("ToDo", todo_name, "color", color)
	return todo_name


def notify_user(user, message, doc):
	frappe.publish_realtime(
		event="inbox_notification",
		message={
			"type": "Alert",
			"subject": f"Inquiry: {doc.name}",
			"message": message,
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
		},
		user=user,
	)


def _get_first_contact_sla_days_default():
	return frappe.get_cached_value("Admission Settings", None, "first_contact_sla_days") or 7


def set_inquiry_deadlines(doc):
	if not getattr(doc, "first_contact_due_on", None):
		base = getdate(doc.submitted_at) if getattr(doc, "submitted_at", None) else getdate(nowdate())
		doc.first_contact_due_on = add_days(base, _get_first_contact_sla_days_default())


def update_sla_status(doc):
	"""This per-doc method remains for form-level updates (Assign/Save)."""
	today = getdate()
	state = (doc.workflow_state or "New Inquiry").strip()
	contacted_states = {"Contacted", "Qualified", "Nurturing", "Accepted", "Unqualified"}

	active = []
	if state not in contacted_states and getattr(doc, "first_contact_due_on", None):
		active.append(getdate(doc.first_contact_due_on))
	if state == "Assigned" and getattr(doc, "followup_due_on", None):
		active.append(getdate(doc.followup_due_on))

	if not active:
		doc.sla_status = "✅ On Track"
	elif any(d < today for d in active):
		doc.sla_status = "🔴 Overdue"
	elif any(d == today for d in active):
		doc.sla_status = "🟡 Due Today"
	else:
		doc.sla_status = "⚪ Upcoming"

@frappe.whitelist()
def assign_inquiry(doctype, docname, assigned_to):
	doc = frappe.get_doc(doctype, docname)

	# Validate role
	if not frappe.db.exists("Has Role", {"parent": assigned_to, "role": "Admission Officer"}):
		frappe.throw(f"{assigned_to} must be an active user with the 'Admission Officer' role.")

	# Prevent double-assign in our custom field
	if doc.assigned_to:
		frappe.throw(_("{0} is already assigned to this inquiry. Please use the Reassign button instead.").format(doc.assigned_to))

	# Load settings
	settings = frappe.get_cached_doc("Admission Settings")

	# Ensure first_contact_due_on exists for legacy rows
	if not getattr(doc, "first_contact_due_on", None):
		base = getdate(doc.submitted_at) if getattr(doc, "submitted_at", None) else getdate(nowdate())
		doc.first_contact_due_on = add_days(base, settings.first_contact_sla_days or 7)

	# Compute follow-up due and update Inquiry (in-memory only)
	followup_due = add_days(nowdate(), settings.followup_sla_days or 1)
	doc.assigned_to = assigned_to
	doc.workflow_state = "Assigned"
	doc.followup_due_on = followup_due

	# stamp FIRST assignment time (never overwrite)
	if not doc.assigned_at: 
		ts = frappe.utils.now_datetime() 
		doc.assigned_at = ts
		doc.db_set("assigned_at", ts, update_modified=False)

	# SLA + single save (avoid db_set before this)
	update_sla_status(doc)
	doc.save(ignore_permissions=True)

	# Native assignment (creates ToDo, may add comment/modify doc server-side)
	todo_name = _create_native_assignment(
		doctype=doctype,
		name=docname,
		user=assigned_to,
		description=f"Follow up inquiry {docname}",
		due_date=followup_due,
		color=(settings.todo_color or "blue"),
	)

	# Timeline + realtime (no further save)
	if todo_name:
		todo_link = frappe.utils.get_link_to_form("ToDo", todo_name)
		doc.add_comment(
			"Comment",
			text=frappe._(
				f"Assigned to <b>{assigned_to}</b> by <b>{frappe.session.user}</b> on {frappe.utils.formatdate(now())}. "
				f"See follow-up task: {todo_link}"
			),
		)

	notify_user(assigned_to, "🆕 You have been assigned a new inquiry.", doc)

	return {"assigned_to": assigned_to, "todo": todo_name}


@frappe.whitelist()
def reassign_inquiry(doctype, docname, new_assigned_to):
	doc = frappe.get_doc(doctype, docname)

	# Must be currently assigned
	if not doc.assigned_to:
		frappe.throw("This inquiry is not currently assigned. Please use the Assign button instead.")
	if doc.assigned_to == new_assigned_to:
		frappe.throw("This inquiry is already assigned to this user.")

	# Validate role
	if not frappe.db.exists("Has Role", {"parent": new_assigned_to, "role": "Admission Officer"}):
		frappe.throw(f"{new_assigned_to} must be an active user with the 'Admission Officer' role.")

	settings = frappe.get_cached_doc("Admission Settings")
	prev_assigned = doc.assigned_to

	# Ensure first_contact_due_on exists for legacy rows
	if not getattr(doc, "first_contact_due_on", None):
		base = getdate(doc.submitted_at) if getattr(doc, "submitted_at", None) else getdate(nowdate())
		doc.first_contact_due_on = add_days(base, settings.first_contact_sla_days or 7)

	# Compute new follow-up due and update Inquiry (in-memory only)
	followup_due = add_days(nowdate(), settings.followup_sla_days or 1)
	doc.assigned_to = new_assigned_to
	doc.workflow_state = "Assigned"
	doc.followup_due_on = followup_due

	# SLA + single save BEFORE messing with native assignments/comments
	update_sla_status(doc)
	doc.save(ignore_permissions=True)

	# Remove previous native assignment (closes its ToDo)
	try:
		remove_assignment(doctype=doctype, name=docname, assign_to=prev_assigned)
	except Exception:
		# Fallback: close any leftover ToDo rows defensively
		open_todos = frappe.get_all(
			"ToDo",
			filters={"reference_type": doctype, "reference_name": docname, "status": "Open"},
			pluck="name",
		)
		for t in open_todos:
			td = frappe.get_doc("ToDo", t)
			td.status = "Closed"
			td.save(ignore_permissions=True)

	# Notify previous assignee
	notify_user(prev_assigned, "🔁 Inquiry reassigned. You are no longer responsible.", doc)

	# Create native assignment for the new assignee
	new_todo = _create_native_assignment(
		doctype=doctype,
		name=docname,
		user=new_assigned_to,
		description=f"Follow up inquiry {docname} (reassigned)",
		due_date=followup_due,
		color=(settings.todo_color or "blue"),
	)

	# Timeline + realtime (no additional save)
	if new_todo:
		todo_link = frappe.utils.get_link_to_form("ToDo", new_todo)
		doc.add_comment(
			"Comment",
			text=frappe._(
				f"Reassigned to <b>{new_assigned_to}</b> by <b>{frappe.session.user}</b> on {frappe.utils.formatdate(now())}. "
				f"New follow-up task: {todo_link}"
			),
		)

	notify_user(new_assigned_to, "🆕 You have been assigned a new inquiry (reassignment).", doc)

	return {"reassigned_to": new_assigned_to, "todo": new_todo}

@frappe.whitelist()
def get_admission_officers(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		SELECT u.name
		FROM `tabUser` u
		JOIN `tabHas Role` r ON r.parent = u.name
		WHERE r.role = 'Admission Officer'
			AND u.enabled = 1
			AND u.name LIKE %s
		ORDER BY u.name ASC
		LIMIT %s OFFSET %s
	""", (f"%{txt}%", page_len, start))

def on_todo_update_close_marks_contacted(doc, method=None):
	# Only when ToDo is Closed
	if doc.status != "Closed":
		return
	# Only for our doctypes
	if doc.reference_type not in ("Inquiry", "Registration of Interest"):
		return
	if not doc.reference_name:
		return

	try:
		ref = frappe.get_doc(doc.reference_type, doc.reference_name)
	except frappe.DoesNotExistError:
		return

	state = (ref.workflow_state or "New Inquiry").strip()
	# Only flip from pre-contact states
	if state not in ("New Inquiry", "Assigned"):
		return

	# Only if the closing user is the current assignee on the document
	if not getattr(ref, "assigned_to", None):
		return
	if ref.assigned_to != doc.allocated_to:
		return

	# Reuse the doc's method; don't try to close ToDo again (avoid loops)
	ref.mark_contacted(complete_todo=False)