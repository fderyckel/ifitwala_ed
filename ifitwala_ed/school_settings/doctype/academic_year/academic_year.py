# Copyright (c) 2024,  François de Ryckel
# For license information, please see license.txt

import frappe
from frappe import _
from frappe import qb
from frappe.utils import getdate, get_link_to_form, cstr
from frappe.model.document import Document


class AcademicYear(Document):

	def autoname(self):
		if self.school:
			sch_abbr = frappe.get_value("School", self.school, "abbr")
		self.name = self.academic_year_name + " ({})".format(sch_abbr) if self.school else ""

	def validate(self):
		self.validate_duplicate()

		if self.school:
			sch_abbr = frappe.get_value("School", self.school, "abbr")

		self.title = self.academic_year_name + " ({})".format(sch_abbr) if self.school else ""

		# The start of the year has to be before the end of the academic year.
		if self.year_start_date and self.year_end_date and getdate(self.year_start_date) >= getdate(self.year_end_date):
				frappe.throw(_("The start of the Academic Year ({}) has to be before the end of the Academic Year ({1}).").format(self.year_start_date, self.year_end_date), title = _("Invalid Dates"))

	def validate_duplicate(self):
		year = qb.DocType("Academic Year")
		query = (
			qb.from_(year)
			.select(year.name)
			.where(
				(year.school == self.school)
				& (year.academic_year_name == self.academic_year_name)
				& (year.docstatus < 2)
				& (year.name != self.name)
			)
		).run()

		if query:
			frappe.throw(_("An Academic Year with this name {0} and this school {1} already exists").format(self.academic_year_name, get_link_to_form("School", self.school)), title = _("Duplicate Academic Year"))


	def create_calendar_event(self):
		"""Create 2 calendar events (one for start and one for end) for the academic year."""
		if self.ay_start:
			start_ay = frappe.get_doc("School Event", self.ay_start)
			if getdate(start_ay.starts_on) != getdate(self.year_start_date):
				start_ay.starts_on =  self.year_start_date
				start_ay.ends_on = self.year_start_date
				start_ay.save(ignore_permissions=True)
				frappe.msgprint(_("The Date for the start of the Academic Year {0} has been updated in the calendar event {0}").format(self.year_start_date, get_link_to_form("School Event", start_ay.name)))

		if self.ay_end:
			end_ay = frappe.get_doc("School Event", self.ay_end)
			if getdate(end_ay.ends_on) != getdate(self.year_end_date):
				end_ay.db_set("starts_on", self.year_end_date)
				end_ay.db_set("ends_on", self.year_end_date)
				frappe.msgprint(_("The Date for the end of the Academic Year {0} has been updated in the calendar event {0}").format(self.year_end_date, get_link_to_form("School Event", end_ay.name)))

		if not self.ay_start:
			start_year = frappe.new_doc("School Event")
			start_year.update({
				"doctype": "School Event",
				"owner": frappe.session.user,
				"subject": "Start of the " + cstr(self.name) + " Academic Year",
				"starts_on": getdate(self.year_start_date),
				"ends_on": getdate(self.year_start_date),
				"status": "Closed",
				"school": self.school,
				"event_type": "Public",
				"all_day": 1,
				"color": "#7575ff",
				"reference_doctype": "Academic Year",
				"reference_docname": self.name
			})
			start_year.insert(ignore_permissions=True)
			self.ay_start = start_year.name
			self.save(ignore_permissions=True)
			frappe.msgprint(_("A calendar event has been created for the start of the Academic Year {0}").format(self.year_start_date, get_link_to_form("School Event", start_year.name)))

		if not self.ay_end: 
			end_year = frappe.new_doc("School Event")
			end_year.update({
				"doctype": "School Event",
				"owner": frappe.session.user,
        "subject": "End of the " + cstr(self.name) + " Academic Year",
        "starts_on": getdate(self.year_end_date),
        "ends_on": getdate(self.year_end_date),
        "status": "Closed",
        "school": self.school,
        "event_category": "Other",
        "event_type": "Public",
        "all_day": "1",
        "color": "#7575ff",
        "reference_type": "Academic Year",
        "reference_name": self.name 
			})
			end_year.insert(ignore_permissions=True) 
			self.ay_end = end_year.name  
			self.save(ignore_permissions=True)
			frappe.msgprint(_("Date for the end of the year {0} has been created on the School Event Calendar {1}").format(self.year_end_date, get_link_to_form("School Event", end_year.name))) 

		frappe.db.commit()
		return {"message": "Calendar events created"}




