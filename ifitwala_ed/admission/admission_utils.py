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

	# Load Admission Settings
	settings = frappe.get_cached_doc("Admission Settings")

	# Update inquiry fields efficiently
	doc.db_set("assigned_to", assigned_to)
	doc.db_set("workflow_state", "Assigned")
	doc.db_set("first_contact_deadline", add_days(nowdate(), settings.default_follow_up_days or 1))
	doc.db_set("follow_up_deadline", add_days(nowdate(), settings.default_first_follow_up_days or 7))

	# Create ToDo
	todo = frappe.new_doc("ToDo")
	todo.reference_type = doctype
	todo.reference_name = docname
	todo.owner = assigned_to
	todo.description = f"Follow up inquiry {docname}"
	todo.date = add_days(nowdate(), settings.default_follow_up_days or 1)
	todo.assigned_by = frappe.session.user
	todo.insert(ignore_permissions=True)

	# Add timeline comment
	doc.add_comment(
		"Comment",
		text=f"Assigned to <b>{assigned_to}</b> by <b>{frappe.session.user}</b> on {frappe.utils.formatdate(now())}"
	)

	# In-app notifications
	if settings.notify_assignee_on_assignment:
		frappe.publish_realtime(
			event="eval_js",
			message={"code": f'frappe.show_alert({{"message": "New inquiry assigned to you: {docname}", "indicator": "green"}});'},
			user=assigned_to
		)

	if settings.notify_manager_on_assignment:
		frappe.publish_realtime(
			event="eval_js",
			message={"code": f'frappe.show_alert({{"message": "Inquiry {docname} assigned to {assigned_to}", "indicator": "blue"}});'},
			user=frappe.session.user
		)

	return {"assigned_to": assigned_to, "todo": todo.name}


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