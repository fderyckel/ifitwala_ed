# Copyright (c) 2025, Francois de Ryckel and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import add_days, nowdate, now

def notify_admission_manager(doc):
  # Ensure this only triggers on new webform submission
  if frappe.flags.in_web_form and doc.workflow_state == "New Inquiry":
    users = frappe.get_all("User", filters={
      "roles.role": "Admission Manager",
      "enabled": 1
    }, distinct=True, pluck="name")

    for user in users:
      frappe.publish_realtime(
        event='eval_js',
        message={"code": f'frappe.show_alert({{"message": "New Inquiry Submitted: {doc.name}", "indicator": "blue"}});'},
        user=user
      )
      


@frappe.whitelist()
def assign_inquiry(doctype, docname, assigned_to):
	doc = frappe.get_doc(doctype, docname)

	# Validate user with role 'Admission Officer'
	admission_officers = frappe.get_users_with_role("Admission Officer")
	if assigned_to not in admission_officers:
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
	todo.date = add_days(nowdate(), settings.assignment_todo_due_days or 1)
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
