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

		if not self.is_new():
			old_criteria = frappe.db.get_value("Task", self.name, "criteria")
			# Previously criteria=1, now criteria=0
			if old_criteria and not self.criteria and self._grading_has_started():
				frappe.throw(_(
					"Criteria-based grading has already started for this Task. "
					"You cannot disable Criteria after grades or rubric scores exist. "
					"Duplicate the Task if you need a different grading mode."
				))

		self._enforce_due_date_if_published()
		self._validate_task_criteria()
		self._validate_task_criterion_scores()
		self._validate_criteria_weighting()
		self._enforce_points_only_bounds()
		self._enforce_criteria_bounds_and_rollup()

		# --- Grading requirements (when graded) ---
		if self.points:
				if not self.grade_scale:
						frappe.throw(_("Grade Scale is required when points are enabled."))
				if not self.max_points or float(self.max_points) <= 0:
						frappe.throw(_("Max Points must be greater than 0 when points are enabled."))

		# --- Submission settings sanity ---
		if (self.submission_required or (self.submission_type and self.submission_type != "None")) and not self.is_graded:
			# Allow ungraded submissions? If not, block; else make this a warning depending on policy.
			pass  # keep permissive for MVP

		if self.attempt_limit and self.attempt_limit < 0:
			frappe.throw(_("Attempt Limit cannot be negative."))

		self._validate_task_students()

		# --- Duplicate guard (same group + lesson + title + due_date) ---
		# Only run when we have enough context; also allow edits that don't change keys
		if self.student_group and self.title:
			self.validate_no_identical_clone()

	def before_save(self):
		# Keep denorm fresh if group changed or cleared
		self._denorm_from_group()
		self.status = self._compute_status()		# Compute status (Draft/Published/Open/Closed) for task
		self._snapshot_task_criteria()
		self._update_task_student_statuses()    # status engine for Task Student rows


	def _enforce_due_date_if_published(self):
		"""
		Enforce that any Task that is visible to students (Published/Open)
		or explicitly marked as is_published must have a Due Date.

		We intentionally compute the effective status here instead of relying
		on self.status, because validate() can run before before_save()
		has written the status field.
		"""
		visible_states = {"Published", "Open"}

		# Compute effective status based on current fields
		effective_status = self._compute_status()

		if (effective_status in visible_states or self.is_published) and not self.due_date:
			frappe.throw(_("Due Date is required when a Task is Published or Open."))

	# --- add inside Task class in task.py ---

	def _grading_has_started(self) -> bool:
		"""
		Return True if there is any meaningful grading activity:
		- On Task Student: marks, feedback, completion, visibility, or non-Assigned status.
		- On Task Criterion Score: chosen level OR non-zero level_points.
		"""
		# Check Task Student rows
		for row in (self.get("task_student") or []):
			if (row.get("mark_awarded") not in (None, "")) \
				or (row.get("total_mark") not in (None, "")) \
				or (row.get("feedback") or "").strip() \
				or (row.get("complete") or 0) \
				or (row.get("visible_to_student") or 0) \
				or (row.get("visible_to_guardian") or 0) \
				or (row.get("status") not in (None, "", "Assigned")):
				return True

		# Check rubric rows
		for r in (self.get("task_criterion_score") or []):
			level = getattr(r, "level", None)
			points = getattr(r, "level_points", None)
			rubric_feedback = (getattr(r, "feedback", "") or "").strip()

			try:
				points_val = float(points) if points not in (None, "") else 0.0
			except Exception:
				points_val = 0.0

			if level or points_val != 0.0 or rubric_feedback:
				return True

		return False

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

	def _enforce_points_only_bounds(self):
		"""
		If the Task has NO criteria, clamp each Task Student's total_mark / mark_awarded:
			0 ≤ value ≤ max_points (if max_points > 0), otherwise prevent negatives only.

		Important: do NOT auto-fill empty marks with 0.0 - we only clamp values the
		teacher has actually entered.
		"""
		# Any criteria? then skip – rubric flow handles totals.
		if any(getattr(r, "assessment_criteria", None) for r in (self.get("assessment_criteria") or [])):
			return

		cap = float(self.max_points or 0)

		def clamp(val):
			try:
				v = float(val)
			except Exception:
				return val  # if it's not numeric, leave it as-is
			if cap > 0:
				if v < 0: return 0.0
				if v > cap: return cap
				return v
			# no cap set -> just prevent negatives
			return 0.0 if v < 0 else v

		for row in (self.get("task_student") or []):
			for fieldname in ("total_mark", "mark_awarded"):
				raw = row.get(fieldname)
				# Only clamp if there is actually something entered
				if raw in (None, ""):
					continue
				new_val = clamp(raw)
				if new_val != raw:
					setattr(row, fieldname, new_val)

	def _enforce_criteria_bounds_and_rollup(self):
		"""
		Clamp Task Criterion Score.level_points within [0, criteria_max_points] for criteria-based tasks,
		then recompute Task Student totals for affected students.
		No effect if the Task has no criteria rows.
		"""
		crit_rows = self.get("assessment_criteria") or []
		if not crit_rows:
			return  # points-only mode handled elsewhere

		# Build snapshot map from Task child table (fast; no joins)
		crit_caps = {}
		for r in crit_rows:
			crit_id = getattr(r, "assessment_criteria", None)
			if not crit_id:
				continue
			crit_caps[crit_id] = float(getattr(r, "criteria_max_points", 0) or 0)

		# Nothing to clamp if we have no caps
		if not crit_caps:
			return

		score_rows = self.get("task_criterion_score") or []
		if not score_rows:
			return

		impacted_students = set()
		for row in score_rows:
			crit_id = getattr(row, "assessment_criteria", None)
			if not crit_id:
				continue
			cap = crit_caps.get(crit_id, 0.0)
			# normalize numeric
			try:
				val = float(getattr(row, "level_points", 0) or 0)
			except Exception:
				val = 0.0
			# clamp: 0 ≤ level_points ≤ cap (if cap>0); otherwise just prevent negatives
			if cap > 0:
				new_val = max(0.0, min(val, cap))
			else:
				new_val = 0.0 if val < 0 else val

			if new_val != val:
				row.level_points = new_val  # mutate child; Frappe will persist on save
				if getattr(row, "student", None):
					impacted_students.add(row.student)
			else:
				if getattr(row, "student", None):
					# still mark as impacted so totals stay up-to-date if caps changed
					impacted_students.add(row.student)

		# Recompute totals for all impacted students
		if impacted_students:
			for stu in impacted_students:
				_recompute_student_totals(self.name, stu)

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

	def _update_task_student_statuses(self) -> None:
		"""
		Deterministically update Task Student.status for each child row based on the Task
		and row fields. Idempotent; safe to call on every save.

		Rules:
		- Returned: visible_to_student or visible_to_guardian
		- Graded: binary+complete OR mark_awarded set OR feedback non-empty
		- In Progress (criteria): at least one rubric row for this student with a chosen level
		  or a non-zero level_points
		- In Progress (points-only): total_mark entered but mark_awarded still empty
		- Assigned: everything else
		"""
		# --- Criteria activity map -------------------------------------------
		has_criteria = any(
			getattr(r, "assessment_criteria", None)
			for r in (self.get("assessment_criteria") or [])
		)

		rubric_by_student = set()
		if has_criteria:
			for r in (self.get("task_criterion_score") or []):
				if not getattr(r, "student", None):
					continue

				level = getattr(r, "level", None)
				points = getattr(r, "level_points", None)
				# normalize numeric
				try:
					points_val = float(points) if points not in (None, "") else 0.0
				except Exception:
					points_val = 0.0

				# "Meaningful work" on the rubric:
				# - a level has been selected OR
				# - level_points is non-zero
				if level or points_val != 0.0:
					rubric_by_student.add(r.student)

		# --- Per-student status engine ---------------------------------------
		for row in (self.get("task_student") or []):
			# Visibility -> Returned
			if (row.get("visible_to_student") or 0) or (row.get("visible_to_guardian") or 0):
				new_status = "Returned"

			# Graded conditions
			elif self.binary and (row.get("complete") or 0):
				new_status = "Graded"
			elif row.get("mark_awarded") not in (None, ""):
				new_status = "Graded"
			elif (row.get("feedback") or "").strip():
				new_status = "Graded"

			# In Progress conditions (work started but not finalized)
			elif has_criteria and (row.get("student") in rubric_by_student):
				# Criteria-based task: rubric edits without final grade
				new_status = "In Progress"
			elif not has_criteria and (
				row.get("total_mark") not in (None, "")
				and row.get("mark_awarded") in (None, "")
			):
				# Points-only: teacher started scoring in total_mark but hasn't finalized mark_awarded
				new_status = "In Progress"

			else:
				new_status = "Assigned"

			# Apply only if changed
			if row.get("status") != new_status:
				row.status = new_status

	## In class helpers
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

	def _validate_task_criteria(self) -> None:
		"""
		When criteria grading is enabled (criteria == 1):

		1) Require at least one Assessment Criteria row.
		2) Require a Course.
		3) Enforce that each selected criteria belongs to the Course via
		   Course Assessment Criteria child table.
		"""
		if not self.criteria:
			return

		rows = self.get("assessment_criteria") or []
		if not rows:
			frappe.throw(_("At least one Assessment Criteria row is required when Criteria is enabled."))

		if not self.course:
			frappe.throw(_("Course is required when Criteria grading is enabled."))

		# Allowed criteria from Course → Course Assessment Criteria
		allowed = set(
			frappe.get_all(
				"Course Assessment Criteria",
				filters={"parent": self.course},
				pluck="assessment_criteria",
			)
		)

		if not allowed:
			frappe.throw(
				_("Course {0} has no linked Assessment Criteria. "
				  "Add criteria on the Course before using Criteria grading.").format(self.course)
			)

		illegal = []
		for r in rows:
			crit = getattr(r, "assessment_criteria", None)
			if not crit:
				continue
			if crit not in allowed:
				illegal.append(crit)

		if illegal:
			frappe.throw(
				_("The following Assessment Criteria are not linked to Course {0}: {1}")
				.format(self.course, ", ".join(sorted(illegal)))
			)

	def _validate_task_criterion_scores(self) -> None:
		"""
		Keep Task Criterion Score in sync with Task:

		- If criteria == 0 → there should be no rubric rows.
		- If criteria == 1:
			* Each rubric row.student must exist in Task Student.
			* Each rubric row.assessment_criteria must be one of the Task.assessment_criteria.
			* At most one row per (student, assessment_criteria).
		"""
		rows = self.get("task_criterion_score") or []
		if not rows:
			return

		# If criteria is OFF but rubric rows exist, that's an inconsistent state.
		if not self.criteria:
			frappe.throw(
				_(
					"Task has rubric scores but Criteria is disabled. "
					"Either re-enable Criteria or clear the rubric rows."
				)
			)

		# Build allowed student + criteria sets from *this* Task
		ts_rows = self.get("task_student") or []
		allowed_students = {getattr(r, "student", None) for r in ts_rows if getattr(r, "student", None)}

		ac_rows = self.get("assessment_criteria") or []
		allowed_criteria = {
			getattr(r, "assessment_criteria", None)
			for r in ac_rows
			if getattr(r, "assessment_criteria", None)
		}

		if not allowed_criteria:
			frappe.throw(
				_("Task has rubric scores but no Assessment Criteria rows. "
				  "Add criteria to the Task or clear rubric scores.")
			)

		seen_pairs = set()
		for idx, r in enumerate(rows, start=1):
			stu = getattr(r, "student", None)
			crit = getattr(r, "assessment_criteria", None)

			# Student must be present and in Task Student table
			if not stu:
				frappe.throw(
					_("Row {0} in Task Criterion Score has no student.").format(idx)
				)
			if stu not in allowed_students:
				frappe.throw(
					_("Student {0} in rubric row {1} is not in Task Student.")
					.format(stu, idx)
				)

			# Criterion must be present and belong to this Task
			if not crit:
				frappe.throw(
					_("Row {0} in Task Criterion Score has no Assessment Criteria.").format(idx)
				)
			if crit not in allowed_criteria:
				frappe.throw(
					_("Assessment Criteria {0} in rubric row {1} is not linked on this Task.")
					.format(crit, idx)
				)

			# No duplicates per (student, criterion)
			key = (stu, crit)
			if key in seen_pairs:
				frappe.throw(
					_(
						"Duplicate rubric entry for Student {0} and Criteria {1} "
						"in Task Criterion Score."
					).format(stu, crit)
				)
			seen_pairs.add(key)

	def _validate_task_students(self) -> None:
		"""
		Enforce:
		1) Each student appears at most once in Task Student child table.
		2) Each student belongs to this Task's student_group as an *active* member.
		"""
		rows = self.get("task_student") or []
		if not rows:
			return

		# If for some reason student_group is missing, the doc should already be failing elsewhere.
		# Don't try to be clever here.
		if not self.student_group:
			return

		# Build membership set: active students in this Student Group
		members = {
			r["student"]
			for r in frappe.get_all(
				"Student Group Student",
				filters={"parent": self.student_group, "active": 1},
				fields=["student"],
			)
			if r.get("student")
		}

		seen = set()
		for idx, row in enumerate(rows, start=1):
			stu = getattr(row, "student", None)
			if not stu:
				continue

			# 1) No duplicates
			if stu in seen:
				frappe.throw(
					_(
						"Student {0} is listed more than once in Task Student (row {1}). "
						"Each student can appear only once."
					).format(stu, idx)
				)
			seen.add(stu)

			# 2) Must belong to the group (active only)
			if stu not in members:
				frappe.throw(
					_(
						"Student {0} is not an active member of Student Group {1}. "
						"You can only add students from the Task’s Student Group."
					).format(stu, self.student_group)
				)





def _recompute_student_totals(task: str, student: str) -> None:
	"""
	Rolls up Task Criterion Score rows for (task, student) into Task Student.
	Uses weighting if any criteria on the Task have criteria_weighting > 0;
	otherwise uses native unweighted sum.
	"""
	task_doc = frappe.get_doc("Task", task)

	# Build a snapshot dict from Task.assessment_criteria (no extra lookups per score row)
	crit_meta = {}
	for r in (task_doc.get("assessment_criteria") or []):
		if not r.assessment_criteria:
			continue
		crit_meta[r.assessment_criteria] = {
			"maxp": float(r.get("criteria_max_points") or 0),
			"w": float(r.get("criteria_weighting") or 0),
		}

	# Fetch this student's rubric rows
	rows = frappe.get_all(
		"Task Criterion Score",
		filters={"parent": task, "parenttype": "Task", "student": student},
		fields=["assessment_criteria", "level_points"]
	)

	if not rows:
		# Still update Task Student to a clean state if present
		ts = frappe.get_all("Task Student",
			filters={"parent": task, "parenttype": "Task", "student": student},
			fields=["name"], limit=1)
		if ts:
			frappe.db.set_value("Task Student", ts[0]["name"], {
				"total_mark": 0.0,
				"out_of": 0.0,
				"percentage": None,
				"updated_on": frappe.utils.now_datetime()
			}, update_modified=False)
		return

	use_weighting = any((crit_meta.get(r["assessment_criteria"], {}).get("w", 0) or 0) > 0 for r in rows)

	if use_weighting:
		pct = 0.0
		for r in rows:
			meta = crit_meta.get(r["assessment_criteria"], {})
			cmax = meta.get("maxp", 0.0) or 0.0
			w = (meta.get("w", 0.0) or 0.0) / 100.0
			lp = float(r.get("level_points") or 0.0)
			if cmax > 0 and w > 0:
				pct += (lp / cmax) * w
		pct *= 100.0
		out_of = float(task_doc.max_points or 0.0)
		total = (pct * out_of / 100.0) if out_of > 0 else 0.0
	else:
		total = 0.0
		out_of = 0.0
		for r in rows:
			meta = crit_meta.get(r["assessment_criteria"], {})
			out_of += float(meta.get("maxp") or 0.0)
			total += float(r.get("level_points") or 0.0)
		pct = (total / out_of * 100.0) if out_of > 0 else None

	ts = frappe.get_all("Task Student",
		filters={"parent": task, "parenttype": "Task", "student": student},
		fields=["name"], limit=1)
	if ts:
		frappe.db.set_value("Task Student", ts[0]["name"], {
			"total_mark": total,
			"out_of": out_of,
			"percentage": pct,
			"updated_on": frappe.utils.now_datetime()
		}, update_modified=False)


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
def recompute_student_totals(task: str, student: str) -> Dict:
	"""Public hook to roll up rubric rows to Task Student for one learner."""
	if not (task and student):
		frappe.throw(_("Task and Student are required."))
	frappe.has_permission(doctype="Task", doc=task, ptype="write", throw=True)
	_recompute_student_totals(task, student)
	return {"ok": True}


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

	We deliberately do NOT denormalize course/program/academic_year/student_group
	onto Task Student. Those remain on the Task parent only.
	"""
	if not task:
		frappe.throw(_("Task is required"))

	doc = frappe.get_doc("Task", task)
	if not doc.student_group:
		frappe.throw(_("Select a Student Group before loading students."))

	s_rows = frappe.get_all(
		"Student Group Student",
		filters={"parent": doc.student_group, "active": 1},
		fields=["student", "student_name"],
	)
	existing = {
		r.student: r.name
		for r in frappe.get_all(
			"Task Student",
			filters={"parent": doc.name, "parenttype": "Task"},
			fields=["name", "student"],
		)
	}

	inserted = 0
	for r in s_rows:
		if r["student"] in existing:
			continue

		ts = frappe.get_doc(
			{
				"doctype": "Task Student",
				"parent": doc.name,
				"parenttype": "Task",
				"parentfield": "task_student",  # ensure this matches Task field name
				"student": r["student"],
				"student_name": r.get("student_name"),
				"status": "Assigned",
				# NO course/program/academic_year/student_group denorm here by design
			}
		)
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

		raw_val = row[0].get("total_mark")
		raw = (str(raw_val) if raw_val is not None else "").strip()
		try:
			val = float(raw) if raw != "" else 0.0
		except Exception:
			val = 0.0

		frappe.db.set_value("Task Student", row[0]["name"], "mark_awarded", val, update_modified=False)
		updated += 1

	return {"updated": updated}

@frappe.whitelist()
def prefill_task_rubrics(task: str) -> dict:
	"""
	Whitelisted helper to (re)seed rubric rows for a Task.

	Used when Criteria is turned ON after students were already loaded, or
	whenever you want to refresh the student×criteria grid.
	"""
	if not task:
		frappe.throw(_("Task is required"))

	task_doc = frappe.get_doc("Task", task)
	res = _prefill_task_rubrics(task_doc)
	return res


def on_doctype_update():
	frappe.db.add_index("Task", ["student_group", "due_date"])		# Group task lists: student/section views
	frappe.db.add_index("Task", ["school", "academic_year", "is_graded"])	# School/AY analytics: number cards and reports
	frappe.db.add_index("Task", ["course", "due_date"])						# Useful for course dashboards and date queries
	frappe.db.add_index("Task Student", ["parent", "student"])
	frappe.db.add_index("Task Criterion Score", ["parent", "student", "assessment_criteria"])

