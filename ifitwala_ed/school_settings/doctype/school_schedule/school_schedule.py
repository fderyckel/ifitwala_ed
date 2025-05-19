# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from frappe import _
from datetime import timedelta
from frappe.utils.nestedset import get_ancestors_of
from ifitwala_ed.utilities.school_tree import (ParentRuleViolation)

class SchoolSchedule(Document): 
	"""Handles school schedule configurations."""

	def autoname(self):
		# e.g.  IPS Weekly 2025-26  (schedule_name is your own field)
		abbr = frappe.db.get_value("School", self.school, "abbr") or self.school
		self.name = f"{abbr} {self.schedule_name}"
		self.title = self.name

	def validate(self):
		self._sync_school_with_calendar()
		self._enforce_single_schedule()
		self._resolve_fallbacks()

		# Get in-memory school_schedule_day
		schedule_days = self.get("school_schedule_day")
		
		# Fallback to DB only if not loaded (e.g. when doc saved without child data)
		if not schedule_days:
			schedule_days = frappe.get_all("School Schedule Day", filters={"parent": self.name}, fields=["name"])

		rotation_day_count = len(schedule_days)

		if rotation_day_count > self.rotation_days:
			frappe.throw(
				f"You have defined {rotation_day_count} rotation days, "
				f"but the schedule allows only {self.rotation_days}. "
				"Please remove the excess rotation days."
			)

		if rotation_day_count < self.rotation_days:
			frappe.throw(
				f"You have defined only {rotation_day_count} rotation days, "
				f"but the schedule requires {self.rotation_days}. "
				"Please add the missing rotation days."
			)  

		if self.first_day_rotation_day: 
			if not 1 <= self.first_day_rotation_day <= self.rotation_days: 
				frappe.throw(_(
					f"The chosen rotation day ({self.first_day_rotation_day}) for the first academic day "
					f"is out of range. You must choose a value between 1 and {self.rotation_days}."
				))   

	# ----------------------------------------------------------------
	def _sync_school_with_calendar(self):
		"""
		School Calendar drives the allowed school tree.
		1. If schedule.school is blank → set to calendar.school.
		2. If filled → must be descendant of calendar.school.
		"""
		if not self.school_calendar:
			frappe.throw(_("Please choose a School Calendar first."))

		calendar_school = frappe.db.get_value("School Calendar", self.school_calendar, "school")

		if not self.school:
			# inherit
			self.school = calendar_school
			return

		allowed = [self.school] + get_ancestors_of("School", self.school)
		if calendar_school not in allowed:
			raise ParentRuleViolation(
				_("School {0} is not within the hierarchy of the Calendar's school ({1}).")
				.format(self.school, calendar_school)
			)

	# ----------------------------------------------------------------
	def _enforce_single_schedule(self):
		"""Disallow two schedules for the same School + Calendar."""
		if frappe.db.exists(
			"School Schedule",
			{
				"school_calendar": self.school_calendar,
				"school": self.school,
				"name": ("!=", self.name),
				"docstatus": ("<", 2),
			}
		):
			frappe.throw(
				_("A Schedule already exists for {0} under Calendar {1}.")
				.format(self.school, self.school_calendar), title=_("Duplicate"),
			)

	# ----------------------------------------------------------------
	def _resolve_fallbacks(self):
		"""
		If this school has *no* schedule yet (we're in before_insert for a child
		who inherits), nothing to do.  When Timetable builder asks for a schedule
		for a given school we'll call the helper below.
		"""
		pass


	@frappe.whitelist()
	def generate_rotation_days(self):
		"""Generate rotation days based on rotation_days count."""
		
		if not self.rotation_days or self.rotation_days <= 0:
			frappe.throw("Please set a valid number of rotation days before generating.")

		# Check existing rotation days
		if self.get("school_schedule_day"):
			frappe.throw(
				"Rotation days already exist. If you want to regenerate them, please clear them first "
			)

		# Generate new rotation days and append them to the child table
		for day in range(1, self.rotation_days + 1):
			rotation_label = f"Day {day}"  # Default label
			schedule_day = self.append("school_schedule_day", {})
			schedule_day.rotation_day = day
			schedule_day.rotation_label = rotation_label
			schedule_day.number_of_blocks = 0  # Default value, user must update later

		frappe.msgprint(f"{self.rotation_days} Rotation Days have been generated.")


	@frappe.whitelist()
	def clear_schedule(self):
		"""Deletes all School Schedule Days and Blocks."""
		frappe.db.sql(
			"""
			DELETE FROM `tabSchool Schedule Block`
			WHERE parent=%s
			""",
			(self.name,)
		)
		frappe.db.sql(
			"""
			DELETE FROM `tabSchool Schedule Day`
			WHERE parent=%s
			""",
			(self.name,)
		)
		frappe.db.commit()
		frappe.msgprint("School Schedule Days and Blocks have been cleared.")
		# Also clear in-memory tables
		self.set("school_schedule_day", [])
		self.set("course_schedule_block", [])

	@frappe.whitelist()
	def generate_blocks(self):
		"""Manually generate School Schedule Blocks based on School Schedule Days."""

		if not self.get("school_schedule_day"):
			frappe.throw("No School Schedule Days found. Please generate rotation days first.")

		# Check if blocks already exist in the child table
		if self.get("course_schedule_block"):
			frappe.throw(
				"Blocks already exist. If you want to regenerate them, please clear them first "
				"or use the overwrite option."
			)

		# Generate blocks for each rotation day
		for day in self.get("school_schedule_day"):
			if day.number_of_blocks <= 0:
				frappe.throw(
					f"Rotation Day {day.rotation_day} does not have a valid number of blocks. "
					"Please set the number of blocks before generating them."
				)

			for block_number in range(1, day.number_of_blocks + 1):
				block = self.append("course_schedule_block", {})
				block.rotation_day = day.rotation_day
				block.block_number = block_number

		frappe.msgprint("School Schedule Blocks have been generated.")


def on_doctype_update():
	frappe.db.add_index(
		"School Schedule",
		fields=["school_calendar", "school"],
		index_name="idx_schedule_cal_school"
	)

@frappe.whitelist()
def get_first_day_of_academic_year(school_calendar):
  academic_year = frappe.db.get_value("School Calendar", school_calendar, "academic_year")
  if not academic_year:
    return None
  year_start_date = frappe.db.get_value("Academic Year", academic_year, "year_start_date")
  return year_start_date
	