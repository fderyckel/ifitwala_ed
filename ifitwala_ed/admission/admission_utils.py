# Copyright (c) 2025, Francois de Ryckel and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_days, nowdate, now
from frappe.utils import now_datetime, getdate
from frappe.desk.form.assign_to import add as add_assignment, remove as remove_assignment

def notify_admission_manager(doc):
	if frappe.flags.in_web_form and doc.workflow_state == "New Inquiry":
		user_ids = frappe.db.get_values(
			"Has Role",
			filters={"role": "Admission Manager"},
			fieldname="parent",
			as_dict=False
		)
		enabled_users = frappe.db.get_values(
			"User",
			filters={"name": ["in", [u[0] for u in user_ids]], "enabled": 1},
			fieldname="name",
			as_dict=False
		)
		if not enabled_users:
			return

		for user_tuple in enabled_users:
			user = user_tuple[0]
			frappe.publish_realtime(
				event='inbox_notification',
				message={
					'type': 'Alert',
					'subject': f"New Inquiry Submitted",
					'message': f"Inquiry {doc.name} has been submitted.",
					'reference_doctype': doc.doctype,
					'reference_name': doc.name
				},
				user=user
			)


def check_sla_breaches():
	"""Recompute SLA status for open admission records using the refactored fields.
	Active clocks (pre-contact only):
	- first_contact_due_on: active until the inquiry is contacted.
	- followup_due_on: active only while workflow_state == 'Assigned' (pre-contact).
	"""

	doc_types = ["Inquiry", "Registration of Interest"]
	today = getdate()

	# States defined on Inquiry:
	# New Inquiry, Assigned, Contacted, Qualified, Nurturing, Accepted, Unqualified
	contacted_states = {"Contacted", "Qualified", "Nurturing", "Accepted", "Unqualified"}

	for doctype in doc_types:
		entries = frappe.db.get_values(
			doctype,
			filters={"docstatus": 0},
			fieldname=[
				"name",
				"assigned_to",
				"workflow_state",
				"first_contact_due_on",
				"followup_due_on",
				"sla_status",
			],
			as_dict=True,
		)

		for row in entries:
			name = row["name"]
			assigned_to = row.get("assigned_to")
			state = (row.get("workflow_state") or "New Inquiry").strip()

			active_dates = []
			# First-contact clock runs until contacted
			if state not in contacted_states and row.get("first_contact_due_on"):
				active_dates.append(getdate(row["first_contact_due_on"]))

			# Follow-up clock runs only when Assigned (pre-contact)
			if state == "Assigned" and row.get("followup_due_on"):
				active_dates.append(getdate(row["followup_due_on"]))

			# Resolve SLA
			if not active_dates:
				new_status = "✅ On Track"
			elif any(d < today for d in active_dates):
				new_status = "🔴 Overdue"
			elif any(d == today for d in active_dates):
				new_status = "🟡 Due Today"
			else:
				new_status = "⚪ Upcoming"

			if new_status != row.get("sla_status"):
				frappe.db.set_value(doctype, name, "sla_status", new_status)

				# Notify stakeholders when overdue
				if new_status == "🔴 Overdue" and assigned_to:
					doc_ref = frappe._dict({"doctype": doctype, "name": name})
					notify_user(assigned_to, "🔴 SLA is overdue for this inquiry.", doc_ref)

					for (manager,) in frappe.db.get_values("Has Role", {"role": "Admission Manager"}, "parent"):
						notify_user(manager, "🔴 SLA is overdue for this inquiry.", doc_ref)

def _create_native_assignment(doctype: str, name: str, user: str, description: str, due_date: str, color: str | None = None) -> str | None:
	# Create native assignment; also sends notifications if notify=1
	add_assignment({
		"assign_to": [user],
		"doctype": doctype,
		"name": name,
		"description": description,
		"date": due_date,        # Frappe accepts 'date' as the ToDo due field
		"due_date": due_date,    # set both for compatibility across minor versions
		"notify": 1,
		"priority": "Medium",
	})
	# Fetch the just-created ToDo so we can color it and link it in timeline
	todo_name = frappe.db.get_value(
		"ToDo",
		{
			"reference_type": doctype,
			"reference_name": name,
			"allocated_to": user,
			"status": "Open",
		},
		"name",
		order_by="creation desc",
	)
	if color and todo_name:
		frappe.db.set_value("ToDo", todo_name, "color", color)
	return todo_name


def notify_user(user, message, doc):
	frappe.publish_realtime(
		event='inbox_notification',
		message={
			'type': 'Alert',
			'subject': f"Inquiry: {doc.name}",
			'message': message,
			'reference_doctype': doc.doctype,
			'reference_name': doc.name
		},
		user=user
	)

def _get_first_contact_sla_days_default(): 
	# Historical default was 7 
	return frappe.get_cached_value("Admission Settings", None, "first_contact_sla_days") or 7

def set_inquiry_deadlines(doc):
	"""
		Set only the first_contact_due_on on save (typically right after insert),
		derived from submitted_at.date() + first_contact_sla_days.
		The followup_due_on is handled on (re)assignment.
	"""
	if not getattr(doc, "first_contact_due_on", None):
		base = getdate(doc.submitted_at) if getattr(doc, "submitted_at", None) else getdate(nowdate())
		doc.first_contact_due_on = add_days(base, _get_first_contact_sla_days_default())
 

def update_sla_status(doc):
	"""Set SLA status based on active pre-contact clocks and current workflow state."""
	today = getdate()
	state = (doc.workflow_state or "New Inquiry").strip()

	# Valid states on Inquiry: New Inquiry, Assigned, Contacted, Qualified, Nurturing, Accepted, Unqualified
	contacted_states = {"Contacted", "Qualified", "Nurturing", "Accepted", "Unqualified"}

	active_dates = []
	# First-contact clock runs until the inquiry is contacted
	if state not in contacted_states and getattr(doc, "first_contact_due_on", None):
		active_dates.append(getdate(doc.first_contact_due_on))

	# Follow-up clock runs only while Assigned (pre-contact)
	if state == "Assigned" and getattr(doc, "followup_due_on", None):
		active_dates.append(getdate(doc.followup_due_on))

	if not active_dates:
		doc.sla_status = "✅ On Track"
	elif any(d < today for d in active_dates):
		doc.sla_status = "🔴 Overdue"
	elif any(d == today for d in active_dates):
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

	# Compute follow-up due and update Inquiry
	followup_due = add_days(nowdate(), settings.followup_sla_days or 1)
	doc.db_set("assigned_to", assigned_to)
	doc.db_set("workflow_state", "Assigned")
	doc.db_set("followup_due_on", followup_due)
	doc.assigned_to = assigned_to
	doc.workflow_state = "Assigned"
	doc.followup_due_on = followup_due

	# Create native assignment (also creates the ToDo)
	todo_name = _create_native_assignment(
		doctype=doctype,
		name=docname,
		user=assigned_to,
		description=f"Follow up inquiry {docname}",
		due_date=followup_due,
		color=(settings.todo_color or "blue"),
	)

	# SLA + save
	update_sla_status(doc)
	doc.save(ignore_permissions=True)

	# Timeline + realtime
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

	# Remove previous assignment (closes its ToDo)
	try:
		remove_assignment(doctype=doctype, name=docname, assign_to=doc.assigned_to)
	except Exception:
		# fallback: close any leftover ToDo rows defensively
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
	notify_user(doc.assigned_to, "🔁 Inquiry reassigned. You are no longer responsible.", doc)

	# Ensure first_contact_due_on exists for legacy rows
	if not getattr(doc, "first_contact_due_on", None):
		base = getdate(doc.submitted_at) if getattr(doc, "submitted_at", None) else getdate(nowdate())
		doc.first_contact_due_on = add_days(base, settings.first_contact_sla_days or 7)

	# Compute new follow-up due
	followup_due = add_days(nowdate(), settings.followup_sla_days or 1)

	# Update Inquiry
	doc.db_set("assigned_to", new_assigned_to)
	doc.db_set("workflow_state", "Assigned")
	doc.db_set("followup_due_on", followup_due)
	doc.assigned_to = new_assigned_to
	doc.workflow_state = "Assigned"
	doc.followup_due_on = followup_due

	# Create native assignment for the new assignee
	new_todo = _create_native_assignment(
		doctype=doctype,
		name=docname,
		user=new_assigned_to,
		description=f"Follow up inquiry {docname} (reassigned)",
		due_date=followup_due,
		color=(settings.todo_color or "blue"),
	)

	# SLA + save
	update_sla_status(doc)
	doc.save(ignore_permissions=True)

	# Timeline + realtime
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