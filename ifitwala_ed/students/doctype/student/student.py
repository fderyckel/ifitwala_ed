# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today, get_link_to_form, validate_email_address
from frappe.model.document import Document
from frappe.desk.form.linked_with import get_linked_doctypes
from frappe.contacts.address_and_contact import load_address_and_contact


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
		self.update_student_enabled_status()
		self.ensure_contact_links_to_student()
		self.rename_student_image()


	# create student as website user
	def create_student_user(self):
		if not frappe.db.exists("User", self.student_email):
			try:
				student_user = frappe.get_doc({
					"doctype": "User",
					"enabled": 1,
					"first_name": self.student_first_name,
					"middle_name": self.student_middle_name,
					"last_name": self.student_last_name,
					"email": self.student_email,
					"username": self.student_email,
					"gender": self.student_gender,
					#"language": self.student_first_language,  # this create issue because our language is not the same as the frappe language.
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

	############################################
	###### Update methods ###### 
	def update_student_enabled_status(self): 
		patient = frappe.db.get_value("Student Patient", {"student":self.name}, "name") 
		if self.enabled == 0: 
			frappe.db.set_value("Student Patient", patient, "status", "Disabled") 
		else: 
			frappe.db.set_value("Student Patient", patient, "status", "Active") 
		
	def ensure_contact_links_to_student(self):
		if not self.student_email: 
			return

    # Check if User exists
		if not frappe.db.exists("User", self.student_email): 
			return 
		
		contact_name = frappe.db.get_value("Contact", {"user": self.student_email}, "name") 
		if not contact_name: 
			return 
		
		contact = frappe.get_doc("Contact", contact_name) 
		# Check if the Student is already linked in the Contact's dynamic links 
		existing_links = [link.link_name for link in contact.links] 
		
		if self.name not in existing_links: 
			contact.append("links", {
        "link_doctype": "Student",
        "link_name": self.name
      }) 
			contact.save(ignore_permissions=True) 
			frappe.msgprint(f"Linked Contact <b>{contact.name}</b> to Student <b>{self.name}</b>.")


	def rename_student_image(self): 
		# Only proceed if there's a student_image
		if not self.student_image: 
			return 
			 
		try: 
			student_id = self.name
			current_file_name = os.path.basename(self.student_image) 
			
			# Check if it already has "STU-XXXX_XXXXXX.jpg" format
			if (current_file_name.startswith(student_id + "_")
 				and len(current_file_name.split("_")[1].split(".")[0]) == 6
 				and current_file_name.split(".")[1].lower() in ["jpg", "jpeg", "png", "gif"]): 
				return 
			
			file_extension = os.path.splitext(self.student_image)[1] 
			random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
			expected_file_name = f"{student_id}_{random_suffix}{file_extension}"
			
			student_folder_fm_path = "Home/student"
			expected_file_path = os.path.join(student_folder_fm_path, expected_file_name)
 
 			# Check if a file with the new expected name already exists
			if frappe.db.exists("File", {"file_url": f"/files/{expected_file_path}"}):
				frappe.log_error(
					title=_("Image Rename Skipped"),
					message=_("Image {0} already exists for student {1}").format(expected_file_name, student_id),
 				)
				return
 
 			# Check if the original file doc exists
			file_name = frappe.db.get_value("File",
				{"file_url": self.student_image, "attached_to_doctype": "Student", "attached_to_name": self.name},
 				"name"
			)
			
			if not file_name: 
				frappe.log_error(
 					title=_("Missing File Doc"),
 					message=_("No File doc found for {0}, attached_to=Student {1}")
 						.format(self.student_image, self.name),
 				)
				return
			
			file_doc = frappe.get_doc("File", file_name)
 
 			# Ensure the "student" folder exists
			if not frappe.db.exists("File", {"file_name": "student", "folder": "Home"}): 
				student_folder = frappe.get_doc({
 					"doctype": "File",
 					"file_name": "student",
 					"is_folder": 1,
 					"folder": "Home"
				})
				student_folder.insert()
 
 			# Rename the file on disk
			new_file_path = os.path.join(get_files_path(), "student", expected_file_name)
			old_file_path = os.path.join(get_files_path(), file_doc.file_name)
			
			if os.path.exists(old_file_path):
				os.rename(old_file_path, new_file_path)
				file_doc.file_name = expected_file_name
				file_doc.file_url = f"/files/student/{expected_file_name}"
				file_doc.folder = "Home/student"
				file_doc.is_private = 0
				file_doc.save()
			else:
				frappe.throw(_("Original file not found: {0}").format(old_file_path))
 
 			# Update doc.student_image to reflect new URL
			self.student_image = file_doc.file_url
 			# Don't call self.save() or self.db_update() here—on_update is already saving
			
			self.db_update()
			
			frappe.msgprint(_("Image renamed to {0} and moved to /files/student/").format(expected_file_name))
			
		except Exception as e:
			frappe.log_error(title=_("Student Image Error"),message=f"Error handling student image for {self.name}: {e}")
			frappe.msgprint(_("Error handling student image for {0}: {1}").format(self.name, e))


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
			