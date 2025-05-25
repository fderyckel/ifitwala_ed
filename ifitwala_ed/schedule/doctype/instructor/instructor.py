# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.user import add_role

class Instructor(Document):

	def autoname(self):
			full_name = frappe.db.get_value("Employee", self.employee, "employee_full_name")
			if not full_name:
					frappe.throw(_("Cannot set Instructor name without employee full name."))
			self.name = full_name

	def onload(self):
		self.load_groups()

	def validate(self):
		self.validate_duplicate_employee()
		user_id = frappe.db.get_value("Employee", self.employee, "user_id")
		if not user_id:
			frappe.throw(_("Linked Employee must have a User ID."))

		self.user_id = user_id

	def after_insert(self):
		add_role(self.user_id, "Instructor")

	def on_update(self):
		if self.status == "Inactive":
			user = frappe.get_doc("User", self.user_id)
			user.remove_roles("Instructor")
		if self.status == "Active":
			user = frappe.get_doc("User", self.user_id)
			add_role(self.user_id, "Instructor")

	def validate_duplicate_employee(self):
		if self.employee and frappe.db.get_value("Instructor", {'employee': self.employee, 'name': ['!=', self.name]}, 'name'):
			frappe.throw(_("Employee ID is linked with another instructor."))

	def load_groups(self):
		self.instructor_log = []

		# Step 1: Get Student Group Instructor links
		group_links = frappe.db.get_values(
			"Student Group Instructor",
			filters={"instructor": self.name},
			fieldname=["parent", "designation"],
			as_dict=True
		)

		if not group_links:
			return

		# Step 2: Batch fetch Student Group info
		student_group_names = [g["parent"] for g in group_links]
		group_records = frappe.db.get_values(
			"Student Group",
			filters={"name": ["in", student_group_names]},
			fieldname=["name", "academic_year", "academic", "course"],
			as_dict=True
		)

		group_lookup = {g["name"]: g for g in group_records}

		# Step 3: Append to child table
		for link in group_links:
			group_doc = group_lookup.get(link["parent"])
			if group_doc:
				self.append("instructor_log", {
					"academic_year": group_doc["academic_year"],
					"academic": group_doc["academic"],
					"designation": link["designation"],
					"student_group": group_doc["name"],
					"course": group_doc["course"]
				})