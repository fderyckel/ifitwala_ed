# Copyright (c) 2024, François de Ryckel
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, get_link_to_form, cstr
from frappe import _
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
        if self.year_start_date and self.year_end_date and getdate(self.year_start_date) > getdate(self.year_end_date):
            frappe.throw(_("The start of the academic year ({0}) has to be before the end of the academic year ({1}).").format(self.year_start_date, self.year_end_date), title=_("Wrong Dates"))

    def on_update(self):
        if self.year_start_date and self.year_end_date:
            self.create_calendar_events()

    def on_trash(self): 
        # first inform user that we will also delete the 2 school events related to that academic year
        frappe.msgprint(_("This is also delete the 2 School Events related to this Academic Year."), 
                        title = _("Warning"), indicator = "orange")
        
        # delete the 2 school events related to the academic year
        school_events = frappe.get_list("School Event", filters = {"reference_type": "Academic Year", "reference_name": self.name}, fields = ["name"])
        for event in school_events: 
            frappe.delete_doc("School Event", event.name)
        
        # confirmation message
        frappe.msgprint(_("The 2 School Events related to this Academic Year have been deleted."), 
                        title = _("Deletion Successful"), indicator = "green")

    def validate_duplicate(self):
        year = frappe.db.sql("""select name from `tabAcademic Year` where school=%s and academic_year_name=%s and docstatus<2 and name!=%s""", (self.school, self.academic_year_name, self.name))
        if year:
            frappe.throw(_("An academic year with this name {0} and this school {1} already exist.").format(self.academic_year_name, get_link_to_form("School", self.school)), title=_("Duplicate Entry"))

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
                "school": self.school,
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
                "school": self.school,
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
    def create_academic_term(self):  
        academic_term = frappe.new_doc("Academic Term")
        academic_term.academic_year = self.name
        academic_term.term_name = "Term 1"
        academic_term.save()
        frappe.response["type"] = "redirect"
        frappe.response["location"] = frappe.get_doc("Academic Term", academic_term.name).get_url()


