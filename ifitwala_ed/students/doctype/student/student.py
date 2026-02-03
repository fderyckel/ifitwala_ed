# ifitwala_ed/students/doctype/student/student.py
# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student/student.py

"""
Student DocType — Creation Modes & Invariants
---------------------------------------------

A Student record represents a canonical, operational learner.
Students may be created through THREE explicit, supported pathways:

1) Applicant Promotion (default, steady-state)
   - Created via StudentApplicant.promote_to_student()
   - `student_applicant` is set
   - Side effects (User, Student Patient, Contact) are GATED
     and intentionally NOT executed during Phase 1
   - Used for all future admissions flows

2) Data Import / Migration (explicit bypass)
   - Used for onboarding existing schools or legacy data
   - Allowed ONLY when one of the following flags is set:
       - frappe.flags.in_import
       - frappe.flags.in_migration
       - frappe.flags.in_patch
       - frappe.flags.allow_direct_student_create
   - `student_applicant` is NOT required
   - All standard Student behaviors DO execute:
       - User creation
       - Student Patient creation
       - Contact linking
       - Image renaming & syncing
       - Sibling synchronization

3) Manual Back-office Creation (exceptional)
   - Allowed only for privileged staff
   - Requires explicit bypass flag
   - Intended for rare operational corrections, not admissions

Invariant:
-----------
In steady state, Students MUST originate from Applicant promotion.
All other creation paths are explicit, auditable exceptions.

This file intentionally enforces that invariant in Python,
not at schema level, to preserve import and migration safety.
"""


import frappe
import os
import random
import string
from frappe import _
from frappe.utils import getdate, today, get_link_to_form, validate_email_address
from frappe.utils import get_files_path
from frappe.model.document import Document
from frappe.desk.form.linked_with import get_linked_doctypes
from frappe.contacts.address_and_contact import load_address_and_contact
from ifitwala_ed.accounting.account_holder_utils import validate_account_holder_for_student
from ifitwala_ed.governance.policy_utils import (
	MEDIA_CONSENT_POLICY_KEY,
	has_applicant_policy_acknowledgement,
)


class Student(Document):
	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		self._validate_creation_source()
		validate_account_holder_for_student(self)
		self.student_full_name = " ".join(filter(None, [self.student_first_name, self.student_middle_name, self.student_last_name]))
		self.validate_email()
		self._validate_siblings_list()

		if frappe.get_value("Student", self.name, "student_full_name") != self.student_full_name:
			self.update_student_name_in_linked_doctype()

		if self.student_date_of_birth and getdate(self.student_date_of_birth) >= getdate(today()):
			frappe.throw(_("Check again student's birth date.  It cannot be after today."))

		if self.student_date_of_birth and getdate(self.student_date_of_birth) >= getdate(self.student_joining_date):
			frappe.throw(_("Check again student's birth date and or joining date. Birth date cannot be after joining date."))

		if self.student_joining_date and self.student_exit_date and getdate(self.student_joining_date) > getdate(self.student_exit_date):
			frappe.throw(_("Check again the exit date. The joining date has to be earlier than the exit date."))

		# Enforce unique student_full_name
		if frappe.db.exists("Student", {"student_full_name": self.student_full_name, "name": ["!=", self.name]}):
			frappe.throw(_("Student Full Name '{0}' must be unique. Please choose a different name.").format(self.student_full_name))

	def _validate_creation_source(self):
		# Canonical path: Applicant promotion
		if self.student_applicant:
			return

		# Explicit bypass for migration / import
		if getattr(frappe.flags, "in_migration", False):
			return
		if getattr(frappe.flags, "in_import", False):
			return
		if getattr(frappe.flags, "allow_direct_student_create", False):
			return
		if self.allow_direct_creation:
			return

		frappe.throw(
			_("Students must be created via Applicant promotion. "
				"Set an explicit migration/import bypass flag to create directly.")
		)


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
						 .format(d, linked_doctypes[d]["fieldname"][0]), (self.student_full_name, self.name))

				if "child_doctype" in linked_doctypes[d].keys() and "student_name" in \
					[f.fieldname for f in frappe.get_meta(linked_doctypes[d]["child_doctype"]).fields]:
					frappe.db.sql("""UPDATE `tab{0}` set student_name = %s where {1} = %s"""
						  .format(linked_doctypes[d]["child_doctype"], linked_doctypes[d]["fieldname"][0]), (self.student_full_name, self.name))

	def after_insert(self):
		"""
		Phase-1 gating:
		- If created via Applicant promotion: NO side effects (no user, no patient, no contact).
		- For imported/onboarded/direct Students: keep existing behavior.
		"""
		if getattr(frappe.flags, "from_applicant_promotion", False):
			return
		self.create_student_user()
		self.create_student_patient()
		self.ensure_contact_and_link()

	def on_update(self):
		self.rename_student_image()
		self.ensure_contact_and_link()
		self.update_student_enabled_status()
		self.sync_student_contact_image()
		self.sync_reciprocal_siblings()

	# create student as website user
	def create_student_user(self):
		if not self.student_email:
			return
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
		patient = frappe.db.get_value("Student Patient", {"student": self.name}, "name")
		if not patient:
			# During Applicant promotion Phase-1, we intentionally do NOT create Patient.
			# Also allow missing patient when student_applicant exists.
			if getattr(frappe.flags, "from_applicant_promotion", False) or self.student_applicant:
				return
			frappe.throw(_("Student Patient record is missing for this student."))
		if self.enabled == 0:
			frappe.db.set_value("Student Patient", patient, "status", "Disabled")
		else:
			frappe.db.set_value("Student Patient", patient, "status", "Active")

	def _has_media_consent(self) -> bool:
		if not self.student_applicant:
			return False
		return has_applicant_policy_acknowledgement(
			policy_key=MEDIA_CONSENT_POLICY_KEY,
			student_applicant=self.student_applicant,
		)

	def rename_student_image(self):
		# Only proceed if there's a student_image
		if not self.student_image:
			return

		if not self._has_media_consent():
			return

		try:
			file_name = frappe.db.get_value(
				"File",
				{"file_url": self.student_image, "attached_to_doctype": "Student", "attached_to_name": self.name},
				"name",
			)
			if file_name and frappe.db.exists("File Classification", {"file": file_name}):
				return

			student_id = self.name
			current_file_name = os.path.basename(self.student_image)

			# Check if it already has "STU-XXXX_XXXXXX.jpg" format
			if (current_file_name.startswith(student_id + "_")
				and len(current_file_name.split("_")[1].split(".")[0]) == 6
				and current_file_name.split(".")[1].lower() in ["jpg", "jpeg", "png", "gif"]
				and self.student_image.startswith("/files/student/")):
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
			file_name = frappe.db.get_value(
				"File",
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
			os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

			old_rel_path = (file_doc.file_url or "").lstrip("/")
			if not old_rel_path:
				frappe.throw(_("Original file URL is missing."))
			old_file_path = frappe.utils.get_site_path(old_rel_path)

			if os.path.exists(old_file_path):
				os.rename(old_file_path, new_file_path)
				new_url = f"/files/student/{expected_file_name}"
				frappe.db.set_value(
					"File",
					file_doc.name,
					{
						"file_name": expected_file_name,
						"file_url": new_url,
						"folder": "Home/student",
						"is_private": 0,
					},
					update_modified=False,
				)
			else:
				frappe.throw(_("Original file not found: {0}").format(old_file_path))

			# Update doc.student_image to reflect new URL
			frappe.db.set_value(
				"Student",
				self.name,
				"student_image",
				new_url,
				update_modified=False,
			)
			self.student_image = new_url

			from ifitwala_ed.utilities.image_utils import process_single_file
			file_doc.file_url = new_url
			process_single_file(file_doc)

			frappe.msgprint(_("Image renamed to {0} and moved to /files/student/").format(expected_file_name))

		except Exception as e:
			frappe.log_error(title=_("Student Image Error"), message=f"Error handling student image for {self.name}: {e}")
			frappe.msgprint(_("Error handling student image for {0}: {1}").format(self.name, e))

	# Sync the student image to the linked contact. This method is called after the student image is renamed
	def sync_student_contact_image(self):
		if not self.student_image:
			return

		contact_name = frappe.db.get_value(
			"Dynamic Link",
			filters={
				"link_doctype": "Student",
				"link_name": self.name,
				"parenttype": "Contact"
			},
			fieldname="parent"
		)

		if contact_name:
			contact = frappe.get_doc("Contact", contact_name)
			if contact.image != self.student_image:
				contact.image = self.student_image
				contact.save(ignore_permissions=True)

	def _validate_siblings_list(self):
		"""Prevent self-reference and duplicates in the child table before save."""
		seen = set()
		pruned = []
		for row in (self.siblings or []):
			if not row.student:
				continue
			if row.student == self.name:
				frappe.throw(_("A student cannot be a sibling of themselves."))
			key = row.student
			if key in seen:
				# skip duplicate
				continue
			seen.add(key)
			pruned.append(row)
		# If we pruned anything, rebuild the child list
		if len(pruned) != len(self.siblings or []):
			self.set("siblings", pruned)

	def sync_reciprocal_siblings(self):
		"""
		Make sibling links bidirectional without re-saving the other Student doc.
		- For each S in self.siblings, ensure a mirror row (student=self.name) exists under S.
		- For each S that *currently* points to self but is no longer in our list, remove that mirror row.
		Uses direct child table inserts/deletes to avoid triggering on_update on the other record.
		"""
		# recursion guard
		if getattr(frappe.flags, "_in_sibling_sync", False):
			return
		frappe.flags._in_sibling_sync = True
		try:
			desired = {row.student for row in (self.siblings or []) if row.student and row.student != self.name}
			current_pointing_to_me = self._current_mirror_set(self.name)  # set of student names who have me in their siblings

			# Ensure mirrors for desired
			for sib in desired:
				self._ensure_mirror_row(parent_student=sib, sibling=self.name)

			# Remove stale mirrors
			for sib in (current_pointing_to_me - desired):
				self._delete_mirror_row(parent_student=sib, sibling=self.name)
		finally:
			frappe.flags._in_sibling_sync = False

	def _current_mirror_set(self, me: str) -> set[str]:
		"""Return set of Student names that currently have a child-row pointing to `me`."""
		rows = frappe.get_all(
			"Student Sibling",
			filters={
				"parenttype": "Student",
				"parentfield": "siblings",
				"student": me
			},
			fields=["parent"],
			limit=None,
		)
		# parent is the other student who lists `me` as a sibling
		return {r["parent"] for r in rows if r.get("parent") and r["parent"] != me}

	def _ensure_mirror_row(self, parent_student: str, sibling: str):
		"""Create a mirror row under `parent_student` (if missing) that points to `sibling`."""
		exists = frappe.db.exists(
			"Student Sibling",
			{
				"parenttype": "Student",
				"parentfield": "siblings",
				"parent": parent_student,
				"student": sibling,
			},
		)
		if exists:
			return

		# Insert child row directly; don't save the parent Student to avoid event loops
		child = frappe.get_doc({
			"doctype": "Student Sibling",
			"parenttype": "Student",
			"parentfield": "siblings",
			"parent": parent_student,
			"student": sibling,
			# convenience fields; fetch_from keeps them fresh too
			"sibling_name": self.student_full_name,
			"sibling_gender": self.student_gender,
			"sibling_date_of_birth": self.student_date_of_birth,
		})
		child.insert(ignore_permissions=True)

	def _delete_mirror_row(self, parent_student: str, sibling: str):
		"""Delete the mirror row under `parent_student` that points to `sibling` (if present)."""
		frappe.db.delete(
			"Student Sibling",
			{
				"parenttype": "Student",
				"parentfield": "siblings",
				"parent": parent_student,
				"student": sibling,
			},
		)

	def ensure_contact_and_link(self):
		"""Idempotently ensure a Contact exists for this student's User and is linked back to the Student.
		No msgprint, safe to call from after_insert and on_update."""
		if not self.student_email:
			return

		# Require a User (created in after_insert)
		if not frappe.db.exists("User", self.student_email):
			return

		# 1) Find or create Contact bound to this user
		contact_name = frappe.db.get_value("Contact", {"user": self.student_email}, "name")
		if not contact_name:
			# Create a minimal Contact
			contact = frappe.get_doc({
				"doctype": "Contact",
				"user": self.student_email,
				"first_name": self.student_first_name or self.student_preferred_name or self.student_last_name or self.name,
				"last_name": self.student_last_name or "",
				"image": self.student_image or None
			})
			contact.flags.ignore_permissions = True
			if hasattr(contact, "email_id") and self.student_email:
				contact.email_id = self.student_email
			try:
				contact.insert()
				contact_name = contact.name
			except Exception:
				# If another request created it concurrently, load it
				contact_name = frappe.db.get_value("Contact", {"user": self.student_email}, "name")
				if not contact_name:
					raise
				contact = frappe.get_doc("Contact", contact_name)
		else:
			contact = frappe.get_doc("Contact", contact_name)

		# 2) Ensure Dynamic Link → Student (idempotent)
		link_exists = frappe.db.exists(
			"Dynamic Link",
			{
				"parenttype": "Contact",
				"parentfield": "links",
				"parent": contact.name,
				"link_doctype": "Student",
				"link_name": self.name,
			},
		)
		if link_exists:
			return

		contact.append("links", {"link_doctype": "Student", "link_name": self.name})
		contact.save(ignore_permissions=True)


@frappe.whitelist()
def get_contact_linked_to_student(student_name):
	"""Pure read: return Contact name linked to this Student, or None."""
	return frappe.db.get_value(
		"Dynamic Link",
		{
			"link_doctype": "Student",
			"link_name": student_name,
			"parenttype": "Contact"
		},
		"parent"
	)


def on_doctype_update():
	# speed up reverse lookups and parent scans
	frappe.db.add_index("Student Sibling", ["student"])
	frappe.db.add_index("Student Sibling", ["parent"])
