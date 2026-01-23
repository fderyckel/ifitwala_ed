# Copyright (c) 2024, François de Ryckel
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.py

import frappe
import json
from frappe import _
from frappe.utils import get_link_to_form, getdate, formatdate, date_diff, cint
from frappe.model.document import Document
from frappe.utils.nestedset import get_ancestors_of
from ifitwala_ed.utilities.school_tree import ParentRuleViolation
from ifitwala_ed.utilities.school_tree import (
	get_descendant_schools,
	is_leaf_school,
	get_first_ancestor_with_doc,
)
from ifitwala_ed.school_settings.school_settings_utils import (
	resolve_terms_for_school_calendar,
)


class SchoolCalendar(Document):
	def autoname(self):
		if not self.academic_year or not self.school:
			frappe.throw(_("Academic Year and School are required to generate the Calendar Name."))

		abbr = frappe.db.get_value("School", self.school, "abbr") or self.school
		ay_name = frappe.db.get_value(
			"Academic Year", self.academic_year, "academic_year_name"
		) or self.academic_year

		if not self.calendar_name:
			self.calendar_name = ay_name

		self.name = f"{abbr} {self.calendar_name}"
		self.title = self.name

	def onload(self):
		if not self.school:
			return

		weekend_color = frappe.db.get_value("School", self.school, "weekend_color")
		self.set_onload("weekend_color", weekend_color)

		break_color = frappe.db.get_value("School", self.school, "break_color")
		self.set_onload("break_color", break_color)

	def validate(self):
		self._sync_school_with_ay()
		self._validate_uniqueness()
		self._populate_term_table()

		self.validate_dates()
		self.validate_holiday_uniqueness()

		ay = frappe.get_doc("Academic Year", self.academic_year)
		self.total_holiday_days = len(self.holidays)
		self.total_number_day = (
			date_diff(getdate(ay.year_end_date), getdate(ay.year_start_date)) + 1
		)
		self.total_instruction_days = (
			self.total_number_day - self.total_holiday_days - 1
		)

	# ----------------------------------------------------------------
	def _sync_school_with_ay(self):
		"""
		AY drives calendar. Rule set:
		1. If school blank → inherit AY.school.
		2. If filled → must be AY.school or one of its descendants.
		"""
		ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school")

		if not self.school:
			self.school = ay_school
			return

		allowed = [self.school] + get_ancestors_of("School", self.school)
		if ay_school not in allowed:
			raise ParentRuleViolation(
				_("School {0} is not within the Academic Year's hierarchy ({1}).")
				.format(self.school, ay_school)
			)

	# ----------------------------------------------------------------
	def _validate_uniqueness(self):
		"""Disallow two calendars with same AY + School."""
		if frappe.db.exists(
			"School Calendar",
			{
				"academic_year": self.academic_year,
				"school": self.school,
				"name": ("!=", self.name),
				"docstatus": ("<", 2),
			},
		):
			frappe.throw(
				_("A School Calendar for {0} - {1} already exists.")
				.format(self.school, self.academic_year),
				title=_("Duplicate"),
			)

	# ----------------------------------------------------------------
	def _populate_term_table(self):
		"""
		Option B:
		Terms are resolved explicitly via School Calendar,
		not inferred from Academic Year or school hierarchy.
		"""

		term_names = resolve_terms_for_school_calendar(
			self.school,
			self.academic_year,
		)

		self.terms = []

		if not term_names:
			return

		terms = frappe.db.get_all(
			"Term",
			fields=["name", "term_start_date", "term_end_date"],
			filters={"name": ["in", term_names]},
			order_by="term_start_date",
		)

		holidays = frappe.db.get_all(
			"School Calendar Holidays",
			fields=["holiday_date"],
			filters={"parent": self.name, "parenttype": "School Calendar"},
		)
		holiday_dates = {h["holiday_date"] for h in holidays}

		for term in terms:
			total_days = (
				date_diff(term["term_end_date"], term["term_start_date"]) + 1
			)

			non_instructional_days = len(
				[
					h
					for h in holiday_dates
					if term["term_start_date"] <= h <= term["term_end_date"]
				]
			)

			instructional_days = total_days - non_instructional_days

			self.append(
				"terms",
				{
					"term": term["name"],
					"start": term["term_start_date"],
					"end": term["term_end_date"],
					"number_of_instructional_days": instructional_days,
				},
			)

	# ----------------------------------------------------------------
	def validate_holiday_uniqueness(self):
		seen = set()
		for h in self.get("holidays"):
			d = getdate(h.holiday_date)
			if d in seen:
				frappe.throw(
					_("Duplicate holiday date found: {0}").format(formatdate(d))
				)
			seen.add(d)

	def validate_dates(self):
		"""Ensure holidays are within the academic year"""
		ay = frappe.get_doc("Academic Year", self.academic_year)
		for day in self.get("holidays"):
			if not (
				getdate(ay.year_start_date)
				<= getdate(day.holiday_date)
				<= getdate(ay.year_end_date)
			):
				frappe.throw(
					_("The {0} holiday is not within your school's academic year {1}")
					.format(
						formatdate(day.holiday_date),
						get_link_to_form("Academic Year", self.academic_year),
					)
				)

	@frappe.whitelist()
	def get_long_break_dates(self):
		"""Logic for button to add long breaks dates to the list of holidays"""
		self.validate_break_dates()
		date_list = self.get_long_break_dates_list(
			self.start_of_break, self.end_of_break
		)
		last_idx = max([cint(d.idx) for d in self.get("holidays")] or [0])
		for i, d in enumerate(date_list):
			ch = self.append("holidays", {})
			ch.description = self.break_description or "Break"
			ch.color = self.break_color or ""
			ch.holiday_date = d
			ch.idx = last_idx + i + 1
		frappe.msgprint(
			_("Break dates for '{0}' have been successfully added to the holidays table.")
			.format(self.break_description)
		)

	def validate_break_dates(self):
		ay = frappe.get_doc("Academic Year", self.academic_year)
		if not self.start_of_break or not self.end_of_break:
			frappe.throw(_("Please select first the start and end dates of your break"))
		if getdate(self.start_of_break) > getdate(self.end_of_break):
			frappe.throw(
				_("The start date of the break must be prior to the end date of the break")
			)
		if not (
			getdate(ay.year_start_date)
			<= getdate(self.start_of_break)
			<= getdate(ay.year_end_date)
			and getdate(ay.year_start_date)
			<= getdate(self.end_of_break)
			<= getdate(ay.year_end_date)
		):
			frappe.throw(
				_("The holiday called {0} should be within your academic year {1} dates.")
				.format(
					self.break_description,
					get_link_to_form("Academic Year", self.academic_year),
				)
			)

	def get_long_break_dates_list(self, start_date, end_date):
		from datetime import timedelta

		start_date, end_date = getdate(start_date), getdate(end_date)
		existing = [getdate(h.holiday_date) for h in self.get("holidays")]

		date_list = []
		ref = start_date
		while ref <= end_date:
			if ref not in existing:
				date_list.append(ref)
			ref += timedelta(days=1)

		return date_list

	@frappe.whitelist()
	def get_weekly_off_dates(self):
		ay = frappe.get_doc("Academic Year", self.academic_year)
		self.validate_values()
		date_list = self.get_weekly_off_dates_list(
			ay.year_start_date, ay.year_end_date
		)
		last_idx = max([cint(d.idx) for d in self.get("holidays")] or [0])
		for i, d in enumerate(date_list):
			ch = self.append("holidays", {})
			ch.description = _(self.weekly_off)
			ch.holiday_date = d
			ch.color = self.weekend_color or ""
			ch.weekly_off = 1
			ch.idx = last_idx + i + 1

	def validate_values(self):
		if not self.weekly_off:
			frappe.throw(_("Please select the weekly off days."))

	def get_weekly_off_dates_list(self, start_date, end_date):
		from dateutil import relativedelta
		from datetime import timedelta
		import calendar

		start_date, end_date = getdate(start_date), getdate(end_date)
		weekday = getattr(calendar, self.weekly_off.upper())
		existing = [getdate(h.holiday_date) for h in self.get("holidays")]

		ref = start_date + relativedelta.relativedelta(weekday=weekday)
		date_list = []
		while ref <= end_date:
			if ref not in existing:
				date_list.append(ref)
			ref += timedelta(days=7)

		return date_list

	def on_doctype_update():
		frappe.db.add_index("School Calendar", ["academic_year", "school"])


@frappe.whitelist()
def get_events(start, end, filters=None):
	if filters:
		filters = json.loads(filters)
	else:
		filters = []

	if start:
		filters.append(["School Calendar Holidays", "holiday_date", ">", getdate(start)])
	if end:
		filters.append(["School Calendar Holidays", "holiday_date", "<", getdate(end)])

	return frappe.get_list(
		"School Calendar",
		fields=[
			"name",
			"academic_year",
			"school",
			"`tabSchool Calendar Holidays`.holiday_date",
			"`tabSchool Calendar Holidays`.description",
			"`tabSchool Calendar Holidays`.color",
		],
		filters=filters,
		update={"allDay": 1},
	)


@frappe.whitelist()
def clone_calendar(source_calendar, academic_year, schools):
	src = frappe.get_doc("School Calendar", source_calendar)
	created = []

	for school in frappe.parse_json(schools):
		if frappe.db.exists(
			"School Calendar",
			{"academic_year": academic_year, "school": school},
		):
			continue

		dup = frappe.copy_doc(src, ignore_no_copy=True)
		dup.school = school
		dup.academic_year = academic_year
		dup.calendar_name = academic_year
		dup.save()
		created.append(get_link_to_form("School Calendar", dup.name))

	return ", ".join(created) if created else "No new calendars created (already exist)."


def get_permission_query_conditions(user):
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return None

	user_school = frappe.defaults.get_user_default("school", user)
	if not user_school:
		return "1=0"

	if is_leaf_school(user_school):
		schools = get_first_ancestor_with_doc("School Calendar", user_school)
	else:
		schools = get_descendant_schools(user_school)

	if not schools:
		return "1=0"

	schools_list = "', '".join(schools)
	return f"`tabSchool Calendar`.`school` IN ('{schools_list}')"


def has_permission(doc, ptype=None, user=None):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	user_school = frappe.defaults.get_user_default("school", user)
	if not user_school:
		return False

	if is_leaf_school(user_school):
		schools = get_first_ancestor_with_doc("School Calendar", user_school)
	else:
		schools = get_descendant_schools(user_school)

	return doc.school in schools
