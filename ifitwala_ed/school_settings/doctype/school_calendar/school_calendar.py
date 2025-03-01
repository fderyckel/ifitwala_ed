# Copyright (c) 2024, François de Ryckel
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.utils import get_link_to_form, getdate, formatdate, date_diff, cint
from frappe.model.document import Document


class SchoolCalendar(Document):
  def autoname(self):
    # Ensure both academic_year and school are set
    if not self.academic_year or not self.school:
      frappe.throw(_("Academic Year and School are required to generate the Calendar Name."))

    # Efficiently get the school's abbreviation using frappe.db.get_value
    school_abbr = frappe.db.get_value("School", self.school, "abbreviation")
    if not school_abbr:
      frappe.throw(_("The selected school ({0}) does not have an abbreviation defined.").format(self.school))

    # Construct and set the document name
    self.name = "{0} {1}".format(self.academic_year, school_abbr)

  def onload(self):
    weekend_color = frappe.db.get_single_value("Education Settings", "weekend_color")
    self.set_onload('weekend_color', weekend_color)
    break_color = frappe.db.get_single_value("Education Settings", "break_color")
    self.set_onload("break_color", break_color)

  def validate(self):
    if not self.terms:
      self.extend("terms", self.get_terms())
    ay = frappe.get_doc("Academic Year", self.academic_year)
    if ay.school != self.school:
      frappe.throw(_("The academic year {0} is not for the school {1}").format(get_link_to_form("Academic Year", self.academic_year), get_link_to_form("School", self.school)))
    self.validate_dates()
    self.total_holidays_day = len(self.holidays)
    self.total_number_days = date_diff(getdate(ay.year_end_date), getdate(ay.year_start_date))
    self.total_instruction_days = date_diff(getdate(ay.year_end_date), getdate(ay.year_start_date)) - self.total_holidays_day

  @frappe.whitelist()
  def get_terms(self):
    self.terms = []
    terms = frappe.get_list(
      "Term",
      filters={"academic_year": self.academic_year},
      fields=['name as term', 'term_start_date as start', 'term_end_date as end'])

    if not terms:
      frappe.msgprint(_("No term found for the selected academic year. You need to add at least one academic term for this academic year {0}.").format(get_link_to_form("Academic Year", self.academic_year)))
      return []

    for term in terms:
      self.append("terms", {
        "term": term.term,
        "start": term.start,
        "end": term.end,
        "length": date_diff(getdate(term.end), getdate(term.start)) + 1
        })
      
    return self.terms

  def validate_dates(self):
    """Ensure holidays are within the academic year"""
    ay = frappe.get_doc("Academic Year", self.academic_year)
    for day in self.get("holidays"):
      if not (getdate(ay.year_start_date) <= getdate(day.holiday_date) <= getdate(ay.year_end_date)):
        frappe.throw(_("The {0} holiday is not within your school's academic year {1}").format(formatdate(day.holiday_date), get_link_to_form("Academic Year", self.academic_year)))

  @frappe.whitelist()
  def get_long_break_dates(self):
    """Logic for button to add long breaks dates to the list of holidays"""
    ay = frappe.get_doc("Academic Year", self.academic_year)
    self.validate_break_dates() 
    date_list = self.get_long_break_dates_list(self.start_of_break, self.end_of_break) 
    last_idx = max([cint(d.idx) for d in self.get("holidays")] or [0,])
    for i, d in enumerate(date_list):
        ch = self.append("holidays", {})
        ch.description = self.break_description if self.break_description else "Break"
        ch.color = self.break_color if self.break_color else ""
        ch.holiday_date = d
        ch.idx = last_idx + i + 1
    frappe.msgprint(_("Break dates for '{0}' have been successfully added to the holidays table.").format(self.break_description))


  def validate_break_dates(self):
    """Ensure breaks dates are wihin the academic year"""
    ay = frappe.get_doc("Academic Year", self.academic_year)
    if not self.start_of_break or not self.end_of_break:
      frappe.throw(_("Please select first the start and end dates of your break"))
    if getdate(self.start_of_break) > getdate(self.end_of_break):
        frappe.throw(_("The start date of the break must be prior to the end date of the break"))
    if not (getdate(ay.year_start_date) <= getdate(self.start_of_break) <= getdate(ay.year_end_date)) or not (getdate(ay.year_start_date) <= getdate(self.end_of_break) <= getdate(ay.year_end_date)):
      frappe.throw(_("The holiday called {0} should be within your academic year {1} dates.").format(self.break_description, get_link_to_form("Academic Year", self.academic_year))) 
      
  def get_long_break_dates_list(self, start_date, end_date):
    start_date, end_date = getdate(start_date), getdate(end_date)

    from datetime import timedelta
    import calendar

    date_list = []
    existing_date_list = []

    reference_date = start_date
    existing_date_list = [getdate(holiday.holiday_date) for holiday in self.get("holidays")]

    while reference_date <= end_date:
      if reference_date not in existing_date_list:
        date_list.append(reference_date)
      reference_date += timedelta(days = 1)

    return date_list

  @frappe.whitelist()
  def get_weekly_off_dates(self): 
    """Logic for button to add weekly off dates to the list of holidays"""
    ay = frappe.get_doc("Academic Year", self.academic_year)
    self.validate_values()
    date_list = self.get_weekly_off_dates_list(ay.year_start_date, ay.year_end_date)
    last_idx = max([cint(d.idx) for d in self.get("holidays")] or [0,])
    for i, d in enumerate(date_list):
      ch = self.append("holidays", {})
      ch.description = _(self.weekly_off)
      ch.holiday_date = d
      ch.color = self.weekend_color if self.weekend_color else ""
      ch.weekly_off = 1
      ch.idx = last_idx + i + 1
            
  def validate_values(self):
    if not self.weekly_off:
      frappe.throw(_("Please select the weekly off days."))
      
  def get_weekly_off_dates_list(self, start_date, end_date):
    start_date, end_date = getdate(start_date), getdate(end_date)

    from dateutil import relativedelta
    from datetime import timedelta
    import calendar

    date_list = []
    existing_date_list = []

    weekday = getattr(calendar, (self.weekly_off).upper())
    reference_date = start_date + relativedelta.relativedelta(weekday=weekday)
    existing_date_list = [getdate(holiday.holiday_date) for holiday in self.get("holidays")]

    while reference_date <= end_date:
      if reference_date not in existing_date_list:
        date_list.append(reference_date)
      reference_date += timedelta(days=7)

    return date_list
    
@frappe.whitelist()
def get_events(start, end, filters=None):
	if filters:
		filters = json.loads(filters)
	else:
		filters = []

	if start:
		filters.append(['Holiday', 'holiday_date', '>', getdate(start)])
	if end:
		filters.append(['Holiday', 'holiday_date', '<', getdate(end)])

	return frappe.get_list('School Calendar',
		fields=['name', 'academic_year', 'school', '`tabHoliday`.holiday_date', '`tabHoliday`.description', '`tabHoliday`.color'],
		filters = filters,
		update={"allDay": 1})
