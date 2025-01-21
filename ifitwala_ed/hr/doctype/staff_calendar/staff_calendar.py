# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import json
from datetime import date

from frappe import _
from frappe.utils import getdate, today, formatdate, cint, date_diff
from frappe.model.document import Document


class StaffCalendar(Document):

  def validate(self):
    self.validate_days()
    self.total_holidays = len(self.holidays)
    self.total_working_day = date_diff(self.to_date, self.from_date) - self.total_holidays + 1
    self.validate_duplicate_date()
    self.sort_holidays()

  def validate_days(self):
    if not self.start_of_break and not self.end_of_break:
      frappe.throw(_("Please select first the start and end of your break."))
    if getdate(self.from_date) > getdate(self.to_date):
      frappe.throw(_("From Date cannot be after To Date. Please adjust the date."))
    for day in self.get("holidays"):
      if not (getdate(self.from_date) <= getdate(day.holiday_date) <= getdate(self.to_date)):
        frappe.throw(_("The holiday on {0} should be between From Date and To Date.").format(formatdate(day.holiday_date)))

  def validate_duplicate_date(self):
    unique_dates = []
    for day in self.holidays:
      if day.holiday_date in unique_dates:
        frappe.throw(_("Date {0} is duplicated. Please remove the duplicate date.").format(formatdate(day.holiday_date)))
      unique_dates.append(day.holiday_date)

  def sort_holidays(self):
    self.holidays.sort(key=lambda x: getdate(x.holiday_date))
    for i in range(len(self.holidays)):
      self.holidays[i].idx = i + 1

  #logic for the button "get_weekly_off_dates"
  @frappe.whitelist()
  def get_weekly_off_dates(self):
    if not self.weekly_off:
        frappe.throw(_("Please select first the weekly off days."))

    existing_holidays = self.get_holidays()

    for d in self.get_weekly_off_dates_list(self.from_date, self.to_date):
      if d in existing_holidays:
        continue
      
    self.append("holidays", {
        "holiday_date": d,
        "description": _("weekly off"),
        "color": self.weekend_color,
        "weekly_off": 1
    })

  # Function to generate the list of weekly off dates
  def get_weekly_off_dates_list(self, start_date, end_date):
    start_date, end_date = getdate(start_date), getdate(end_date)

    from dateutil import relativedelta
    from datetime import timedelta
    import calendar
    
    date_list = []
    existing_date_list = []
    weekday = getattr(calendar, (self.weekly_off).upper())
    reference_date = start_date + relativedelta.relativedelta(weekday = weekday)
    existing_date_list = [getdate(holiday.holiday_date) for holiday in self.get("holidays")]

    while reference_date <= end_date:
      if reference_date not in existing_date_list:
        date_list.append(reference_date)
      reference_date += timedelta(days = 7)

    return date_list
  
  def get_holidays(self) -> list[date]:
    return [getdate(holiday.holiday_date) for holiday in self.holidays]

	# logic for the button "get_long_break_dates"
  @frappe.whitelist()
  def get_country_holidays(self): 
    from holidays import country_holidays

    if not self.country: 
      frappe.throw(_("Please select the country first."))

    existing_holidays = self.get_holidays()
    from_date = getdate(self.from_date)
    to_date = getdate(self.to_date)

    for holiday_date, holiday_name in country_holidays(
      self.country, 
      subdiv = self.subdivision,
      years = list(range(from_date.year, to_date.year + 1)), 
      language = frappe.local.lang
    ).item(): 
      if holiday_date in existing_holidays: 
        continue

      if holiday_date < from_date or holiday_date > to_date: 
        continue

      self.append("holidays", {
        "holiday_date": holiday_date,
        "description": holiday_name,
        "weekly_off": 0, 
        "color": self.local_holiday_color
      })

  @frappe.whitelist()
  def get_break_holidays(self):
    self.validate_break_values()
    existing_holidays = self.get_holidays()

    for d in self.get_long_break_dates_list(self.start_of_break, self.end_of_break): 
      if d in existing_holidays: 
        continue

      self.append("holidays", {
        "holiday_date": d,
        "description": self.break_description,
        "color": self.break_color,
        "weekly_off": 0
      })

      
  def validate_break_values(self):
    if not self.start_of_break and not self.end_of_break:
      frappe.throw(_("Please select first the start and end of your break."))
    if getdate(self.start_of_break) > getdate(self.end_of_break):
      frappe.throw(_("The start of the break cannot be after its end. Adjust the dates."))
    if not (getdate(self.from_date) <= getdate(self.start_of_break) <= getdate(self.to_date)) or not (getdate(self.from_date) <= getdate(self.end_of_break) <= getdate(self.to_date)):
      frappe.throw(_("The start and end of the break have to be within the start and end of the calendar."))

  # Function to get the list of long break dates
  def get_long_break_dates_list(self, start_date, end_date):
    start_date, end_date = getdate(start_date), getdate(end_date)

    from dateutil import relativedelta
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

  # logic for the button "clear_table"
  def clear_table(self):
    self.set("holidays", [])

  def get_holidays(self) -> list[date]:
    return [getdate(holiday.holiday_date) for holiday in self.holidays]



@frappe.whitelist()
def get_events(start, end, filters=None):
  """Returns events for Gantt/Calendar view rendering. 
	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
  if filters:
    filters = json.loads(filters)
  else:
    filters = []

  if start:
    filters.append(['Holiday', 'holiday_date', '>', getdate(start)])
  if end:
    filters.append(['Holiday', 'holiday_date', '<', getdate(end)])

  return frappe.get_list('Staff Calendar',
    fields=["name", "academic_year", "school", 
            "`tabHoliday`.holiday_date", "`tabHoliday`.description", "`tabHoliday`.color"],
    filters=filters,
    update={"allDay": 1})
