# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from frappe import _
from frappe.utils import getdate
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
		self._validate_block_time_overlaps()

		# Get in-memory school_schedule_day
		schedule_days = self.get("school_schedule_day")
		
		# Fallback to DB only if not loaded (e.g. when doc saved without child data)
		if not schedule_days:
			schedule_days = frappe.get_all("School Schedule Day", filters={"parent": self.name}, fields=["name"])

		rotation_day_count = len(schedule_days)

		if rotation_day_count > self.rotation_days:
			frappe.throw(_(
				f"You have defined {rotation_day_count} rotation days, "
				f"but the schedule allows only {self.rotation_days}. "
				"Please remove the excess rotation days.")
			)

		if rotation_day_count < self.rotation_days:
			frappe.throw(_(
				f"You have defined only {rotation_day_count} rotation days, "
				f"but the schedule requires {self.rotation_days}. "
				"Please add the missing rotation days.")
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
			raise ParentRuleViolation(_(
				"School {0} is not within the hierarchy of the Calendar's school ({1}).")
				.format(get_link_to_form(self.school), calendar_school
			))

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
			frappe.throw(_(
				"A Schedule already exists for {0} under Calendar {1}.")
				.format(get_link_to_form(self.school), get_link_to_form(self.school_calendar)), title=_("Duplicate"),
			)

	# ----------------------------------------------------------------
	def _resolve_fallbacks(self):
		"""
		If this school has *no* schedule yet (we're in before_insert for a child
		who inherits), nothing to do.  When Timetable builder asks for a schedule
		for a given school we'll call the helper below.
		"""
		pass


	def _validate_block_time_overlaps(self):
		day_blocks = {}
		for row in self.school_schedule_block:
			if not row.from_time or not row.to_time:
				continue  # Ignore incomplete entries

			# Check that start time is before end time
			if row.from_time >= row.to_time:
				frappe.throw(_(
					"For Block {block} on Rotation Day {day}, the start time ({start}) must be before the end time ({end})."
				).format(
					block=row.block_number,
					day=row.rotation_day,
					start=row.from_time,
					end=row.to_time,
				))

			day_blocks.setdefault(row.rotation_day, []).append(row)

		# Check all block pairs for overlaps per rotation day
		for rotation_day, blocks in day_blocks.items():
			sorted_blocks = sorted(blocks, key=lambda b: b.from_time)
			for i, block1 in enumerate(sorted_blocks):
				for block2 in sorted_blocks[i+1:]:
					if block1.to_time <= block2.from_time:
						break
					if block2.from_time < block1.to_time:
						frappe.throw(_(
							"Block {block1} ({start1}–{end1}) and Block {block2} ({start2}–{end2}) on Rotation Day {day} have overlapping times."
						).format(
							block1=block1.block_number,
							start1=block1.from_time,
							end1=block1.to_time,
							block2=block2.block_number,
							start2=block2.from_time,
							end2=block2.to_time,
							day=rotation_day
						))


	@frappe.whitelist()
	def generate_rotation_days(self):
		"""Generate rotation days based on rotation_days count."""
		
		if not self.rotation_days or self.rotation_days <= 0:
			frappe.throw(_("Please set a valid number of rotation days before generating."))

		# Check existing rotation days
		if self.get("school_schedule_day"):
			frappe.throw(_("Rotation days already exist. If you want to regenerate them, please clear them first "))

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
		self.set("school_schedule_block", [])

	@frappe.whitelist()
	def generate_blocks(self):
		"""Manually generate School Schedule Blocks based on School Schedule Days."""

		if not self.get("school_schedule_day"):
			frappe.throw("No School Schedule Days found. Please generate rotation days first.")

		# Check if blocks already exist in the child table
		if self.get("school_schedule_block"):
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
				block = self.append("school_schedule_block", {})
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
def get_first_academic_term_start(school_calendar):
  # Fetch the academic_year from the selected School Calendar
  academic_year = frappe.db.get_value("School Calendar", school_calendar, "academic_year")
  if not academic_year:
    return None

  # Fetch all Terms for this academic_year, filter to Academic terms only
  terms = frappe.get_all(
    "Term",
    filters={
      "academic_year": academic_year,
      "term_type": "Academic"
    },
    fields=["term_start_date"]
  )

  # Extract start dates and find the earliest
  dates = [getdate(t["term_start_date"]) for t in terms if t["term_start_date"]]
  if not dates:
    return None

  return min(dates)
	