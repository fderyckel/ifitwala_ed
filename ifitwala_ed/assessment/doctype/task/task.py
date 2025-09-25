# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe import _
from typing import Optional

# If you need the school tree guard (AY on parent vs group on leaf)
try:
	from ifitwala_ed.utilities.school_tree import is_descendant
except Exception:
	def is_descendant(*args, **kwargs):
		return True  # soft fallback if util not available in early migrations

class Task(Document):
	def before_insert(self):
		# Ensure Posted Date is set if schema default didn't apply (programmatic inserts)
		if not self.posted_date:
			self.posted_date = now_datetime()
		# Denorm from student_group (cheap, read-only fields in schema)
		self._denorm_from_group()

	def validate(self):
		# --- Date sanity (parent window) ---
		if self.available_from and self.available_until and self.available_from > self.available_until:
			frappe.throw(_("Available From must be before Available Until."))

		# Prevent-late requires a due date
		if self.prevent_late_submission and not self.due_date:
			frappe.throw(_("Prevent Late Submission requires a Due Date."))

		# --- Publish guard ---
		if self.is_published and not self.student_group:
			frappe.throw(_("Select a Student Group before publishing."))

		# --- Group & course consistency ---
		if self.student_group:
			g = frappe.db.get_value(
				"Student Group",
				self.student_group,
				["group_type", "course", "school", "academic_year"],
				as_dict=True,
			) or {}

			# If the group is course-scoped, its course must match the task course
			if (g.get("group_type") or "").lower() == "course":
				if g.get("course") and self.course and g["course"] != self.course:
					frappe.throw(_("Selected Student Group belongs to a different Course."))

			# Optional tree guard: group school should be same or descendant of task.school (if both present)
			if self.school and g.get("school") and not is_descendant(
				ancestor=self.school, node=g["school"], include_equal=True
			):
				frappe.throw(_("Student Group’s school must be {0} or its descendant.").format(self.school))

		# --- Grading requirements (when graded) ---
		if self.is_graded:
			if not self.grade_scale:
				frappe.throw(_("Grade Scale is required when the task is graded."))
			if self.max_points in (None, 0):
				frappe.throw(_("Max Points must be greater than 0 for graded tasks."))

		# --- Submission settings sanity ---
		if (self.submission_required or (self.submission_type and self.submission_type != "None")) and not self.is_graded:
			# Allow ungraded submissions? If not, block; else make this a warning depending on policy.
			pass  # keep permissive for MVP

		if self.attempt_limit and self.attempt_limit < 0:
			frappe.throw(_("Attempt Limit cannot be negative."))

	def before_save(self):
		# Keep denorm fresh if group changed or cleared
		self._denorm_from_group()

		# Compute status (Draft/Published/Open/Closed) from publish flag + window
		self.status = self._compute_status()

	def _denorm_from_group(self) -> None:
		"""Best-effort, cheap denormalization from Student Group. Fields are read-only in the schema."""
		if not self.student_group:
			return

		# Pull what you actually store on Student Group (cheap lookups)
		school, program, ay, group_course = frappe.db.get_value(
			"Student Group",
			self.student_group,
			["school", "program", "academic_year", "course"],
			as_dict=False
		) or (None, None, None, None)

		# Write denorms
		self.school = school
		self.program = program
		self.academic_year = ay

		# If task.course is empty and group has a course, adopt it
		if not self.course and group_course:
			self.course = group_course

	def _compute_status(self) -> str:
		"""Draft if not published; Published if before window; Open during window; Closed after."""
		if not self.is_published:
			return "Draft"

		now = now_datetime()
		start = self.available_from
		end = self.available_until

		if start and now < start:
			return "Published"
		if end and now > end:
			return "Closed"
		return "Open"


def on_doctype_update():
	# Course task lists: common instructor view
	frappe.db.add_index("Task", ["course", "is_published", "due_date"])

	# Group task lists: student/section views
	frappe.db.add_index("Task", ["student_group", "is_published", "due_date"])

	# School/AY analytics: number cards and reports
	frappe.db.add_index("Task", ["school", "academic_year", "is_graded"])

	# Fast status + overdue filtering
	frappe.db.add_index("Task", ["status", "due_date"])