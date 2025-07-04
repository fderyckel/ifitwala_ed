# Copyright (c) 2025, Francois de Ryckel and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import add_days, nowdate, now
from frappe.utils import now_datetime, get_datetime, getdate

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
	doc_types = ["Inquiry", "Registration of Interest"]
	now = now_datetime()
	today = get_datetime(now).date()

	# Get all admission managers only once
	admission_managers = frappe.db.get_values(
		"Has Role",
		{"role": "Admission Manager"},
		"parent"
	)
	manager_usernames = [u[0] for u in admission_managers]

	for doctype in doc_types:
		entries = frappe.get_all(doctype,
			filters={
				"workflow_state": "Assigned",
				"docstatus": 0,
				"first_contact_deadline": ["<=", now]
			},
			fields=["name", "assigned_to", "first_contact_deadline"]
		)

		for entry in entries:
			assignee = entry.assigned_to
			if not assignee:
				continue

			due = get_datetime(entry.first_contact_deadline).date()
			days_overdue = (today - due).days

			if days_overdue == 0:
				message = "⚠️ First Contact deadline reached today."
			else:
				message = f"🔴 First Contact overdue by {days_overdue} day(s)."

			# Notify assigned user
			notify_user(assignee, message, frappe._dict({
				"name": entry.name,
				"doctype": doctype
			}))

			# Notify admission managers
			for user in manager_usernames:
				notify_user(user, message, frappe._dict({
					"name": entry.name,
					"doctype": doctype
				}))

			# Add timeline comment (1 call to get_doc)
			doc = frappe.get_doc(doctype, entry.name)
			doc.add_comment("Comment", text=message)
			doc.save(ignore_permissions=True)

def notify_user(user, message, doc):
	frappe.publish_realtime(
		event='inbox_notification',
		message={
			'type': 'Alert',
			'subject': f"SLA Alert: {doc.name}",
			'message': message,
			'reference_doctype': doc.doctype,
			'reference_name': doc.name
		},
		user=user
	)

def get_admission_deadline_days():
	settings = frappe.get_single("Admission Settings")
	return (
		settings.default_follow_up_days or 1,
		settings.default_first_follow_up_days or 7
	)

def set_inquiry_deadlines(doc):
	if not doc.follow_up_deadline or not doc.first_contact_deadline:
		follow_up_days, first_contact_days = get_admission_deadline_days()
		now = now_datetime()
		if not doc.follow_up_deadline:
			doc.follow_up_deadline = add_days(now, follow_up_days)
		if not doc.first_contact_deadline:
			doc.first_contact_deadline = add_days(now, first_contact_days)

def update_sla_status(doc):
	today = getdate()
	if not doc.first_contact_deadline:
		doc.sla_status = "✅ On Track"
		return

	fc_date = getdate(doc.first_contact_deadline)
	if fc_date < today:
		doc.sla_status = "🔴 Overdue"
	elif fc_date == today:
		doc.sla_status = "🟡 Due Today"
	else:
		doc.sla_status = "⚪ Upcoming"

@frappe.whitelist()
def assign_inquiry(doctype, docname, assigned_to):
	doc = frappe.get_doc(doctype, docname)

	# Validate user with role 'Admission Officer'
	if not frappe.db.exists("Has Role", {"parent": assigned_to, "role": "Admission Officer"}): 
		frappe.throw(f"{assigned_to} must be an active user with the 'Admission Officer' role.")

	# Prevent assignment if already assigned
	if doc.assigned_to:
		frappe.throw(_("{0} is already assigned to this inquiry. Please use the Reassign button instead.").format(doc.assigned_to))		

	# Load Admission Settings
	settings = frappe.get_cached_doc("Admission Settings")

	# Update inquiry fields efficiently
	doc.db_set("assigned_to", assigned_to)
	doc.db_set("workflow_state", "Assigned")
	doc.db_set("first_contact_deadline", add_days(nowdate(), settings.default_follow_up_days or 1))
	doc.db_set("follow_up_deadline", add_days(nowdate(), settings.default_first_follow_up_days or 7))

		# Set fields and save
	doc.assigned_to = assigned_to
	doc.workflow_state = "Assigned"
	doc.first_contact_deadline = add_days(nowdate(), settings.default_follow_up_days or 1)
	doc.follow_up_deadline = add_days(nowdate(), settings.default_first_follow_up_days or 7)
	doc.save(ignore_permissions=True)

	# Create ToDo
	todo = frappe.new_doc("ToDo")
	todo.reference_type = doctype
	todo.reference_name = docname
	todo.allocated_to = assigned_to
	todo.description = f"Follow up inquiry {docname}"
	todo.date = add_days(nowdate(), settings.default_follow_up_days or 1)
	todo.assigned_by = frappe.session.user
	todo.insert(ignore_permissions=True)

	# Add timeline comment
	doc.add_comment(
		"Comment",
		text=f"Assigned to <b>{assigned_to}</b> by <b>{frappe.session.user}</b> on {frappe.utils.formatdate(now())}"
	)

	return {"assigned_to": assigned_to, "todo": todo.name}

@frappe.whitelist()
@frappe.whitelist()
def reassign_inquiry(doctype, docname, new_assigned_to):
	doc = frappe.get_doc(doctype, docname)

	# Check if inquiry is currently assigned
	if not doc.assigned_to:
		frappe.throw("This inquiry is not currently assigned. Please use the Assign button instead.")

	if doc.assigned_to == new_assigned_to:
		frappe.throw("This inquiry is already assigned to this user.")

	# Validate new user
	if not frappe.db.exists("Has Role", {"parent": new_assigned_to, "role": "Admission Officer"}): 
		frappe.throw(f"{new_assigned_to} must be an active user with the 'Admission Officer' role.")

	# Complete previous ToDo (if any)
	todo = frappe.get_all("ToDo", filters={
		"reference_type": doctype,
		"reference_name": docname,
		"status": "Open"
	}, limit=1)

	if todo:
		todo_doc = frappe.get_doc("ToDo", todo[0].name)
		todo_doc.status = "Completed"
		todo_doc.save(ignore_permissions=True)

		doc.add_comment("Comment", text=frappe._(
			f"Previous ToDo <b>{todo_doc.name}</b> marked as completed during reassignment to <b>{new_assigned_to}</b> by <b>{frappe.session.user}</b>."
		))

	# Create new ToDo
	todo_doc = frappe.new_doc("ToDo")
	todo_doc.reference_type = doctype
	todo_doc.reference_name = docname
	todo_doc.allocated_to = new_assigned_to
	todo_doc.description = f"Follow up inquiry {docname} (reassigned)"
	todo_doc.date = add_days(nowdate(), frappe.get_cached_value("Admission Settings", None, "default_follow_up_days") or 1)
	todo_doc.assigned_by = frappe.session.user
	todo_doc.insert(ignore_permissions=True)

	# Update Inquiry assignment and deadlines
	doc.db_set("assigned_to", new_assigned_to)
	doc.db_set("workflow_state", "Assigned")
	doc.db_set("first_contact_deadline", add_days(nowdate(), frappe.get_cached_value("Admission Settings", None, "default_follow_up_days") or 1))
	doc.db_set("follow_up_deadline", add_days(nowdate(), frappe.get_cached_value("Admission Settings", None, "default_first_follow_up_days") or 7))

	# Add system comment
	doc.add_comment(
		"Comment",
		text=frappe._(
			f"Reassigned to <b>{new_assigned_to}</b> by <b>{frappe.session.user}</b> on {frappe.utils.formatdate(now())}."
		)
	)

	return {"reassigned_to": new_assigned_to, "todo": todo_doc.name}



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