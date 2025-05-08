# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

import os
import frappe
from frappe.utils.nestedset import NestedSet
from frappe.utils import getdate
from frappe import _, scrub
from frappe.utils import getdate, validate_email_address, today, add_years, cstr
from frappe.permissions import add_user_permission, remove_user_permission, has_permission, get_doc_permissions
from frappe.contacts.address_and_contact import load_address_and_contact

from ifitwala_ed.utilities.transaction_base import delete_events

class EmployeeUserDisabledError(frappe.ValidationError): pass
class InactiveEmployeeStatusError(frappe.ValidationError): pass

class Employee(NestedSet):
	nsm_parent_field = 'reports_to'

	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		from ifitwala_ed.controllers.status_updater import validate_status
		validate_status(self.status, ["Active", "Temporary Leave", "Left", "Suspended"])

		self.employee = self.name
		self.employee_full_name = " ".join(filter(None, [self.employee_first_name, self.employee_middle_name, self.employee_last_name]))
		self.validate_date()
		self.validate_email()
		self.validate_status()
		self.validate_reports_to()
		self.validate_preferred_email()
		self.update_user_default_school()

		if self.user_id:
			self.validate_user_details()
		else:
			existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
			if existing_user_id:
				user = frappe.get_doc("User", existing_user_id)
				validate_employee_role(user, ignore_emp_check = True)
				user.save(ignore_permissions=True)
				remove_user_permission("Employee", self.name, existing_user_id)

	def after_rename(self, old, new, merge):
		self.db_set("employee", new)

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_update(self):
		self.update_nsm_model()
		if self.user_id:
			self.update_user()
			self.update_user_permissions()
		self.reset_employee_emails_cache()
		self.update_approver_role()

	def on_trash(self):
		self.update_nsm_model()
		delete_events(self.doctype, self.name)

	# call on validate.  Broad check to make sure birtdhdate, joining date are making sense.
	def validate_date(self):
		if self.employee_date_of_birth and getdate(self.employee_date_of_birth) > getdate(today()):
			frappe.throw(_("Date of Birth cannot be after today.")) 
		if self.employee_date_of_birth and getdate(self.employee_date_of_birth) > getdate(add_years(today(), - 16)):
			frappe.throw(_("Maybe you are too young to be an employee of this school!"))	
		if self.employee_date_of_birth and self.date_of_joining and getdate(self.employee_date_of_birth) >= getdate(self.date_of_joining):
			frappe.throw(_("Date of Joining must be after Date of Birth"))
		if self.notice_date and self.relieving_date and getdate(self.relieving_date) <  getdate(self.notice_date):
			frappe.throw(_("Date of Notice {0} should be before Relieving Date {1}. Please adjust dates.").format(getdate(self.notice_date), getdate(self.relieving_date)))
		if self.relieving_date and self.date_of_joining and getdate(self.relieving_date) <  getdate(self.date_of_joining):
			frappe.throw(_("Date of Joining {0} should be before Relieving Date {1}. Please adjust dates.").format(getdate(self.date_of_joining), getdate(self.relieving_date)))

	# call on validate. Broad check to make sure the email address has an appropriate format.
	def validate_email(self):
		if self.employee_professional_email:
			validate_email_address(self.employee_professional_email, True)
		if self.employee_personal_email:
			validate_email_address(self.employee_personal_email, True)

	# call on validate.  If status is set to left, then need to put relieving date.
	# also you can not be set as left if there are people reporting to you.
	def validate_status(self):
		if self.status == 'Left':
			reports_to = frappe.db.get_all("Employee", filters={"reports_to": self.name, "status": "Active"}, fields=["name","employee_full_name"])
			if reports_to:
				link_to_employees = [frappe.utils.get_link_to_form("Employee", employee.name, label=employee.employee_full_name) for employee in reports_to]
				message = _("The following employees are currently still reporting to {0}:").format(frappe.bold(self.employee_full_name))
				message += "<br><br><ul><li>" + "</li><li>".join(link_to_employees)
				message += "</li></ul><br>"
				message += _("Please make sure the employees above report to another Active employee.")
				frappe.throw(message, InactiveEmployeeStatusError, _("Cannot Relieve Employee"))
			if not self.relieving_date:
				frappe.throw(_("Please enter relieving date."))

	# call on validate.  You cannot report to yourself.
	def validate_reports_to(self):
		if self.reports_to == self.name:
			frappe.throw(_("Employee cannot report to her/himself."))

	# call on validate. Check that there is at least one email to use.
	def validate_preferred_email(self):
		"""
		Validates the preferred contact email for an employee.

		This method checks if the preferred contact email is set and ensures that the corresponding
		field (either "User ID" or the scrubbed version of the preferred contact email) is filled.
		If the required field is not filled, it displays a message prompting the user to enter the
		preferred contact email.

		Raises:
			frappe.msgprint: If the required field for the preferred contact email is not filled.
		"""
		if self.preferred_contact_email:
			if self.preferred_contact_email == "User ID" and not self.get("user_id"):
				frappe.msgprint(_("Please enter {0}").format(self.preferred_contact_email))
			elif self.preferred_contact_email and not self.get("employee_" + scrub(self.preferred_contact_email)):
				frappe.msgprint(_("Please enter {0}").format(self.preferred_contact_email))	
				
	def update_user_default_school(self):
		"""Set or update the default school for the user linked to this employee."""
		if not self.user_id: 
			return  # No linked user to update

		# Get the current default school for this user
		current_default = frappe.defaults.get_user_default("school", self.user_id)

		# Set the default if missing and a school is already filled
		if not current_default and self.school: 
			frappe.defaults.set_user_default("school", self.school, self.user_id) 
			frappe.clear_user_cache(self.user_id) 
			frappe.msgprint(_("Default school set to {0} for user {1} (first-time setup).").format(self.school, self.user_id)) 
			return

		# Handle clearing the default if the field is empty
		if not self.school:
			frappe.defaults.clear_default("school", self.user_id)
			frappe.clear_user_cache(self.user_id)
			frappe.msgprint(_("Default school cleared for user {0}.").format(self.user_id))
			return

		# Update default school only if it has changed
		if self.school != current_default:
			frappe.defaults.set_user_default("school", self.school, self.user_id)
			frappe.clear_user_cache(self.user_id)
			frappe.msgprint(_("Default school set to {0} for user {1}.").format(self.school, self.user_id))

	# call on validate.  Check that if there is already a user, a few more checks to do.
	def validate_user_details(self):
		if self.user_id: 
			data = frappe.db.get_value('User', self.user_id, ['enabled', 'user_image'], as_dict=1)

		self.validate_for_enabled_user_id(data.get("enabled", 0))
		self.validate_duplicate_user_id()

	# call on validate through validate_user_details().
	# If employee is referring to a user, that user has to be active.
	def validate_for_enabled_user_id(self, enabled):
		if not self.status == 'Active':
			return
		if enabled is None:
			frappe.throw(_("User {0} does not exist").format(self.user_id))
		if enabled == 0:
			frappe.throw(_("User {0} is disabled").format(self.user_id), EmployeeUserDisabledError)

	# call on validate through validate_user_details().
	def validate_duplicate_user_id(self): 
		Employee = frappe.qb.DocType("Employee")
		employee = (
			frappe.qb.from_("Employee")
			.select(Employee.name)
			.where(
				(Employee.user_id == self.user_id) 
				& (Employee.status == "Active")
				& (Employee.name != self.name)
			)
		).run()
		if employee:
			frappe.throw(_("User {0} is already assigned to Employee {1}").format(self.user_id, employee[0][0]), frappe.DuplicateEntryError)


	# to update the user fields when employee fields are changing
	def update_user(self):
			user = frappe.get_doc("User", self.user_id)
			user.flags.ignore_permissions = True

			if "Employee" not in user.get("roles"):
					user.append_roles("Employee")

			user.first_name = self.employee_first_name
			user.last_name = self.employee_last_name
			user.full_name = self.employee_full_name

			if self.employee_date_of_birth:
					user.birth_date = self.employee_date_of_birth

			# ---- image sync -------------------------------------------------------
			img_path = self.employee_image
			if img_path:
					abs_path = frappe.utils.get_site_path("public", img_path.lstrip("/"))

					# Skip (and log) if the file has been moved but the field wasn’t updated yet
					if not os.path.exists(abs_path):
							frappe.log_error(
									title=_("Missing file on disk during update_user"),
									message=f"{abs_path} does not exist for Employee {self.name}"
							)
							img_path = None                # prevents 500 in attach_files_to_document

			if img_path:                           # only run if the path is valid
					if user.user_image != img_path: 
						user.user_image = img_path

					# keep / update the File row attached to User.user_image
					existing = frappe.db.exists(
							"File",
							{
									"attached_to_doctype": "User",
									"attached_to_name":   self.user_id,
									"attached_to_field":  "user_image",
							}
					)

					if not existing:
							frappe.get_doc({
									"doctype": "File",
									"file_url":           img_path,
									"attached_to_doctype":"User",
									"attached_to_name":   self.user_id,
									"attached_to_field":  "user_image",
							}).insert(ignore_permissions=True, ignore_if_duplicate=True)
					else:                               
						frappe.db.set_value(
								"File", existing, "file_url", img_path, update_modified=False
						)


			user.save()


	def update_user_permissions(self):
		if not self.create_user_permission: 
			return
		if not has_permission('User Permission', ptype='write', raise_exception=False): 
			return

		employee_user_permission_exists = frappe.db.exists(
			"User Permission", 
			{
				"allow": 'Employee',
				"for_value": self.name,
				"user": self.user_id
			}
		)

		if employee_user_permission_exists: 
			return

		add_user_permission("Employee", self.name, self.user_id)
		add_user_permission("Organization", self.organization, self.user_id)

	def reset_employee_emails_cache(self):
		prev_doc = self.get_doc_before_save() or {}
		cell_number = cstr(self.get("employee_mobile_phone"))
		prev_number = cstr(prev_doc.get("employee_mobile_phone"))
		if (cell_number != prev_number or self.get("user_id") != prev_doc.get("user_id")):
			frappe.cache().hdel("employees_with_number", cell_number)
			frappe.cache().hdel("employees_with_number", prev_number)

	def update_approver_role(self):
		if self.leave_approver:
			user = frappe.get_doc("User", self.leave_approver)
			user.flags.ignore_permissions = True
			user.add_roles("Leave Approver")

		if self.expense_approver:
			user = frappe.get_doc("User", self.expense_approver)
			user.flags.ignore_permissions = True
			user.add_roles("Expense Approver")



@frappe.whitelist()
def create_user(employee, user = None, email=None):
	emp = frappe.get_doc("Employee", employee)
	privacy = frappe.get_single("Privacy Settings")
	birth_date = None
	phone = None
	if emp.employee_date_of_birth and privacy.dob_to_user==1:
		birth_date = emp.employee_date_of_birth
	if emp.employee_mobile_phone and privacy.mobile_to_user==1:
		phone = emp.employee_mobile_phone

	user = frappe.new_doc("User")
	user.update({
		"name": emp.employee_full_name,
		"email": emp.employee_professional_email,
		"enabled": 1,
		"first_name": emp.employee_first_name,
		"middle_name": emp.employee_middle_name,
		"last_name": emp.employee_last_name,
		"gender": emp.employee_gender,
		"birth_date": birth_date,
		"mobile_no": phone
	})

	user.insert() 
	emp.user_id = user.name 
	emp.save(ignore_permissions=True)
	
	return user.name

@frappe.whitelist()
def get_children(doctype, parent=None, organization=None, is_root=False, is_tree=False):
	filters = [["status", "=", "Active"]]
	if organization and organization != "All Organizations":
		filters.append(["organization", "=", organization])

	fields = ["name as value", "employee_full_name as title"]

	if is_root:
		parent = ""
	if parent and organization and parent != organization:
		filters.append(["reports_to", "=", parent])
	else:
		filters.append(["reports_to", "=", ""])

	employees = frappe.get_list(doctype, fields=fields, filters=filters, order_by="name")

	for employee in employees:
		is_expandable = frappe.get_all(doctype, filters=[["reports_to", "=", employee.get("value")]])
		employee.expandable = 1 if is_expandable else 0

	return employees


def on_doctype_update():
	frappe.db.add_index("Employee", ["lft", "rgt"])

def validate_employee_role(doc, method=None, ignore_emp_check=False):
	# called via User hook
	if not ignore_emp_check:
		if frappe.db.get_value("Employee", {"user_id":doc.name}):
			return

	user_roles =  [d.role for d in doc.get("roles")]
	if "Employee" in user_roles: 
		frappe.msgprint(_("User {0}: Removed Employee role as there is no mapped employee.").format(doc.name))
		doc.get("roles").remove(doc.get("roles", {"role": "Employee"})[0])

	if "Employee Self Service" in user_roles:
		frappe.msgprint(_("User {0}: Removed Employee Self Service role as there is no mapped employee.").format(doc.name))
		doc.get("roles").remove(doc.get("roles", {"role": "Employee Self Service"})[0])


def update_user_permissions(doc, method):
	# called via User hook
	if "Employee" in [d.role for d in doc.get("roles")]:
		if not has_permission('User Permission', ptype='write', raise_exception=False): return
		employee = frappe.get_doc("Employee", {"user_id": doc.name})
		employee.update_user_permissions()

def has_user_permission_for_employee(user_name, employee_name):
	return frappe.db.exists(
		{
			"doctype": "User Permission",
			"user": user_name,
			"allow": "Employee",
			"for_value": employee_name,
		}
	)


def has_upload_permission(doc, ptype='read', user=None):
	if not user:
		user = frappe.session.user
	if get_doc_permissions(doc, user=user, ptype=ptype).get(ptype):
		return True
	return doc.user_id == user
