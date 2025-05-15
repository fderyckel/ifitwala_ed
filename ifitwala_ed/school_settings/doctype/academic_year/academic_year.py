# Copyright (c) 2024, François de Ryckel
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, get_link_to_form, cstr
from frappe import _
from frappe.model.document import Document

class AcademicYear(Document):

	def autoname(self):
		if self.school:
			abbr = frappe.db.get_value("School", self.school, "abbr") or self.school 
			self.name = f"{abbr} {self.academic_year_name}" 
		else: 
			self.name = self.academic_year_name 
		self.title = self.name 

	def autoname(self):
		abbr = frappe.db.get_value("School", self.school, "abbr") or self.school
		self.name = f"{abbr} {self.academic_year_name}"
		self.title = self.name			# keep title in sync

	# ──────────────────────────────────────────────────────────────────
	def validate(self):
		self._validate_duplicate()
		self._validate_dates()

	def on_update(self):
		if self.year_start_date and self.year_end_date:
			self.create_calendar_events()

	def _validate_duplicate(self):
		# same ay_name in same school not allowed
		if frappe.db.exists(
			"Academic Year",
			{
				"academic_year_name": self.academic_year_name,
				"school": self.school,
				"name": ("!=", self.name),
				"docstatus": ("<", 2),
			},
		):
			frappe.throw(
				_("Academic Year {0} already exists for school {1}.")
				.format(self.academic_year_name, self.school),
				title=_("Duplicate"),
			)

	def _validate_dates(self):
		if self.year_start_date and self.year_end_date \
				and getdate(self.year_start_date) > getdate(self.year_end_date):
			frappe.throw(_("Start date ({0}) must be before end date ({1}).")
				.format(self.year_start_date, self.year_end_date),
				title=_("Date Error"),
			)		

	def create_calendar_events(self):
		if self.ay_start:
			start_ay = frappe.get_doc("School Event", self.ay_start)
			if getdate(start_ay.starts_on) != getdate(self.year_start_date):
				start_ay.db_set("starts_on", self.year_start_date)
				start_ay.db_set("ends_on", self.year_start_date)
				frappe.msgprint(_("Date for the start of the year {0} has been updated on the School Event Calendar {1}").format(self.year_start_date, get_link_to_form("School Event", start_ay.name)))

		if self.ay_end:
			end_ay = frappe.get_doc("School Event", self.ay_end)
			if getdate(end_ay.ends_on) != getdate(self.year_end_date):
				end_ay.db_set("starts_on", self.year_end_date)
				end_ay.db_set("ends_on", self.year_end_date)
				frappe.msgprint(_("Date for the end of the year {0} has been updated on the School Event Calendar {1}").format(self.year_end_date, get_link_to_form("School Event", end_ay.name)))

		if not self.ay_start:
			start_year = frappe.get_doc({
				"doctype": "School Event",
				"owner": frappe.session.user,
				"subject": "Start of the " + cstr(self.name) + " Academic Year",
				"starts_on": getdate(self.year_start_date),
				"ends_on": getdate(self.year_start_date),
				"status": "Closed",
				"event_category": "Other",
				"event_type": "Public",
				"all_day": "1",
				"color": "#7575ff",
				"reference_type": "Academic Year",
				"reference_name": self.name
			})
			start_year.insert()
			self.db_set("ay_start", start_year.name)
			frappe.msgprint(_("Date for the start of the year {0} has been created on the School Event Calendar {1}").format(self.year_start_date, get_link_to_form("School Event", start_year.name)))

		if not self.ay_end:
			end_year = frappe.get_doc({
				"doctype": "School Event",
				"owner": frappe.session.user,
				"subject": "End of the " + cstr(self.name) + " Academic Year",
				"starts_on": getdate(self.year_end_date),
				"ends_on": getdate(self.year_end_date),
				"status": "Closed",
				"event_category": "Other",
				"event_type": "Public",
				"all_day": "1",
				"color": "#7575ff",
				"reference_type": "Academic Year",
				"reference_name": self.name
			})
			end_year.insert()
			self.db_set("ay_end", end_year.name)
			frappe.msgprint(_("Date for the end of the year {0} has been created on the School Event Calendar {1}").format(self.year_end_date, get_link_to_form("School Event", end_year.name)))  

	@frappe.whitelist()
	def retire_ay(self):

		# 1. Retire all active Terms linked to this Academic Year
		frappe.db.sql("""
			UPDATE `tabTerm`
			SET archived = 1
			WHERE academic_year = %s
			AND archived = 0
		""", (self.name,))

		# 2. Retire all active Program Enrollments for this Academic Year
		frappe.db.sql("""
			UPDATE `tabProgram Enrollment`
			SET archived = 1
			WHERE academic_year = %s
			AND archived = 0
		""", (self.name,))
		
		# Update the Academic Year's own status to indicate it is retired
		self.db_set("archived", 1)
		frappe.db.commit()
		frappe.msgprint(_("Academic Year retired successfully. Set status to 0 for linked program enrollments and terms"))
		return "Academic Year archived successfully."   

@frappe.whitelist()
def retire_academic_year(academic_year):
	# Fetch the Academic Year doc and call its retire method
	doc = frappe.get_doc("Academic Year", academic_year)
	return doc.retire_ay() 
