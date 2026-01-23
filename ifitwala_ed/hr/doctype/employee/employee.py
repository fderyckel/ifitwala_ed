# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

# ifitwala_ed.hr.doctype.employee.employee

import os
import frappe
from frappe.utils.nestedset import NestedSet
from frappe.utils import getdate, today
from frappe import _, scrub
from frappe.utils import validate_email_address, add_years, cstr
from frappe.permissions import get_doc_permissions
from frappe.contacts.address_and_contact import load_address_and_contact
from ifitwala_ed.utilities.file_dispatcher import create_and_classify_file


from ifitwala_ed.utilities.employee_utils import (
	get_user_base_org,
	get_user_base_school,
	get_descendant_organizations,
)

from ifitwala_ed.utilities.school_tree import get_descendant_schools
from ifitwala_ed.utilities.transaction_base import delete_events


class EmployeeUserDisabledError(frappe.ValidationError):
	pass


class InactiveEmployeeStatusError(frappe.ValidationError):
	pass


class Employee(NestedSet):
	nsm_parent_field = "reports_to"

	def onload(self):
		"""
		Load Contact and Address for HR convenience.

		RULE:
		- HR can read Contact + Address
		- HR must NOT require User read permission
		- Therefore we resolve Contact via Employee Dynamic Link only
		"""
		# Resolve Contact linked directly to Employee
		contact_name = frappe.db.get_value(
			"Dynamic Link",
			{
				"link_doctype": "Employee",
				"link_name": self.name,
				"parenttype": "Contact",
			},
			"parent",
		)

		if not contact_name:
			return

		# Attach contact to doc (same shape as load_address_and_contact)
		self._contact = frappe.get_doc("Contact", contact_name)

		# Load addresses linked to this Contact
		addresses = frappe.get_all(
			"Dynamic Link",
			filters={
				"link_doctype": "Contact",
				"link_name": contact_name,
				"parenttype": "Address",
			},
			fields=["parent"],
		)

		self._addresses = [
			frappe.get_doc("Address", a.parent)
			for a in addresses
		]


	def validate(self):
		from ifitwala_ed.controllers.status_updater import validate_status
		validate_status(self.status, ["Active", "Temporary Leave", "Left", "Suspended"])

		self.employee = self.name
		self.employee_full_name = " ".join(filter(None, [
			self.employee_first_name,
			self.employee_middle_name,
			self.employee_last_name,
		]))

		# Pure invariants only (no heavy side-effects)
		self.validate_date()
		self.validate_email()
		self.validate_status()
		self.validate_reports_to()
		self.validate_preferred_email()
		self.validate_employee_history()

		if self.user_id:
			self.validate_user_details()
		else:
			existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
			if existing_user_id:
				user = frappe.get_doc("User", existing_user_id)
				validate_employee_role(user, ignore_emp_check=True)
				user.flags.ignore_permissions = True
				user.save(ignore_permissions=True)


		# Ensure the employee history is sorted before saving
		if self.employee_history:
			self.employee_history.sort(
				key=lambda row: getdate(row.to_date) if row.to_date else getdate("9999-12-31"),
				reverse=True,
			)

	def after_save(self):
		self._classify_employee_image()


	def after_rename(self, old, new, merge):
		self.db_set("employee", new)

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def _reports_to_changed(self):
		prev = self.get_doc_before_save()
		if not prev:
			# New doc insert or unknown state: be safe and update
			return True
		return (prev.reports_to or "") != (self.reports_to or "")

	def on_update(self):
		# ---------------------------------------------------------
		# 1) Structural graph integrity (always allowed)
		# ---------------------------------------------------------
		if self._reports_to_changed():
			self.update_nsm_model()

		self.reset_employee_emails_cache()
		self.sync_employee_history()
		self._sync_staff_calendar()
		self._ensure_primary_contact()
		self._govern_profile_photo()

		# ---------------------------------------------------------
		# 2) Role / authority enforcement (HR-governed, safe)
		# ---------------------------------------------------------
		self._apply_designation_role()
		self._apply_approver_roles()

		# ---------------------------------------------------------
		# 3) User profile sync (STRICTLY gated)
		# ---------------------------------------------------------
		if self.user_id and self._can_sync_user_profile():
			self.update_user()
			self.update_user_default_school()

	def on_trash(self):
		# Keep consistency on delete; guard to avoid unnecessary work
		if self._reports_to_changed():
			self.update_nsm_model()
		delete_events(self.doctype, self.name)

	# call on validate. Broad check to make sure birthdate, joining date are making sense.
	def validate_date(self):
		if self.employee_date_of_birth and getdate(self.employee_date_of_birth) > getdate(today()):
			frappe.throw(_("Date of Birth cannot be after today."))
		if self.employee_date_of_birth and getdate(self.employee_date_of_birth) > getdate(add_years(today(), -16)):
			frappe.throw(_("Maybe you are too young to be an employee of this school!"))
		if self.employee_date_of_birth and self.date_of_joining and getdate(self.employee_date_of_birth) >= getdate(self.date_of_joining):
			frappe.throw(_("Date of Joining must be after Date of Birth"))
		if self.notice_date and self.relieving_date and getdate(self.relieving_date) < getdate(self.notice_date):
			frappe.throw(
				_("Date of Notice {0} should be before Relieving Date {1}. Please adjust dates.")
				.format(getdate(self.notice_date), getdate(self.relieving_date))
			)
		if self.relieving_date and self.date_of_joining and getdate(self.relieving_date) < getdate(self.date_of_joining):
			frappe.throw(
				_("Date of Joining {0} should be before Relieving Date {1}. Please adjust dates.")
				.format(getdate(self.date_of_joining), getdate(self.relieving_date))
			)

	# call on validate. Broad check to make sure the email address has an appropriate format.
	def validate_email(self):
		if self.employee_professional_email:
			validate_email_address(self.employee_professional_email, True)
		if self.employee_personal_email:
			validate_email_address(self.employee_personal_email, True)

	# call on validate. If status is set to left, then need to put relieving date.
	# also you can not be set as left if there are people reporting to you.
	def validate_status(self):
		if self.status == "Left":
			reports_to = frappe.db.get_all(
				"Employee",
				filters={"reports_to": self.name, "status": "Active"},
				fields=["name", "employee_full_name"],
			)
			if reports_to:
				link_to_employees = [
					frappe.utils.get_link_to_form("Employee", employee.name, label=employee.employee_full_name)
					for employee in reports_to
				]
				message = _("The following employees are currently still reporting to {0}:").format(
					frappe.bold(self.employee_full_name)
				)
				message += "<br><br><ul><li>" + "</li><li>".join(link_to_employees)
				message += "</li></ul><br>"
				message += _("Please make sure the employees above report to another Active employee.")
				frappe.throw(message, InactiveEmployeeStatusError, _("Cannot Relieve Employee"))
			if not self.relieving_date:
				frappe.throw(_("Please enter relieving date."))

	# You cannot report to yourself or cross organizations (only parents)
	def validate_reports_to(self):
		# Prevent self-reporting
		if self.reports_to == self.name:
			frappe.throw(_("An Employee cannot report to themselves."))

		# If no reports_to is set, skip validation
		if not self.reports_to or not self.organization:
			return

		# Get the organization of the supervisor (reports_to)
		supervisor_org = frappe.db.get_value("Employee", self.reports_to, "organization")
		if not supervisor_org:
			return  # Skip if the supervisor has no organization (edge case)

		# Allow reporting within the same organization
		if self.organization == supervisor_org:
			return

		# Validate upward hierarchy
		is_parent_org = frappe.db.sql(
			"""
			SELECT 1
			FROM `tabOrganization`
			WHERE name = %s
			AND lft <= (SELECT lft FROM `tabOrganization` WHERE name = %s)
			AND rgt >= (SELECT rgt FROM `tabOrganization` WHERE name = %s)
		""",
			(supervisor_org, self.organization, self.organization),
		)

		if not is_parent_org:
			frappe.throw(
				_("Employee cannot report to a supervisor from a different organization unless it is a parent organization.")
			)

		# Validate downward consistency (no cross-lineage connections)
		# Fetch all direct reports of the current employee
		direct_reports = frappe.db.get_values(
			"Employee",
			filters={"reports_to": self.name},
			fieldname=["name", "organization"],
			as_dict=True,
		)

		# Get the organization lineage of the current employee
		lineage = frappe.db.sql(
			"""
			SELECT name
			FROM `tabOrganization`
			WHERE lft <= (SELECT lft FROM `tabOrganization` WHERE name = %s)
			AND rgt >= (SELECT rgt FROM `tabOrganization` WHERE name = %s)
		""",
			(self.organization, self.organization),
		)

		valid_orgs = {org[0] for org in lineage}

		# Check each direct report for cross-lineage violations
		for report in direct_reports:
			if report["organization"] not in valid_orgs:
				frappe.throw(
					_(
						"Direct report '{0}' (Organization: {1}) cannot belong to an organization outside the hierarchy of '{2}' (Organization: {3})."
					).format(report["name"], report["organization"], self.name, self.organization)
				)

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
			frappe.cache().hdel("user:" + self.user_id, "defaults")
			frappe.msgprint(
				_("Default school set to {0} for user {1} (first-time setup).").format(self.school, self.user_id)
			)
			return

		# Handle clearing the default if the field is empty
		if not self.school:
			if current_default:
				frappe.defaults.clear_default("school", self.user_id)
				frappe.cache().hdel("user:" + self.user_id, "defaults")
				frappe.msgprint(_("Default school cleared for user {0}.").format(self.user_id))
				return

		# Update default school only if it has changed
		if self.school != current_default:
			frappe.defaults.set_user_default("school", self.school, self.user_id)
			frappe.cache().hdel("user:" + self.user_id, "defaults")
			frappe.msgprint(_("Default school set to {0} for user {1}.").format(self.school, self.user_id))

	def validate_employee_history(self):
		"""Validate history rows:
		- from_date required and not before date_of_joining
		- to_date >= from_date (if set)
		- NO overlap ONLY when (designation, organization, school) are the same
		- is_current is derived from dates

		NOTE: employee_history is expected to remain small; O(n²) overlap check is acceptable.
		"""
		if not self.date_of_joining:
			frappe.throw(_("Please set the Employee's Date of Joining before adding Employee History."))

		today_d = getdate(today())
		join_d = getdate(self.date_of_joining)
		history = self.get("employee_history", []) or []

		def key(r):
			return (r.designation or "", r.organization or "", r.school or "")

		def rng(r):
			start = getdate(r.from_date or "0001-01-01")
			end = getdate(r.to_date or "9999-12-31")
			return start, end

		for i, row in enumerate(history):
			# require from_date
			if not row.from_date:
				frappe.throw(_("Please set 'From Date' for row #{0}.").format(i + 1))

			# row.from_date >= joining date
			if getdate(row.from_date) < join_d:
				frappe.throw(
					_("Row #{0}: From Date cannot be before Date of Joining ({1}).")
					.format(i + 1, self.date_of_joining)
				)

			# to_date >= from_date (if set)
			if row.to_date and getdate(row.to_date) < getdate(row.from_date):
				frappe.throw(_("Row #{0}: 'To Date' cannot be before 'From Date'.").format(i + 1))

		# pairwise overlap ONLY for identical (designation, org, school)
		for i, a in enumerate(history):
			ka = key(a)
			a_start, a_end = rng(a)
			for j, b in enumerate(history):
				if i >= j:
					continue
				if key(b) != ka:
					continue
				b_start, b_end = rng(b)
				# intervals intersect?
				if b_start <= a_end and a_start <= b_end:
					frappe.throw(
						_("Overlap detected for '{0}' @ '{1}/{2}' between row #{3} and row #{4}.")
						.format(a.designation or "-", a.organization or "-", a.school or "-", i + 1, j + 1)
					)

		# compute is_current from dates
		for row in history:
			start, end = rng(row)
			row.is_current = 1 if (start <= today_d <= end) else 0

	def sync_employee_history(self):
		"""Auto-maintain history when primary tuple changes.
		- Detect change via previous doc (designation/org/school).
		- Close the latest row for the *previous* tuple to (new_from - 1).
		- Append a new row for the *current* tuple with from_date = today (idempotent).
		- Allow multiple 'current' rows across different tuples; overlap forbids only same tuple.
		"""
		if not self.date_of_joining or not self.designation:
			return

		history = self.get("employee_history", []) or []
		prev = self.get_doc_before_save()

		# Initial seed if no history
		if not history:
			self.append(
				"employee_history",
				{
					"designation": self.designation,
					"organization": self.organization,
					"school": self.school,
					"from_date": self.date_of_joining,
					# is_current will be recomputed in validate()
				},
			)
			return

		# Need previous values to detect a tuple change
		if not prev:
			return

		prev_tuple = (prev.designation, prev.organization, prev.school)
		cur_tuple = (self.designation, self.organization, self.school)

		# no change → nothing to do
		if prev_tuple == cur_tuple:
			return

		# if employee hasn't joined yet, just update the most recent matching row for prev tuple
		if getdate(self.date_of_joining) > getdate(today()):
			# update the last row (assume preparatory history)
			last = history[-1]
			last.designation = self.designation
			last.organization = self.organization
			last.school = self.school
			return

		# Change happened after joining → close previous tuple's latest row and add new one
		new_from = getdate(today())

		# correct close_to to new_from - 1 day
		close_to = getdate(frappe.utils.add_days(new_from, -1))

		# 1) close the latest row for the previous tuple (if open or crossing new_from)
		for row in reversed(history):
			if (row.designation, row.organization, row.school) == prev_tuple:
				# If it's already closed before new_from, leave it
				if not row.to_date or getdate(row.to_date) >= close_to:
					row.to_date = close_to
				break

		# 2) avoid duplicate (same tuple @ same from_date)
		for r in history:
			if (r.designation, r.organization, r.school) == cur_tuple and getdate(r.from_date or "9999-12-31") == new_from:
				return

		# 3) append new row for current tuple starting today
		self.append(
			"employee_history",
			{
				"designation": self.designation,
				"organization": self.organization,
				"school": self.school,
				"from_date": new_from,
				# is_current computed in validate()
			},
		)

		# keep your sorter
		self._sort_employee_history()

	def _sort_employee_history(self):
		history = self.get("employee_history", [])

		current_roles = [row for row in history if not row.to_date]
		past_roles = [row for row in history if row.to_date]

		current_roles.sort(key=lambda row: getdate(row.from_date), reverse=True)
		past_roles.sort(key=lambda row: getdate(row.to_date), reverse=True)

		sorted_history = current_roles + past_roles
		self.set("employee_history", sorted_history)

		for idx, row in enumerate(self.employee_history, start=1):
			row.idx = idx

	# call on validate. Check that if there is already a user, a few more checks to do.
	def validate_user_details(self):
		if not self.user_id:
			return

		data = frappe.db.get_value("User", self.user_id, ["enabled"], as_dict=1)
		if not data:
			frappe.throw(_("User {0} does not exist").format(self.user_id))

		self.validate_for_enabled_user_id(data.get("enabled"))
		self.validate_duplicate_user_id()


	# call on validate through validate_user_details().
	# If employee is referring to a user, that user has to be active.
	def validate_for_enabled_user_id(self, enabled):
		if not self.status == "Active":
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
			frappe.throw(
				_("User {0} is already assigned to Employee {1}").format(self.user_id, employee[0][0]),
				frappe.DuplicateEntryError,
			)

	# to update the user fields when employee fields are changing
	def update_user(self):
		if not self.user_id:
			return

		user = frappe.get_doc("User", self.user_id)
		user.flags.ignore_permissions = True

		# Ensure base role
		if "Employee" not in {r.role for r in user.roles}:
			user.append("roles", {"role": "Employee"})

		user.first_name = self.employee_first_name
		user.last_name = self.employee_last_name
		user.full_name = self.employee_full_name

		if self.employee_date_of_birth:
			user.birth_date = self.employee_date_of_birth

		# ---- image sync -------------------------------------------------------
		img_path = self.employee_image
		if img_path:
			abs_path = frappe.utils.get_site_path("public", img_path.lstrip("/"))
			if not os.path.exists(abs_path):
				frappe.log_error(
					title=_("Missing file on disk during update_user"),
					message=f"{abs_path} does not exist for Employee {self.name}",
				)
				img_path = None

		if img_path and user.user_image != img_path:
			user.user_image = img_path

		user.save(ignore_permissions=True)


	def _sync_staff_calendar(self):
		"""Attach the appropriate Staff Calendar to current_holiday_lis based on employee_group.

		Strategy:
		- If no employee_group or employee not Active → clear current_holiday_lis.
		- Otherwise, pick the Staff Calendar whose employee_group matches,
			and whose period (from_date/to_date) contains today.
		- If multiple match, choose the one with the latest from_date.
		- If none match the date, fall back to the latest by from_date.
		"""
		# Only for active staff
		if self.status != "Active":
			self.current_holiday_lis = None
			return

		if not self.employee_group:
			self.current_holiday_lis = None
			return

		today_d = getdate(today())

		calendars = frappe.get_all(
			"Staff Calendar",
			filters={"employee_group": self.employee_group},
			fields=["name", "from_date", "to_date"],
			order_by="from_date desc",
		)

		if not calendars:
			self.current_holiday_lis = None
			return

		selected = None
		for cal in calendars:
			from_d = getdate(cal.get("from_date")) if cal.get("from_date") else None
			to_d = getdate(cal.get("to_date")) if cal.get("to_date") else None

			if from_d and to_d and from_d <= today_d <= to_d:
				selected = cal["name"]
				break

		if not selected:
			selected = calendars[0]["name"]

		self.current_holiday_lis = selected

	def reset_employee_emails_cache(self):
		prev_doc = self.get_doc_before_save() or {}
		cell_number = cstr(self.get("employee_mobile_phone"))
		prev_number = cstr(prev_doc.get("employee_mobile_phone"))
		if (cell_number != prev_number or self.get("user_id") != prev_doc.get("user_id")):
			frappe.cache().hdel("employees_with_number", cell_number)
			frappe.cache().hdel("employees_with_number", prev_number)

	def _ensure_primary_contact(self):
		"""
		NOTE:
		Employee does NOT own contact/address data.
		Contact is the single source of truth.
		This method only ensures correct graph linking:
		User → Contact → Employee (via Dynamic Link).

		Dependency:
		User creation is expected to auto-create a Contact linked to the User (hook-level behavior).
		"""
		if not self.user_id:
			return

		contact_name = frappe.db.get_value(
			"Dynamic Link",
			{
				"link_doctype": "User",
				"link_name": self.user_id,
				"parenttype": "Contact",
			},
			"parent",
		)

		if not contact_name:
			frappe.log_error(
				title="Employee Contact Link Missing",
				message=f"No Contact found for User {self.user_id}",
			)
			return

		exists = frappe.db.exists(
			"Dynamic Link",
			{
				"parenttype": "Contact",
				"parent": contact_name,
				"link_doctype": "Employee",
				"link_name": self.name,
			},
		)

		if not exists:
			frappe.get_doc(
				{
					"doctype": "Dynamic Link",
					"parenttype": "Contact",
					"parentfield": "links",
					"parent": contact_name,
					"link_doctype": "Employee",
					"link_name": self.name,
				}
			).insert(ignore_permissions=True)

		if not self.empl_primary_contact:
			self.db_set("empl_primary_contact", contact_name, update_modified=False)

	def _can_sync_user_profile(self) -> bool:
		"""
		Only System Manager or the user themself can sync Employee -> User profile fields.
		HR should not be editing other User attributes as a side-effect of editing Employee.
		"""
		if frappe.session.user == "Administrator":
			return True
		if "System Manager" in set(frappe.get_roles()):
			return True
		return bool(self.user_id and self.user_id == frappe.session.user)

	def _can_manage_user_roles(self) -> bool:
		"""
		HR Manager / System Manager can enforce roles programmatically.
		(This does NOT grant generic User write permissions in the UI.)
		"""
		roles = set(frappe.get_roles())
		return bool(roles & {"HR Manager", "System Manager"}) or frappe.session.user == "Administrator"

	def _ensure_user_has_role(self, user: str, role: str):
		"""Add role to user if missing, using ignore_permissions to avoid User doctype access issues."""
		if not user or not role:
			return

		exists = frappe.db.exists("Has Role", {"parent": user, "role": role})
		if exists:
			return

		u = frappe.get_doc("User", user)
		u.flags.ignore_permissions = True
		u.append("roles", {"role": role})
		u.save(ignore_permissions=True)

	def _apply_designation_role(self):
		if not self.user_id or not self.designation:
			return
		if not self._can_manage_user_roles():
			return

		prev = self.get_doc_before_save()
		if prev and prev.designation == self.designation:
			return

		role = frappe.db.get_value("Designation", self.designation, "default_role_profile")
		if role:
			self._ensure_user_has_role(self.user_id, role)

	def _apply_approver_roles(self):
		if not self._can_manage_user_roles():
			return

		prev = self.get_doc_before_save() or {}

		if self.leave_approver and self.leave_approver != prev.get("leave_approver"):
			self._ensure_user_has_role(self.leave_approver, "Leave Approver")

		if self.expense_approver and self.expense_approver != prev.get("expense_approver"):
			self._ensure_user_has_role(self.expense_approver, "Expense Approver")

	# ------------------------------------------------------------------
	# Employee Image Governance
	# ------------------------------------------------------------------
	def _govern_profile_photo(self):
		"""
		Ensure Employee.employee_image is always backed by a governed File.

		Invariant:
		- At most ONE active profile photo per Employee
		- Slot: profile_photo
		- Subject: Employee

		Policy:
		- Public file (is_private=0).
		- Governance is best-effort: if file is not yet on disk, do NOT block save.
			Retry will happen on next save (or later scheduler if added).
		"""
		if not self.employee_image:
			return

		# If the file isn't materialized on disk yet, defer governance (do not block save)
		file_url = (self.employee_image or "").strip()
		if file_url and not file_url.startswith("http"):
			rel_path = file_url.lstrip("/")
			abs_path = frappe.utils.get_site_path(rel_path)
			if not os.path.exists(abs_path):
				frappe.logger().info(
					f"[Employee] Profile photo not on disk yet; governance deferred: employee={self.name} url={file_url}"
				)
				return

		# Resolve File by file_url
		file_name = frappe.db.get_value(
			"File",
			{"file_url": self.employee_image},
			"name",
		)

		if not file_name:
			# Defensive: nothing to govern
			return

		# If already classified as profile_photo, we are done
		existing_classification = frappe.db.get_value(
			"File Classification",
			{
				"file": file_name,
				"primary_subject_type": "Employee",
				"primary_subject_id": self.name,
				"slot": "profile_photo",
			},
			"name",
		)

		if existing_classification:
			return

		# Create governed replacement via dispatcher
		governed_file = create_and_classify_file(
			file_kwargs={
				"file_url": self.employee_image,
				"attached_to_doctype": "Employee",
				"attached_to_name": self.name,
				"is_private": 0,
			},
			classification={
				"primary_subject_type": "Employee",
				"primary_subject_id": self.name,
				"data_class": "administrative",
				"purpose": "profile_photo",
				"retention_policy": "until_employment_end_plus_policy",
				"slot": "profile_photo",
				"organization": self.organization,
				"school": self.school,
			},
		)

		if not governed_file:
			frappe.throw(
				_(
					"Employee profile photo could not be governed. "
					"Upload was blocked to protect data integrity."
				)
			)

		# Update employee_image to governed file
		self.db_set("employee_image", governed_file.file_url)

		# Delete the original ungoverned file
		try:
			frappe.delete_doc("File", file_name, ignore_permissions=True)
		except Exception:
			# Fail-safe: do not block save, but log loudly
			frappe.log_error(
				title="Employee Image Cleanup Failed",
				message=f"Failed to delete ungoverned File {file_name} for Employee {self.name}",
			)


	def _classify_employee_image(self):
		"""
		Classify employee profile image uploaded via Desk.
		Slot-based, idempotent, HR-safe.
		"""

		if not self.employee_image:
			return

		# Fetch File row
		file_name = frappe.db.get_value(
			"File",
			{"file_url": self.employee_image},
			"name",
		)

		if not file_name:
			return

		file_doc = frappe.get_doc("File", file_name)

		# Skip if already classified for this slot + file
		exists = frappe.db.exists(
			"File Classification",
			{
				"file": file_doc.name,
				"primary_subject_type": "Employee",
				"primary_subject_id": self.name,
				"slot": "profile_image",
			},
		)

		if exists:
			return

		from ifitwala_ed.utilities.file_dispatcher import create_and_classify_file

		create_and_classify_file(
			file_doc=file_doc,
			classification={
				"primary_subject_type": "Employee",
				"primary_subject_id": self.name,
				"data_class": "biometric",
				"purpose": "employee_profile_image",
				"slot": "profile_image",
				"organization": self.organization,
				"school": self.school,
				"upload_source": "Desk",
			},
		)



@frappe.whitelist()
def create_user(employee, user=None, email=None):
	# 0) Basic guards
	if not employee:
		frappe.throw(_("Missing Employee"), frappe.ValidationError)

	# 1) Authorize caller
	caller = frappe.session.user
	caller_roles = set(frappe.get_roles(caller))

	# Allow System Manager unconditionally
	is_sysman = "System Manager" in caller_roles

	# Allow HR Manager/HR User only within their org subtree
	if not is_sysman:
		is_hr = bool(caller_roles & {"HR Manager", "HR User"})
		if not is_hr:
			frappe.throw(_("Only HR can create users from Employee."), frappe.PermissionError)

		# Resolve caller's base org
		from ifitwala_ed.utilities.employee_utils import get_user_base_org, get_descendant_organizations
		base_org = get_user_base_org(caller)
		if not base_org:
			frappe.throw(_("Your account is not linked to an Active Employee or has no Organization."), frappe.PermissionError)

		# Target employee must be in caller's org subtree
		target_org = frappe.db.get_value("Employee", employee, "organization")
		allowed_orgs = set(get_descendant_organizations(base_org) or [])
		if target_org not in allowed_orgs:
			frappe.throw(_("You can only create users for Employees in your Organization subtree."), frappe.PermissionError)

	# 2) Load employee (you already enforce form access via PQC/has_permission)
	emp = frappe.get_doc("Employee", employee)

	# 3) Prevent duplicates
	if emp.user_id:
		frappe.throw(_("This Employee already has a User: {0}").format(frappe.bold(emp.user_id)))

	if not emp.employee_professional_email:
		frappe.throw(_("Please set a Professional Email on the Employee before creating a User."))

	existing = frappe.db.exists("User", {"name": emp.employee_professional_email})
	if existing:
		frappe.throw(_("A User with email {0} already exists.").format(frappe.bold(emp.employee_professional_email)))

	# 4) Build the User document (keep your privacy handling)
	privacy = frappe.get_single("Org Setting")
	birth_date = emp.employee_date_of_birth if getattr(privacy, "dob_to_user", 0) == 1 else None
	phone = emp.employee_mobile_phone if getattr(privacy, "mobile_to_user", 0) == 1 else None

	user_doc = frappe.new_doc("User")
	user_doc.flags.ignore_permissions = True
	user_doc.update({
		# NOTE: do NOT force 'name' here; let Frappe name it as the email
		"email": emp.employee_professional_email,
		"enabled": 1,
		"first_name": emp.employee_first_name,
		"middle_name": emp.employee_middle_name,
		"last_name": emp.employee_last_name,
		"gender": emp.employee_gender,
		"birth_date": birth_date,
		"mobile_no": phone,
	})

	user_doc.insert(ignore_permissions=True)

	emp.user_id = user_doc.name
	emp.save(ignore_permissions=True)

	return user_doc.name


@frappe.whitelist()
def get_children(doctype, parent=None, organization=None, is_root=False, is_tree=False):
	# NOTE:
	# - Treeview calls this often; avoid N+1 queries.
	# - We keep the existing "All Organizations" sentinel for compatibility with current JS.

	filters = [["status", "=", "Active"]]

	# Organization filter (compat with current treeview default)
	if organization and organization != "All Organizations":
		filters.append(["organization", "=", organization])

	fields = ["name as value", "employee_full_name as title"]

	# Root resolution
	if is_root:
		parent = ""

	# Children of a node vs top-level nodes
	if parent:
		filters.append(["reports_to", "=", parent])
	else:
		filters.append(["reports_to", "=", ""])

	employees = frappe.get_list(
		doctype,
		fields=fields,
		filters=filters,
		order_by="name",
	)

	# Nothing to expand
	if not employees:
		return employees

	# --- Batch-expandable check (single query) -----------------------------
	names = [e.get("value") for e in employees if e.get("value")]

	# Count children per supervisor among returned names
	# (We only care whether count > 0)
	rows = frappe.db.sql(
		"""
		SELECT reports_to, COUNT(*) AS cnt
		FROM `tabEmployee`
		WHERE status = 'Active'
			AND reports_to IN %(names)s
		GROUP BY reports_to
		""",
		{"names": tuple(names)},
		as_dict=True,
	)

	count_by_reports_to = {r.reports_to: int(r.cnt or 0) for r in (rows or [])}

	for e in employees:
		e.expandable = 1 if count_by_reports_to.get(e.get("value"), 0) > 0 else 0

	return employees



def on_doctype_update():
	frappe.db.add_index("Employee", ["lft", "rgt"])


def validate_employee_role(doc, method=None, ignore_emp_check=False):
	# called via User hook
	if not ignore_emp_check:
		if frappe.db.get_value("Employee", {"user_id": doc.name}):
			return

	user_roles = [d.role for d in doc.get("roles")]
	if "Employee" in user_roles:
		frappe.msgprint(_("User {0}: Removed Employee role as there is no mapped employee.").format(doc.name))
		doc.get("roles").remove(doc.get("roles", {"role": "Employee"})[0])

	if "Employee Self Service" in user_roles:
		frappe.msgprint(_("User {0}: Removed Employee Self Service role as there is no mapped employee.").format(doc.name))
		doc.get("roles").remove(doc.get("roles", {"role": "Employee Self Service"})[0])


def update_user_permissions(doc, method):
	"""No-op: we no longer use Employee User Permissions at all."""
	return


def has_upload_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user
	if get_doc_permissions(doc, user=user, ptype=ptype).get(ptype):
		return True
	return doc.user_id == user


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None

	roles = set(frappe.get_roles(user))

	# HR: scope by Organization subtree
	if roles & {"HR Manager", "HR User"}:
		base_org = get_user_base_org(user)
		if not base_org:
			return None
		orgs = get_descendant_organizations(base_org) or []
		if not orgs:
			return "1=0"
		vals = ", ".join(frappe.db.escape(o) for o in orgs)
		return f"`tabEmployee`.`organization` IN ({vals})"

	# Academic Admin: scope by School subtree
	if "Academic Admin" in roles:
		base_school = get_user_base_school(user)
		if not base_school:
			return None
		schools = get_descendant_schools(base_school) or []
		if not schools:
			return "1=0"
		vals = ", ".join(frappe.db.escape(s) for s in schools)
		return f"`tabEmployee`.`school` IN ({vals})"

	return None


def employee_has_permission(doc, ptype, user):
	# System Manager full access
	if "System Manager" in frappe.get_roles(user):
		return True

	roles = set(frappe.get_roles(user))

	# Read-like checks (list/report/export/print/open)
	if ptype in {"read", "report", "export", "print"}:
		# HR → Organization subtree
		if roles & {"HR Manager", "HR User"}:
			base_org = get_user_base_org(user)
			if not base_org:
				return None
			desc = set(get_descendant_organizations(base_org) or [])
			return doc.organization in desc

		# Academic Admin → School subtree
		if "Academic Admin" in roles:
			base_school = get_user_base_school(user)
			if not base_school:
				return None
			desc = set(get_descendant_schools(base_school) or [])
			return doc.school in desc

	# Others fall back to standard perms
	return None
