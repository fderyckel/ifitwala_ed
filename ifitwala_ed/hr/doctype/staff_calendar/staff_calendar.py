# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.hr.doctype.staff_calendar.staff_calendar

import frappe
from datetime import date
from frappe import _
from frappe.utils import getdate, formatdate, date_diff
from frappe.model.document import Document

class StaffCalendar(Document):
	def validate(self):
		self._validate_period()
		self.validate_days()
		self.validate_duplicate_date()
		self.sort_holidays()

		# totals
		self.total_holidays = len(self.holidays or [])
		if self.from_date and self.to_date:
			# inclusive of both from_date and to_date
			self.total_working_day = date_diff(self.to_date, self.from_date) + 1 - self.total_holidays
		else:
			self.total_working_day = 0

	def _validate_period(self):
		if not self.from_date or not self.to_date:
			frappe.throw(_("From Date and To Date are required."))

		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be after To Date. Please adjust the date."))

		# New: enforce Employee Group (core of the design)
		if not getattr(self, "employee_group", None):
			frappe.throw(_("Employee Group must be specified for this Staff Calendar."))

	def validate_duplicate_date(self):
		unique_dates = []
		for day in self.holidays:
			if day.holiday_date in unique_dates:
				frappe.throw(_("Date {0} is duplicated. Please remove the duplicate date.").format(formatdate(day.holiday_date)))
			unique_dates.append(day.holiday_date)

	def sort_holidays(self):
		self.holidays.sort(key=lambda x: getdate(x.holiday_date))
		for idx, row in enumerate(self.holidays, start=1):
			row.idx = idx

	@frappe.whitelist()
	def get_weekly_off_dates(self):
		# If you keep this functionality
		if not self.weekly_off:
			frappe.throw(_("Please select first the weekly off day."))
		existing = self.get_holidays()
		for d in self.get_weekly_off_dates_list(self.from_date, self.to_date):
			if d in existing:
				continue
			self.append("holidays", {
				"holiday_date": d,
				"description": _("Weekly Off"),
				"color": self.weekend_color,
				"weekly_off": 1
			})

	def get_weekly_off_dates_list(self, start_date, end_date):
		start, end = getdate(start_date), getdate(end_date)
		from dateutil import relativedelta
		from datetime import timedelta
		import calendar
		date_list = []
		existing = [getdate(h.holiday_date) for h in self.get("holidays")]
		weekday = getattr(calendar, (self.weekly_off).upper())
		reference = start + relativedelta.relativedelta(weekday=weekday)
		while reference <= end:
			if reference not in existing:
				date_list.append(reference)
			reference += timedelta(days=7)
		return date_list

	def get_holidays(self) -> list[date]:
		return [getdate(h.holiday_date) for h in self.holidays]

	@frappe.whitelist()
	def get_country_holidays(self):
		from holidays import country_holidays
		if not self.country:
			frappe.throw(_("Please select the country first."))
		existing = self.get_holidays()
		from_date = getdate(self.from_date)
		to_date = getdate(self.to_date)
		for holiday_date, holiday_name in country_holidays(
				self.country,
				subdiv=self.subdivision,
				years=list(range(from_date.year, to_date.year + 1)),
				language=frappe.local.lang
		).items():
			if holiday_date in existing:
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
	def get_supported_countries(self):
		from holidays.utils import list_supported_countries

		subdivisions_by_country = list_supported_countries()
		countries = [
			{"value": code, "label": code}
			for code in sorted(subdivisions_by_country.keys())
		]
		return {
			"countries": countries,
			"subdivisions_by_country": subdivisions_by_country,
		}


	@frappe.whitelist()
	def get_break_holidays(self):
		self.validate_break_values()
		existing = self.get_holidays()
		for d in self.get_long_break_dates_list(self.start_of_break, self.end_of_break):
			if d in existing:
				continue
			self.append("holidays", {
				"holiday_date": d,
				"description": self.break_description,
				"color": self.break_color,
				"weekly_off": 0
			})

	def validate_break_values(self):
		if not (self.start_of_break and self.end_of_break):
			frappe.throw(_("Please select the start and end of the break."))
		if getdate(self.start_of_break) > getdate(self.end_of_break):
			frappe.throw(_("The start of the break cannot be after its end."))
		if not (getdate(self.from_date) <= getdate(self.start_of_break) <= getdate(self.to_date)) or not (getdate(self.from_date) <= getdate(self.end_of_break) <= getdate(self.to_date)):
			frappe.throw(_("The break period must fall within the calendar period."))

	def get_long_break_dates_list(self, start_date, end_date):
		start, end = getdate(start_date), getdate(end_date)
		from datetime import timedelta
		date_list = []
		existing = [getdate(h.holiday_date) for h in self.get("holidays")]
		reference = start
		while reference <= end:
			if reference not in existing:
				date_list.append(reference)
			reference += timedelta(days=1)
		return date_list

	@frappe.whitelist()
	def clear_table(self):
		self.set("holidays", [])

	@frappe.whitelist()
	def copy_from_calendar(self, source_calendar):
		if not source_calendar:
			frappe.throw(_("Please specify a source calendar."))

		src = frappe.get_doc("Staff Calendar", source_calendar)

		if src.school != self.school:
			frappe.throw(_("Source calendar must belong to the same school."))

		existing = {getdate(h.holiday_date) for h in self.holidays}

		for row in src.holidays:
			if getdate(row.holiday_date) in existing:
				continue
			self.append("holidays", {
				"holiday_date": row.holiday_date,
				"description": row.description,
				"color": row.color,
				"weekly_off": row.weekly_off,
			})


