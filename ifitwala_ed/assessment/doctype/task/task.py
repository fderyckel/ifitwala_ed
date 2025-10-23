# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/task/task.py

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe import _
from typing import Optional, Dict

# If you need the school tree guard (AY on parent vs group on leaf)
try:
	from ifitwala_ed.utilities.school_tree import is_descendant
except Exception:
	def is_descendant(*args, **kwargs):
		return True  # soft fallback if util not available in early migrations

def _is_course_scoped_group(group_row: dict) -> bool:
	gb = group_row.get("group_based_on") or ""
	return gb.strip().lower() == "course"




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
				["group_based_on", "course", "school", "academic_year"],
				as_dict=True,
			) or {}

			# If the group is course-scoped, ensure its course matches the task course (when both present)
			if _is_course_scoped_group(g):
				if g.get("course") and self.course and g["course"] != self.course:
					frappe.throw(_("Selected Student Group belongs to a different Course."))

			# Tree guard: group school must be the same as task.school or a descendant (when both present)
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

		# --- Duplicate guard (same group + lesson + title + due_date) ---
		# Only run when we have enough context; also allow edits that don't change keys
		if self.student_group and self.title:
			self.validate_no_identical_clone()

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

	def validate_no_identical_clone(self) -> None:
		"""Disallow an identical Task for the same student_group + lesson + title + due_date.
		Excludes self when updating an existing Task.
		"""
		# Build filters
		filters = [
			["Task", "student_group", "=", self.student_group],
			["Task", "title", "=", self.title],
		]
		# lesson may be optional; include when present
		if self.lesson:
			filters.append(["Task", "lesson", "=", self.lesson])

		# due_date match: either exact datetime or both unset/null
		if self.due_date:
			filters.append(["Task", "due_date", "=", self.due_date])
		else:
			filters.append(["Task", "due_date", "is", "not set"])

		# Exclude current document if it exists (updates)
		if self.name:
			filters.append(["Task", "name", "!=", self.name])

		exists = frappe.get_all("Task", filters=filters, fields=["name"], limit=1)
		if exists:
			frappe.throw(_("A similar Task already exists for this group with the same due date: {0}")
				.format(exists[0]["name"]))



@frappe.whitelist()
def duplicate_for_group(
	source_task: str,
	new_student_group: str,
	available_from: Optional[str] = None,
	due_date: Optional[str] = None,
	available_until: Optional[str] = None,
	is_published: Optional[int] = None
) -> dict:
	"""Clone a Task to a new student_group with optional new dates.
	Returns {"name": <new_task_name>}.
	"""
	if not source_task or not new_student_group:
		frappe.throw(_("source_task and new_student_group are required"))

	src = frappe.get_doc("Task", source_task)

	# Fetch school/program/ay from Student Group to keep context correct
	sg_school, sg_program, sg_ay = frappe.db.get_value(
		"Student Group",
		new_student_group,
		["school", "program", "academic_year"],
		as_dict=False
	) or (None, None, None)

	# Prepare new doc as shallow clone; avoid copying system fields
	data = src.as_dict()
	for k in ("name", "amended_from", "owner", "creation", "modified", "modified_by", "docstatus"):
		data.pop(k, None)

	# Overwrite audience-specific bits
	data["student_group"] = new_student_group
	data["school"] = sg_school
	data["program"] = sg_program
	data["academic_year"] = sg_ay

	# Dates: use provided overrides, else copy from source
	data["available_from"] = available_from or src.get("available_from")
	data["due_date"] = due_date or src.get("due_date")
	data["available_until"] = available_until or src.get("available_until")

	# is_published override if provided (0/1), else keep source
	if is_published is not None:
		data["is_published"] = int(is_published)

	# Preserve everything else (title, course, learning_unit, lesson, task_type, delivery_type, grading fields, instructions, attachments, etc.)
	new_doc = frappe.get_doc({"doctype": "Task", **data})

	# Run duplicate check against current key for the target group BEFORE insert
	# (mirrors validate_no_identical_clone but we can short-circuit nicer error messages here if needed)
	dup_filters = [
		["Task", "student_group", "=", data.get("student_group")],
		["Task", "title", "=", data.get("title")],
	]
	if data.get("lesson"):
		dup_filters.append(["Task", "lesson", "=", data.get("lesson")])
	if data.get("due_date"):
		dup_filters.append(["Task", "due_date", "=", data.get("due_date")])
	else:
		dup_filters.append(["Task", "due_date", "is", "not set"])
	if frappe.get_all("Task", filters=dup_filters, limit=1):
		frappe.throw(_("A similar Task already exists for this group with the same due date."))

	new_doc.insert(ignore_permissions=False)  # normal perms
	# do not submit automatically; let author review if Task is submittable in your flow

	return {"name": new_doc.name}


@frappe.whitelist()
def prefill_task_students(task: str) -> Dict:
    """
    Insert missing Task Student rows for active students in the Task’s student_group.
    """
    if not task:
        frappe.throw(_("Task is required"))

    doc = frappe.get_doc("Task", task)
    if not doc.student_group:
        frappe.throw(_("Select a Student Group before loading students."))

    s_rows = frappe.get_all(
        "Student Group Student",
        filters={"parent": doc.student_group, "active": 1},
        fields=["student", "student_name"]
    )
    existing = {
        r.student: r.name
        for r in frappe.get_all(
            "Task Student",
            filters={"parent": doc.name, "parenttype": "Task"},
            fields=["name", "student"]
        )
    }

    inserted = 0
    for r in s_rows:
        if r["student"] in existing:
            continue
        ts = frappe.get_doc({
            "doctype": "Task Student",
            "parent": doc.name,
            "parenttype": "Task",
            "parentfield": "task_student",  # ensure this matches Task field name
            "student": r["student"],
            "student_name": r.get("student_name"),
            "status": "Assigned",
            "student_group": doc.student_group,
            "course": doc.course,
            "program": doc.program,
            "academic_year": doc.academic_year,
        })
        ts.insert(ignore_permissions=False)
        inserted += 1

    return {"inserted": inserted, "total": len(s_rows)}


@frappe.whitelist()
def get_criterion_scores_for_student(task: str, student: str) -> Dict:
    """
    Returns existing Task Criterion Score rows for given (task, student)
    so the UI can preload them in the rubric dialog.
    Returns { "rows": [ {assessment_criteria, level, level_points, feedback}, … ] }
    """
    if not (task and student):
        return {"rows": []}

    rows = frappe.get_all(
        "Task Criterion Score",
        filters={"parent": task, "parenttype": "Task", "student": student},
        fields=["assessment_criteria", "level", "level_points", "feedback"]
    )
    return {"rows": rows}


@frappe.whitelist()
def apply_rubric_to_awarded(task: str, students: list) -> Dict:
    """
    For each student in the list, sets mark_awarded = total_mark in Task Student,
    or optionally applies grade scale if configured. Returns counts.
    """
    if not (task and students and isinstance(students, list)):
        frappe.throw(_("Task and students list are required."))

    # Only allow instructors or permitted roles
    frappe.only_for(("Instructor", "Academic Admin", "Curriculum Coordinator", "System Manager"))

    updated = 0
    for student in students:
        ts_name = frappe.db.get_value(
            "Task Student",
            {"parent": task, "parenttype": "Task", "student": student},
            "name"
        )
        if not ts_name:
            continue

        total = frappe.db.get_value(
            "Task Student",
            ts_name,
            "total_mark"
        ) or 0.0

        # You might apply grade scale logic here if needed (future)
        frappe.db.set_value(
            "Task Student",
            ts_name,
            "mark_awarded",
            total,
            update_modified=False
        )
        updated += 1

    return {"updated": updated}



def on_doctype_update():
	frappe.db.add_index("Task", ["student_group", "due_date"])		# Group task lists: student/section views
	frappe.db.add_index("Task", ["school", "academic_year", "is_graded"])	# School/AY analytics: number cards and reports
	frappe.db.add_index("Task", ["course", "due_date"])						# Useful for course dashboards and date queries
	frappe.db.add_index("Task Student", ["parent", "student"])
	frappe.db.add_index("Task Criterion Score", ["parent", "student", "assessment_criteria"])

