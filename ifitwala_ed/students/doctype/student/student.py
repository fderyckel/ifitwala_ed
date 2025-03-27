# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today, get_link_to_form, validate_email_address
from frappe.model.document import Document
from frappe.desk.form.linked_with import get_linked_doctypes
from frappe.contacts.address_and_contact import load_address_and_contact
from ifitwala_ed.utilities.student_utils import rename_and_move_student_image


class Student(Document):
	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		self.student_full_name = " ".join(filter(None, [self.student_first_name, self.student_middle_name, self.student_last_name]))
		self.validate_email()

		if frappe.get_value("Student", self.name, "student_full_name") != self.student_full_name:
			self.update_student_name_in_linked_doctype()

		if self.student_date_of_birth and getdate(self.student_date_of_birth) >= getdate(today()):
			frappe.throw(_("Check again student's birth date.  It cannot be after today."))

		if self.student_date_of_birth and getdate(self.student_date_of_birth) >= getdate(self.student_joining_date):
			frappe.throw(_("Check again student's birth date and or joining date. Birth date cannot be after joining date."))

		if self.student_joining_date and self.student_exit_date and getdate(self.student_joining_date) > getdate(self.student_exit_date):
			frappe.throw(_("Check again the exit date. The joining date has to be earlier than the exit date."))


	def validate_email(self):
		if self.student_email:
			validate_email_address(self.student_email, True)


	def update_student_name_in_linked_doctype(self):
		linked_doctypes = get_linked_doctypes("Student")
		for d in linked_doctypes:
			meta = frappe.get_meta(d)
			if not meta.issingle:
				if "student_name" in [f.fieldname for f in meta.fields]:
					frappe.db.sql("""UPDATE `tab{0}` set student_name = %s where {1} = %s"""
						 .format(d, linked_doctypes[d]["fieldname"][0]),(self.student_full_name, self.name))

				if "child_doctype" in linked_doctypes[d].keys() and "student_name" in \
					[f.fieldname for f in frappe.get_meta(linked_doctypes[d]["child_doctype"]).fields]:
					frappe.db.sql("""UPDATE `tab{0}` set student_name = %s where {1} = %s"""
						  .format(linked_doctypes[d]["child_doctype"], linked_doctypes[d]["fieldname"][0]),(self.student_full_name, self.name))

	def after_insert(self):
		self.create_student_user()
		self.create_student_patient()

	def on_update(self):
		self.update_student_user()
		self.update_student_patient()
		self.update_links()
		
		if self.student_image: 
			frappe.enqueue(
				rename_and_move_student_image, 
				student_docname=self.name,
				current_image_url=self.student_image,
				queue='default', 
				timeout=300
      )	

	# create student as website user
	def create_student_user(self):
		if not frappe.db.exists("User", self.student_email):
			try:
				student_user = frappe.get_doc({
					"doctype": "User",
					"enabled": 1,
					"first_name": self.student_first_name,
					"last_name": self.student_last_name,
					"email": self.student_email,
					"username": self.student_email,
					"gender": self.student_gender,
					#"language": self.student_first_language,  # this create issue becuase language is not the same as the frappe language.
					"send_welcome_email": 0,  # Set to 0 to disable welcome email during import
					"user_type": "Website User"
				})
				student_user.flags.ignore_permissions = True
				student_user.add_roles("Student")
				student_user.save()  
				frappe.msgprint(_("User {0} has been created").format(get_link_to_form("User", self.student_email)))
			except Exception as e:
				frappe.log_error(f"Error creating user for student {self.name}: {e}")
				frappe.msgprint(f"Error creating user for student {self.name}. Check Error Log for details.")

	# Create student as patient
	def create_student_patient(self):
		if not frappe.db.exists("Student Patient", {"student_name": self.student_full_name}):
			student_patient = frappe.get_doc({
				"doctype": "Student Patient",
				"student": self.name
			})
			student_patient.save()
			frappe.msgprint(_("Student Patient {0} linked to this student has been created").format(self.student_full_name))


###### Update methods ######
	# update the student contact card if info in student changes
	def update_links(self): 
		# Fetch the contact name linked to the user (student_email)
		contact_name = frappe.db.get_value("Contact", {"user": self.student_email}, "name")  
		if contact_name: 
			contact_doc = frappe.get_doc("Contact", contact_name) 
			# Ensure the link does not already exist 
			existing_links = [link.link_name for link in contact_doc.links]
		
			if self.name not in existing_links: 
				contact_doc.append("links", {"link_doctype": "Student", "link_name": self.name}) 
				contact_doc.flags.ignore_permissions = True 
				contact_doc.save() 
				frappe.msgprint(_("Contact for {0} updated with student link").format(self.student_full_name)) 
		else:
			frappe.msgprint(_("No Contact found for Student Email: {0}. Ensure a Contact is created.").format(self.student_email)) 

	# will update user main info if the student info change  
	def update_student_user(self): 
		user = frappe.get_doc("User", self.student_email) 
		user.flags.ignore_permissions = True 
		user.first_name = self.student_first_name 
		user.last_name = self.student_last_name 
		user.full_name = self.student_full_name 
		if self.student_gender: 
			user.gender = self.student_gender 
		user.save()

	# disactivate the student patient if the student is disactivated
	def update_student_patient(self):
		patient = frappe.db.get_value("Student Patient", {"student":self.name}, "name")
		if self.enabled == 0:
			frappe.db.set_value("Student Patient", patient, "status", "Disabled")
		else:
			frappe.db.set_value("Student Patient", patient, "status", "Active")

####### From schedule module #######
	def enroll_in_course(self, course_name, program_enrollment, enrollment_date):
		try:
			enrollment = frappe.get_doc({
					"doctype": "Course Enrollment",
					"student": self.name,
					"course": course_name,
					"program_enrollment": program_enrollment,
					"enrollment_date": enrollment_date,
					"status": "Current"
				})
			enrollment.save(ignore_permissions=True)
		except frappe.exceptions.ValidationError:
			enrollment_name = frappe.get_list("Course Enrollment", filters={"student": self.name, "course": course_name, "program_enrollment": program_enrollment})[0].name
			return frappe.get_doc("Course Enrollment", enrollment_name)
		else:
			return enrollment
			
