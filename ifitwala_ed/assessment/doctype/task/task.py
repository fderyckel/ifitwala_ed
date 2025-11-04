# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/task/task.py

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime
from frappe import _
from typing import Optional, Dict, List

# If you need the school tree guard (AY on parent vs group on leaf)
try:
	from ifitwala_ed.utilities.school_tree import is_descendant
except Exception:
	def is_descendant(*args, **kwargs):
		return True  # soft fallback if util not available in early migrations

def _is_course_scoped_group(group_row: dict) -> bool:
	gb = group_row.get("group_based_on") or ""
	return gb.strip().lower() == "course"

def _as_dt(val):
	"""None-safe coercion of Frappe Datetime field values to datetime."""
	return get_datetime(val) if val else None


class Task(Document):

	def before_insert(self):
		# Ensure Posted Date is set if schema default didn't apply (programmatic inserts)
		if not self.posted_date:
			self.posted_date = now_datetime()
		# Denorm from student_group (cheap, read-only fields in schema)
		self._denorm_from_group()

	def validate(self):
		self._validate_learning_unit_belongs_to_course()
		# --- Date sanity (parent window) ---
		start_dt = _as_dt(self.available_from)
		end_dt = _as_dt(self.available_until)
		if start_dt and end_dt and start_dt > end_dt:
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

		self._enforce_due_date_if_published()
		self._validate_criteria_weighting()


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
		self._snapshot_task_criteria()

	def _enforce_due_date_if_published(self):
			# If status implies visibility, enforce due_date
			visible_states = {'Published', 'Open'}
			if (self.status in visible_states or self.is_published) and not self.due_date:
				frappe.throw(_("Due Date is required when a Task is Published or Open."))

# --- add inside Task class in task.py ---

	def _validate_criteria_weighting(self):
		"""Ensure Task.assessment_criteria weightings are sensible."""
		rows = self.get("assessment_criteria") or []
		if not rows:
			return

		weights = []
		for r in rows:
			# Percent fields may be None; coerce to float
			w = float(r.get("criteria_weighting") or 0)
			if w < 0:
				frappe.throw(_("Criteria weighting cannot be negative."))
			weights.append(w)

		total = sum(weights)

		# If any weighting is used (>0 anywhere), enforce hard ceiling 100%
		if any(w > 0 for w in weights):
			if total > 100.0000001:
				frappe.throw(_("Sum of criteria weighting is {0:.2f}%, which exceeds 100%.")
					.format(total))
			# Soft nudge if not exactly 100%
			if 0 < total < 99.999:
				frappe.msgprint(
					_("Sum of criteria weighting is {0:.2f}%. Consider making it 100% for clarity.")
					.format(total),
					indicator="orange"
				)

	def _validate_learning_unit_belongs_to_course(self):
		if not self.learning_unit:
			return
		lu_course = frappe.db.get_value("Learning Unit", self.learning_unit, "course")
		if not lu_course:
			frappe.throw(f"Learning Unit <b>{self.learning_unit}</b> has no Course set.")
		if self.course and lu_course != self.course:
			frappe.throw(
				f"Learning Unit <b>{self.learning_unit}</b> belongs to Course "
				f"<b>{lu_course}</b> which does not match this Task’s Course <b>{self.course}</b>."
			)
		# If course is somehow still empty (e.g., manual entry), set it safely
		if not self.course:
			self.course = lu_course

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
		start = _as_dt(self.available_from)
		end = _as_dt(self.available_until)

		if start and now < start:
			return "Published"
		if end and now > end:
			return "Closed"
		return "Open"

	def _snapshot_task_criteria(self):
		for r in (self.get("assessment_criteria") or []):
			if not r.assessment_criteria:
				continue
			maxp = frappe.db.get_value(
				"Assessment Criteria", r.assessment_criteria, "maximum_mark"
			)
			r.criteria_max_points = float(maxp or 0)


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


def _prefill_task_rubrics(task_doc) -> dict:
	"""
	For each student already in Task Student, ensure one Task Criterion Score row exists
	per Assessment Criteria selected on the Task. Initialize with level_points = 0.
	No weighting math here; this step only creates missing rows.
	"""
	# 1) Criteria chosen on this Task (from Assessment Criteria child table)
	crit_ids = [
		r.assessment_criteria
		for r in (task_doc.get("assessment_criteria") or [])
		if r.assessment_criteria
	]
	if not crit_ids:
		return {"created": 0, "students": 0, "criteria": 0}

	# 2) Students already loaded on this Task
	students = frappe.get_all(
		"Task Student",
		filters={"parent": task_doc.name, "parenttype": "Task"},
		fields=["student"]
	)
	if not students:
		return {"created": 0, "students": 0, "criteria": len(crit_ids)}

	# 3) Existing rubric rows (to avoid duplicates)
	existing_pairs = {
		(r.student, r.assessment_criteria)
		for r in frappe.get_all(
			"Task Criterion Score",
			filters={"parent": task_doc.name, "parenttype": "Task"},
			fields=["student", "assessment_criteria"]
		)
	}

	# 4) Insert missing (student × criterion) rows
	created = 0
	for s in students:
		for crit in crit_ids:
			key = (s["student"], crit)
			if key in existing_pairs:
				continue
			frappe.get_doc({
				"doctype": "Task Criterion Score",
				"parent": task_doc.name,
				"parenttype": "Task",
				"parentfield": "task_criterion_score",
				"student": s["student"],
				"assessment_criteria": crit,
				"level": None,
				"level_points": 0.0
			}).insert(ignore_permissions=False)
			created += 1

	return {"created": created, "students": len(students), "criteria": len(crit_ids)}

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

    result = {"inserted": inserted, "total": len(s_rows)}

    # also ensure rubric rows exist for each student × criterion
    doc.reload()  # make sure child tables are fresh
    rub = _prefill_task_rubrics(doc)
    result.update({"rubric_rows_created": rub.get("created", 0)})

    return result


@frappe.whitelist()
def get_criterion_scores_for_student(task: str, student: str) -> Dict:
	"""Return existing rubric rows so the dialog can preload them."""
	if not (task and student):
		return {"rows": []}

	# Basic permission: ensure current user can read this Task
	frappe.has_permission(doctype="Task", doc=task, ptype="read", throw=True)

	rows = frappe.get_all(
		"Task Criterion Score",
		filters={"parent": task, "parenttype": "Task", "student": student},
		fields=["assessment_criteria", "level", "level_points", "feedback"],
		order_by="idx asc"
	)
	return {"rows": rows}


@frappe.whitelist()
def apply_rubric_to_awarded(task: str, students: List[str]) -> Dict:
	"""
	Set mark_awarded = float(total_mark) for each selected student.
	If total_mark (Data) is empty/non-numeric, use 0.0.
	"""
	if not (task and isinstance(students, list) and students):
		frappe.throw(_("Task and a non-empty students list are required."))

	frappe.only_for(("Instructor", "Academic Admin", "Curriculum Coordinator", "System Manager"))
	frappe.has_permission(doctype="Task", doc=task, ptype="write", throw=True)

	updated = 0
	for student in students:
		row = frappe.get_all(
			"Task Student",
			filters={"parent": task, "parenttype": "Task", "student": student},
			fields=["name", "total_mark"],
			limit=1
		)
		if not row:
			continue

		raw = (row[0].get("total_mark") or "").strip()
		try:
			val = float(raw) if raw != "" else 0.0
		except Exception:
			val = 0.0

		frappe.db.set_value("Task Student", row[0]["name"], "mark_awarded", val, update_modified=False)
		updated += 1

	return {"updated": updated}


def on_doctype_update():
	frappe.db.add_index("Task", ["student_group", "due_date"])		# Group task lists: student/section views
	frappe.db.add_index("Task", ["school", "academic_year", "is_graded"])	# School/AY analytics: number cards and reports
	frappe.db.add_index("Task", ["course", "due_date"])						# Useful for course dashboards and date queries
	frappe.db.add_index("Task Student", ["parent", "student"])
	frappe.db.add_index("Task Criterion Score", ["parent", "student", "assessment_criteria"])

