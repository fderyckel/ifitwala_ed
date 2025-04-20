# Copyright (c) 2024, François de Ryckel
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, get_link_to_form, cstr
from frappe import _
from frappe.model.document import Document


class AcademicYear(Document):

    def autoname(self):
        self.name = self.academic_year_name

    def validate(self):
        self.validate_duplicate()

        self.title = self.academic_year_name

        # The start of the year has to be before the end of the academic year.
        if self.year_start_date and self.year_end_date and getdate(self.year_start_date) > getdate(self.year_end_date):
            frappe.throw(_("The start of the academic year ({0}) has to be before the end of the academic year ({1}).").format(self.year_start_date, self.year_end_date), title=_("Wrong Dates"))

    def on_update(self):
        if self.year_start_date and self.year_end_date:
            self.create_calendar_events()

    def validate_duplicate(self):
        year = frappe.db.exists("Academic Year", 
                              {
                                    "academic_year_name": self.academic_year_name,
                                    "docstatus": ("<", 2),
                                    "name": ("!=", self.name)
                              })
        if year:
            frappe.throw(_("An academic year with this name {0} already exist.").format(self.academic_year_name), 
                         title=_("Duplicate Entry"))

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
        # Retire all active Program Enrollments for this Academic Year
        frappe.db.sql("""
            UPDATE `tabProgram Enrollment`
            SET status = 0
            WHERE academic_year = %s
            AND status = 1
        """, (self.name,))
        
        # Update the Academic Year's own status to indicate it is retired
        self.db_set("status", 0)
        frappe.db.commit()
        frappe.msgprint(_("Academic Year retired successfully."))
        return "Academic Year retired successfully."   

@frappe.whitelist()
def retire_academic_year(academic_year):
    # Fetch the Academic Year doc and call its retire method
    doc = frappe.get_doc("Academic Year", academic_year)
    return doc.retire_ay() 