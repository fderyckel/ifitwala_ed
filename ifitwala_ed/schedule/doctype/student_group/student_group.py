# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifiwala_ed/schedule/doctype/student_group/student_group.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_link_to_form, get_datetime, format_datetime

from ifitwala_ed.schedule.schedule_utils import get_conflict_rule, get_rotation_dates
from ifitwala_ed.schedule.student_group_scheduling import check_slot_conflicts
from ifitwala_ed.utilities.school_tree import get_ancestor_schools
from ifitwala_ed.schedule.attendance_utils import invalidate_meeting_dates
from ifitwala_ed.utilities.location_utils import find_room_conflicts

from ifitwala_ed.schedule.student_group_employee_booking import (
	rebuild_employee_bookings_for_student_group,
)

class OverlapError(frappe.ValidationError):
	"""Raised when a scheduling conflict violates the hard rule."""
	pass


class StudentGroup(Document):
	def autoname(self):
		if self.group_based_on == "Course" or self.group_based_on == "Activity":
			if self.term:
				self.name = self.student_group_abbreviation + "/" + self.term
			else:
				self.name = self.student_group_abbreviation + "/" + self.academic_year
		elif self.group_based_on == "Cohort":
			self.name = self.student_group_abbreviation + "/" + self.cohort
		else:
			self.name = self.student_group_abbreviation

	def validate(self):
		if self.term:
			self.validate_term()

		self._derive_program_from_offering()
		self._validate_ay_in_offering_spine()
		self._enforce_school_rules()
		self._validate_course_scoping()
		self._validate_overlap_conflicts()

		self.validate_mandatory_fields()
		self.validate_size()
		self.validate_students()
		self.validate_and_set_child_table_fields()
		self.validate_duplicate_students()
		self.validate_rotation_clashes()
		self.validate_location_capacity()


		########
		# Auto-fill school_schedule if missing and based on course
		if self.group_based_on in {"Course", "Activity"} and not self.school_schedule:
			# Uses offering/school/AY resolution + ancestor checks
			ss = self._get_school_schedule()
			self.school_schedule = ss.name

		frappe.logger("ifitwala.materialization").warning({
			"event": "student_group_rebuild_triggered",
			"student_group": self.name,
			"hook": "on_update",
		})

		############
		self._validate_schedule_rows()
		# Cross-object room conflicts (Student Groups ↔ Meetings / Events)
		self.validate_location_conflicts_absolute()

		if self.group_based_on in ["Course", "Activity"]:
			if self.term:
				self.title = self.student_group_abbreviation + "/" + self.term
			else:
				self.title = self.student_group_abbreviation + "/" + self.academic_year
		elif self.group_based_on == "Cohort":
			self.title = self.student_group_abbreviation + "/" + self.cohort
		else:
			self.title = self.student_group_abbreviation

	def before_save(self):
		"""
		Detect changes efficiently:
		- active students added/removed (child: students)
		- instructor identity changes (child: instructors) → triggers re-sync for all current active students
		"""
		old = self.get_doc_before_save()
		if not old:
			# no diff on first save
			self.flags._sg_students_added = set()
			self.flags._sg_students_removed = set()
			self.flags._sg_instructors_changed = False
			# meeting dates: nothing cached yet on first save
			self.flags._sg_meeting_dates_changed = False
			self.flags._sg_schedule_changed = bool(self.student_group_schedule)
			return

		# ----- students (active only) -----
		def active_students(doc):
			return {
				(r.student or "").strip()
				for r in (doc.students or [])
				if getattr(r, "student", None) and cint(getattr(r, "active", 1))
			}

		prev_active = active_students(old)
		curr_active = active_students(self)

		self.flags._sg_students_added = curr_active - prev_active
		self.flags._sg_students_removed = prev_active - curr_active

		# ----- instructors (normalize identity → prefer user_id, fallback to instructor id) -----
		def instructor_keys(doc):
			keys = set()
			for r in (doc.instructors or []):
				emp = (getattr(r, "employee", "") or "").strip()
				uid = (getattr(r, "user_id", "") or "").strip()
				ins = (getattr(r, "instructor", "") or "").strip()
				if emp:
					keys.add(("emp", emp))
				if uid:
					keys.add(("uid", uid))
				elif ins:
					keys.add(("ins", ins))
			return keys

		prev_instr = instructor_keys(old)
		curr_instr = instructor_keys(self)
		self.flags._sg_instructors_changed = (prev_instr != curr_instr)

		# ----- schedule rows (rotation/day/block/location/instructor/employee) -----
		def schedule_keys(doc):
			keys = []
			for r in (doc.student_group_schedule or []):
				rd = getattr(r, "rotation_day", None)
				blk = getattr(r, "block_number", None)
				loc = (getattr(r, "location", "") or "").strip()
				ins = (getattr(r, "instructor", "") or "").strip()
				emp = (getattr(r, "employee", "") or "").strip()
				try:
					rd = int(rd) if rd is not None else None
				except Exception:
					pass
				try:
					blk = int(blk) if blk is not None else None
				except Exception:
					pass
				keys.append((rd, blk, loc, ins, emp))
			return sorted(keys)

		prev_sched = schedule_keys(old)
		curr_sched = schedule_keys(self)
		self.flags._sg_schedule_changed = (prev_sched != curr_sched)

		# ----- MEETING-DATES impact detection (NEW) -----
		def rotation_days_set(doc):
			return {
				int(r.rotation_day)
				for r in (doc.student_group_schedule or [])
				if getattr(r, "rotation_day", None)
			}

		sched_changed = (old.school_schedule or "") != (self.school_schedule or "")
		ay_changed = (old.academic_year or "") != (self.academic_year or "")
		prev_days = rotation_days_set(old)
		curr_days = rotation_days_set(self)

		self.flags._sg_meeting_dates_changed = bool(
			sched_changed or ay_changed or (prev_days != curr_days)
		)

	def after_save(self):
		"""
		Sync SSG access/acks when:
		- students were added/removed, or
		- instructor set changed (mid-year teacher change)
		"""
		added = getattr(self.flags, "_sg_students_added", set()) or set()
		removed = getattr(self.flags, "_sg_students_removed", set()) or set()
		instr_changed = bool(getattr(self.flags, "_sg_instructors_changed", False))
		# sched_changed removed - unused(getattr(self.flags, "_sg_schedule_changed", False))

		if not added and not removed and not instr_changed:
			pass
		else:
			ay = (self.academic_year or "").strip()
			if ay:
				from ifitwala_ed.students.doctype.referral_case.referral_case import _sync_ssg_access_for
				for stu in sorted(added):
					_sync_ssg_access_for(stu, ay, reason="sgs-added")
				for stu in sorted(removed):
					_sync_ssg_access_for(stu, ay, reason="sgs-removed")
				if instr_changed:
					for r in (self.students or []):
						if getattr(r, "student", None) and cint(getattr(r, "active", 1)):
							_sync_ssg_access_for((r.student or "").strip(), ay, reason="sgi-changed")

		# ----- MEETING-DATES invalidation -----
		if bool(getattr(self.flags, "_sg_meeting_dates_changed", False)):
			invalidate_meeting_dates(self.name)

		# cleanup flags
		self.flags._sg_students_added = set()
		self.flags._sg_students_removed = set()
		self.flags._sg_instructors_changed = False
		self.flags._sg_meeting_dates_changed = False
		self.flags._sg_schedule_changed = False

	def on_update(self):
		# Rebuild bookings on every save for Active groups to keep materialized facts in sync.
		if (self.status or "Active") != "Active":
			return

		has_schedule = bool(self.student_group_schedule) or frappe.db.exists(
			"Student Group Schedule",
			{"parent": self.name},
		)
		if not has_schedule:
			return

		rebuild_employee_bookings_for_student_group(self.name)


	##################### VALIDATONS #########################

	def validate_term(self) -> None:
		term_year = frappe.get_doc("Term", self.term)
		if self.academic_year != term_year.academic_year:
			frappe.throw(_("The term {0} does not belong to the academic year {1}.").format(self.term, self.academic_year))

	def validate_mandatory_fields(self) -> None:
		if self.group_based_on == "Course" and not self.course:
			frappe.throw(_("Please select a course."))
		if self.group_based_on == "Cohort" and not self.cohort:
			frappe.throw(_("Please select a cohort."))

	# Throwing message if more students than maximum size in the group
	def validate_size(self):
		if cint(self.maximum_size) < 0:
			frappe.throw(_("Max number of student in this group cannot be negative."))
		if self.maximum_size and len(self.students) > cint(self.maximum_size):
			frappe.throw(_("You can only enroll {0} students in this group.").format(self.maximum_size))

	# you should not be able to make a group that include inactive students.
	# this is to ensure students are still active students (aka not graduated or not transferred, etc.)
	def validate_students(self):
		if not self.students:
			return

		# Skip all validation for "Other"
		if self.group_based_on == "Other":
			return

		student_names = [s.student for s in self.students if s.student]
		if not student_names:
			return

		# Fetch enabled status for all listed students
		enabled_records = frappe.db.get_values(
			"Student",
			{"name": ["in", student_names]},
			["name", "enabled"],
			as_dict=True
		)
		enabled_dict = {rec.name: rec.enabled for rec in enabled_records}

		for student in self.students:
			if not student.student:
				continue

			is_enabled = enabled_dict.get(student.student)
			if is_enabled is None:
				frappe.throw(_("Student data not found for {0}").format(student.student))

			if not is_enabled and student.active:
				frappe.throw(_("{0} - {1} is an inactive student").format(
					student.group_roll_number, student.student_name
				))

			# Enrollment integrity by Program Offering (optional, only if offering is set)
			if self.program_offering:
				if not frappe.db.exists("Program Enrollment", {
					"student": student.student,
					"program_offering": self.program_offering,
					"academic_year": self.academic_year
				}):
					frappe.throw(_("Student {0} ({1}) is not enrolled in the selected Program Offering for academic year {2}.").format(
						student.student_name,
						student.student,
						self.academic_year
					))

			# Cohort check (optional) — still anchored on the same offering+AY
			if self.cohort:
				if not frappe.db.exists("Program Enrollment", {
					"student": student.student,
					"program_offering": self.program_offering,
					"academic_year": self.academic_year,
					"cohort": self.cohort
				}):
					frappe.throw(_("Student {0} ({1}) is not part of the cohort {2} for this Program Offering and Academic Year.").format(
						student.student_name,
						student.student,
						get_link_to_form("Student Cohort", self.cohort)
					))

		if self.group_based_on == "Course" and self.course and self.term:
			for student in self.students:
				if not student.student:
					continue

				# 🔍 Check if already assigned to another Course-based group (same course, year, term)
				conflict_group = frappe.db.sql("""
					SELECT sg.name
					FROM `tabStudent Group` sg
					INNER JOIN `tabStudent Group Student` sgs ON sg.name = sgs.parent
					WHERE sg.name != %(current_group)s
						AND sgs.student = %(student)s
						AND sg.group_based_on = 'Course'
						AND sg.academic_year = %(academic_year)s
						AND sg.course = %(course)s
						AND sg.term = %(term)s
					LIMIT 1
				""", {
					"current_group": self.name,
					"student": student.student,
					"academic_year": self.academic_year,
					"course": self.course,
					"term": self.term
				})

				if conflict_group:
					frappe.throw(_(
						"Student <b>{0} ({1})</b> is already assigned to Course-based group {2} "
						"for <b>{3}</b> during <b>{4}</b>."
					).format(
						student.student_name,
						student.student,
						get_link_to_form("Student Group", conflict_group[0][0]),
						get_link_to_form("Course", self.course),
						get_link_to_form("Term", self.term)
					))

				# Enrollment integrity check: Student must have a Program Enrollment Course entry
				program_clause = "AND pe.program = %(program)s" if self.program else ""
				params = {
					"student": student.student,
					"academic_year": self.academic_year,
					"course": self.course,
					"term": self.term,
				}
				if self.program:
					params["program"] = self.program

				valid_enrollment = frappe.db.sql(f"""
					SELECT 1
					FROM `tabProgram Enrollment` pe
					INNER JOIN `tabProgram Enrollment Course` pec ON pec.parent = pe.name
					WHERE pe.student = %(student)s
						AND pe.academic_year = %(academic_year)s
						{program_clause}
						AND pec.course = %(course)s
						AND pec.term_start = %(term)s
					LIMIT 1
				""", params)

				if not valid_enrollment:
					frappe.throw(_(
						"Student <b>{0} ({1})</b> does not have a valid Program Enrollment for "
						"<b>{2}</b> in term <b>{3}</b>. Please ensure they are enrolled in the course."
					).format(
						student.student_name,
						student.student,
						get_link_to_form("Course", self.course),
						get_link_to_form("Term", self.term)
					))

	# to input the roll number field in child table
	def validate_and_set_child_table_fields(self):
		roll_numbers = [d.group_roll_number for d in self.students if d.group_roll_number]
		max_roll_no = max(roll_numbers) if roll_numbers else 0
		roll_no_list = []
		for d in self.students:
			if not d.student_name:
				d.student_name = frappe.db.get_value("Student", d.student, "student_full_name")
			if not d.group_roll_number:
				max_roll_no += 1
				d.group_roll_number = max_roll_no
			if d.group_roll_number in roll_no_list:
				frappe.throw(_("Duplicate roll number for student {0}").format(d.student_name))
			else:
				roll_no_list.append(d.group_roll_number)

	def validate_duplicate_students(self) -> None:
		"""
		Ensure each student appears at most once in the Student Group Student child table.
		Raises a validation error if the same student id is found on multiple rows.
		"""
		seen = {}  # student_id -> first row idx

		for row in (self.students or []):
			student_id = getattr(row, "student", None)
			if not student_id:
				continue

			if student_id in seen:
				first_idx = seen[student_id]
				frappe.throw(
					_("Student {0} - {1} appears Multiple times in row {2} & {3}")
					.format(student_id, row.student_name, first_idx, row.idx)
				)
			else:
				seen[student_id] = row.idx

	def validate_rotation_clashes(self):
		"""
		Check duplicate use of the same student or instructor within this
		Student Group at the same rotation_day / block_number.

		Room/location conflicts across Student Groups / Meetings / Events are
		now handled by validate_location_conflicts_absolute().
		"""
		key_sets = {
			"student": set(),
			"instructor": set(),
		}

		for row in (self.student_group_schedule or []):
			hash_base = f"{row.rotation_day}:{row.block_number}"

			# students
			for s in (self.students or []):
				if not getattr(s, "student", None):
					continue

				key = f"{hash_base}:{s.student}"
				if key in key_sets["student"]:
					frappe.throw(
						_("Student clash on rotation {0} block {1} ({2})").format(
							row.rotation_day, row.block_number, s.student
						)
					)
				key_sets["student"].add(key)

			# instructors (child table Student Group Instructor)
			for instr in (self.instructors or []):
				identifier = (
					(getattr(instr, "employee", "") or "").strip()
					or (getattr(instr, "instructor", "") or "").strip()
				)
				if not identifier:
					continue

				key = f"{hash_base}:{identifier}"
				if key in key_sets["instructor"]:
					frappe.throw(
						_("Instructor clash on rotation {0} block {1} ({2})").format(
							row.rotation_day, row.block_number, identifier
						)
					)
				key_sets["instructor"].add(key)

	def _validate_overlap_conflicts(self):
		"""
		Enforce that:
		  - No instructor is double-booked in another Student Group
		    at the same rotation_day + block_number.
		  - No student is double-booked in another Student Group
		    at the same rotation_day + block_number.

		Room conflicts are handled separately by the canonical room conflict helper.
		"""

		# Use a plain dict so check_slot_conflicts can be called both from
		# client (JSON) and server (Document).
		conflicts = check_slot_conflicts(self.as_dict()) or {}

		if not conflicts:
			return

		messages = []

		ins_conf = conflicts.get("instructor") or []
		stu_conf = conflicts.get("student") or []

		def _names(payload):
			labels = payload.get("labels") or payload.get("ids") or []
			return ", ".join(label for label in labels if label)

		def _group_links(payload):
			sgs = payload.get("groups") or []
			links = [
				get_link_to_form("Student Group", sg)
				for sg in sgs if sg
			]
			return ", ".join(links) if links else _("another Student Group")

		if ins_conf:
			for payload in ins_conf:
				ins_list = _names(payload)
				rot = payload.get("rotation_day")
				blk = payload.get("block_number")
				sg_links = _group_links(payload)
				messages.append(
					_("Instructor(s) {ins} already booked on rotation day {rot}, block {blk} in {sg}.")
					.format(ins=ins_list, rot=rot, blk=blk, sg=sg_links)
				)

		if stu_conf:
			for payload in stu_conf:
				stu_list = _names(payload)
				rot = payload.get("rotation_day")
				blk = payload.get("block_number")
				sg_links = _group_links(payload)
				messages.append(
					_("Student(s) {stu} already booked on rotation day {rot}, block {blk} in {sg}.")
					.format(stu=stu_list, rot=rot, blk=blk, sg=sg_links)
				)

		if not messages:
			return

		rule = get_conflict_rule()  # "Hard" or "Soft" from School settings

		msg = "<br>".join(messages)
		frappe.msgprint(msg, title=_("Scheduling Conflicts"), indicator="red")

		if rule == "Hard":
			raise OverlapError(msg)

	def validate_location_capacity(self):
		"""Ensure the chosen locations can accommodate the group's active student count.
		- Reads unique Location rows from the schedule child table.
		- Counts only active students in the students child table.
		- Batches Location lookups for efficiency.
		- Enforces capacity only when `maximum_capacity` > 0 (0/None = no limit).
		"""
		# collect unique, non-empty locations from schedule
		locations = {row.location for row in (self.student_group_schedule or []) if row.location}
		if not locations:
			return

		# count active students in group
		active_students = sum(1 for r in (self.students or []) if cint(getattr(r, "active", 1)) == 1)
		# if no students, nothing to validate
		if active_students == 0:
			return

		# fetch capacities in one query
		caps = frappe.get_all(
			"Location",
			filters={"name": ["in", list(locations)]},
			fields=["name", "maximum_capacity"],
			ignore_permissions=True,
		)
		cap_map = {c["name"]: cint(c.get("maximum_capacity") or 0) for c in caps}

		# find any locations where capacity is set (>0) and violated
		over = []
		for loc in locations:
			cap = cap_map.get(loc, 0)
			if cap > 0 and active_students > cap:
				over.append((loc, cap))

		if over:
			lines = "\n".join(
				f"- {loc}: capacity {cap}, active students {active_students}"
				for loc, cap in over
			)
			frappe.throw(
				_("Room capacity exceeded for the following locations:\n{0}").format(lines),
				title=_("Maximum Capacity Exceeded"),
			)

	def _get_school_schedule(self):
		"""
		Resolve the School Schedule used to validate schedule rows.

		Priority:
		1) If an explicit `school_schedule` is set, validate it (AY + school chain) and return it.
		2) Otherwise, auto-pick the first schedule for:
			- Program Offering's school (if present), else
			- Student Group's school (if set), else
			- Academic Year's school
			... including ancestors (via nested set), for the selected Academic Year.
		"""
		if not self.academic_year:
			frappe.throw(_("Please select an Academic Year first."))

		# 1) If user explicitly chose a schedule, validate and return it
		if self.school_schedule:
			ss = frappe.get_cached_doc("School Schedule", self.school_schedule)

			# Validate AY via its calendar
			cal_ay = frappe.db.get_value("School Calendar", ss.school_calendar, "academic_year")
			if cal_ay != self.academic_year:
				frappe.throw(_("Selected School Schedule {0} belongs to Academic Year {1}, not {2}.")
					.format(ss.name, cal_ay or "?", self.academic_year))

			# Validate school chain (schedule's school must be an ancestor (or same) of the base)
			base_school = (
				frappe.db.get_value("Program Offering", self.program_offering, "school") if self.program_offering
				else (self.school or frappe.db.get_value("Academic Year", self.academic_year, "school"))
			)
			if not base_school:
				frappe.throw(_("Cannot resolve a base School from Program Offering / Student Group / Academic Year."))

			allowed = set(get_ancestor_schools(base_school))  # self + parents
			if ss.school not in allowed:
				frappe.throw(_("School Schedule {0} is owned by {1}, which is not in the ancestor chain of {2}.")
					.format(ss.name, ss.school, base_school))

			return ss

		# 2) Auto-pick from the allowed chain for the selected AY
		base_school = (
			frappe.db.get_value("Program Offering", self.program_offering, "school") if self.program_offering
			else (self.school or frappe.db.get_value("Academic Year", self.academic_year, "school"))
		)
		if not base_school:
			frappe.throw(_("Cannot resolve a base School from Program Offering / Student Group / Academic Year."))

		allowed = tuple(get_ancestor_schools(base_school))  # self + parents

		row = frappe.db.sql("""
			SELECT ss.name
			FROM `tabSchool Schedule` ss
			INNER JOIN `tabSchool Calendar` sc ON sc.name = ss.school_calendar
			WHERE ss.school IN %(schools)s
				AND sc.academic_year = %(ay)s
			ORDER BY ss.idx, ss.name
			LIMIT 1
		""", {"schools": allowed, "ay": self.academic_year})

		if not row:
			frappe.throw(_("No School Schedule found for school {0} (or its ancestors) in academic year {1}.")
				.format(base_school, self.academic_year))

		return frappe.get_cached_doc("School Schedule", row[0][0])

	def _validate_schedule_rows(self):
		"""
		• Ensures rotation_day / block_number exist in the resolved School Schedule
		• Auto-fills read-only from_time / to_time based on that block
		• Ensures instructor on each row belongs to the SG-instructor table
		"""
		if not self.student_group_schedule:
			return

		sched = self._get_school_schedule()   # single source of truth

		# Build: {rotation_day: {block_number: (from_time, to_time)} }
		block_map: dict[int, dict[int, tuple[str, str]]] = {}
		for b in sched.school_schedule_block:        # child table in School Schedule
			block_map.setdefault(b.rotation_day, {})[b.block_number] = (b.from_time, b.to_time)

		valid_instructors = {i.instructor for i in self.instructors}

		for row in self.student_group_schedule:

			# 1️⃣ Rotation-day within range
			if row.rotation_day < 1 or row.rotation_day > sched.rotation_days:
				frappe.throw(_(
					"Rotation Day {0} is outside the 1 - {1} range defined in {2}."
				).format(row.rotation_day, sched.rotation_days, sched.name))

			# 2️⃣ Block exists on that day
			if row.block_number not in block_map.get(row.rotation_day, {}):
				frappe.throw(_(
					"Block {0} is not defined on Rotation Day {1} in School Schedule {2}."
				).format(row.block_number, row.rotation_day, sched.name))

			# 3️⃣ Instructor consistency
			if row.instructor and row.instructor not in valid_instructors:
				frappe.throw(_(
					"Row {0}: Instructor {1} is not listed in the Student Group Instructor table."
				).format(row.idx, row.instructor))

			# 4️⃣ Auto-fill times (use read-only fields)
			from_t, to_t = block_map[row.rotation_day][row.block_number]
			row.from_time, row.to_time = from_t, to_t

	def validate_location_conflicts_absolute(self):
		"""
		Check this Student Group's room usage against materialized bookings.

		Compares this group's concrete sessions (absolute datetimes derived
		from rotation days + blocks) against Location Booking only.

		Respects the School's schedule_conflict_rule (Hard / Soft).
		"""
		# No schedule rows → nothing to check
		if not self.student_group_schedule:
			return

		# No rooms on any row → nothing to check
		if not any(getattr(row, "location", None) for row in self.student_group_schedule):
			return

		# We need an Academic Year to resolve real dates
		if not self.academic_year:
			return

		# Resolve School Schedule (same as in _validate_schedule_rows)
		try:
			sched = self._get_school_schedule()
		except Exception:
			# If schedule validation fails, that method will already raise;
			# no need to duplicate errors here.
			return

		# Build rotation_day → [dates] map for this schedule & AY
		rot_list = get_rotation_dates(sched.name, self.academic_year)
		if not rot_list:
			return

		rotation_dates: dict[int, list] = {}
		for row in rot_list:
			try:
				rd = int(row.get("rotation_day"))
			except Exception:
				continue
			d = row.get("date")
			if not d:
				continue
			rotation_dates.setdefault(rd, []).append(d)

		if not rotation_dates:
			return

		# Build: {rotation_day: {block_number: (from_time, to_time)}}
		block_map: dict[int, dict[int, tuple]] = {}
		for b in (sched.school_schedule_block or []):
			if b.rotation_day is None or b.block_number is None:
				continue
			try:
				rd = int(b.rotation_day)
				blk = int(b.block_number)
			except Exception:
				continue
			block_map.setdefault(rd, {})[blk] = (b.from_time, b.to_time)

		# Expand THIS group's proposed slots into absolute datetimes
		slots: list[tuple[str, object, object]] = []  # (location, start_dt, end_dt)

		for row in (self.student_group_schedule or []):
			loc = getattr(row, "location", None)
			rot = getattr(row, "rotation_day", None)
			blk = getattr(row, "block_number", None)

			if not (loc and rot and blk):
				continue

			try:
				rot = int(rot)
				blk = int(blk)
			except Exception:
				continue

			if rot not in rotation_dates:
				continue

			if blk not in block_map.get(rot, {}):
				continue

			from_t, to_t = block_map[rot][blk]
			if not (from_t and to_t):
				continue

			for d in rotation_dates[rot]:
				start_dt = get_datetime(f"{d} {from_t}")
				end_dt = get_datetime(f"{d} {to_t}")

				if not (start_dt and end_dt) or end_dt <= start_dt:
					continue

				slots.append((loc, start_dt, end_dt))

		if not slots:
			return

		exclude = {"source_doctype": "Student Group", "source_name": self.name}
		all_conflicts = []
		seen = set()

		for loc, start_dt, end_dt in slots:
			hits = find_room_conflicts(
				loc,
				start_dt,
				end_dt,
				exclude=exclude,
			)
			for c in hits:
				# Extra safety: don't ever flag this group against itself
				if c.get("source_doctype") == "Student Group" and c.get("source_name") == self.name:
					continue

				key = (
					c.get("source_doctype"),
					c.get("source_name"),
					c.get("location"),
					c.get("from"),
					c.get("to"),
				)
				if key in seen:
					continue
				seen.add(key)
				all_conflicts.append(c)

		if not all_conflicts:
			return

		lines = []
		for c in all_conflicts:
			target = get_link_to_form(c.get("source_doctype"), c.get("source_name"))
			start_str = format_datetime(c.get("from"))
			end_str = format_datetime(c.get("to"))

			lines.append(
				_("{location} is already booked by {doctype} {target} from {start} to {end}.").format(
					location=c.get("location"),
					doctype=c.get("source_doctype"),
					target=target,
					start=start_str,
					end=end_str,
				)
			)

		msg = "<br>".join(lines)
		title = _("Location conflicts detected")

		if get_conflict_rule() == "Hard":
			frappe.throw(msg, title=title)
		else:
			frappe.msgprint(msg, alert=True, title=title)


	def _derive_program_from_offering(self):
		"""Quality-of-life: show Program in the form, but do not treat as source of truth."""
		if not self.program and self.program_offering:
			self.program = frappe.db.get_value("Program Offering", self.program_offering, "program")


	# ---------- AY spine ----------

	def _validate_ay_in_offering_spine(self):
		"""Single AY field must be a member of the Program Offering's spine."""
		if not (self.program_offering and self.academic_year):
			return
		exists = frappe.db.exists(
			"Program Offering Academic Year",
			{
				"parenttype": "Program Offering",
				"parent": self.program_offering,
				"academic_year": self.academic_year,
			},
		)
		if not exists:
			frappe.throw(_("Academic Year must be one of the Program Offering's academic years."))

	##################### HELPERS #########################

	def _enforce_school_rules(self):
		"""Enforce:
		- SG.school must be same as or descendant of AY.school
		- If Program Offering present: branches must intersect; SG.school must be in intersection
		- Post-creation AY change: new AY.school must be same as or ancestor of existing SG.school
		- Activity/Other without Program Offering: default SG.school to AY.school on first save if empty
		"""
		ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school") if self.academic_year else None
		po_school = frappe.db.get_value("Program Offering", self.program_offering, "school") if self.program_offering else None

		# Guard: AY must have a school for rules to make sense
		if not ay_school:
			frappe.throw(_("Selected Academic Year has no linked School."))

		# Build allowed set
		ay_branch = descendants_inclusive(ay_school)
		allowed = set(ay_branch)

		if po_school:
			po_branch = descendants_inclusive(po_school)
			intersection = ay_branch.intersection(po_branch)
			if not intersection:
				# Different branches (no shared ancestor/desc relationship under either root) → hard error
				frappe.throw(_("Program Offering's school and Academic Year's school are in different branches."))
			allowed = intersection

		# Defaulting for Activity/Other (no Program driver)
		if (self.group_based_on in {"Activity", "Other"}) and not self.program_offering:
			if not self.school:
				# First-save default: set to AY.school
				self.school = ay_school

		# Validate SG.school is in allowed set (if user or code has set it)
		if self.school:
			if self.school not in allowed:
				frappe.throw(
					_("Student Group School must be {0} or a descendant within the allowed branch.").format(ay_school)
				)
		else:
			# No SG.school provided: if Program Offering exists, prefer PO.school when valid; otherwise require explicit choice
			if po_school and (po_school in allowed):
				self.school = po_school
			else:
				# Remain unset to force explicit user choice within allowed set
				pass

		# Post-creation AY change constraint:
		if not self.is_new():
			prior_ay = frappe.db.get_value(self.doctype, self.name, "academic_year")
			if prior_ay and self.academic_year and prior_ay != self.academic_year:
				# new AY.school must be same or ANCESTOR of the (already chosen) SG.school
				if not is_same_or_descendant(ay_school, self.school):
					frappe.throw(
						_("New Academic Year's school must be the same as or a parent of the Student Group's school.")
					)

	##################### COURSE SCOPING #########################
	# --- Course scoping (Program Offering Course) ---

	def _course_in_offering_for_ay(self) -> bool:
			"""Return True if self.course is present in Program Offering Course and valid for self.academic_year.
			Uses proper overlap logic for date windows and inclusive AY-range checks.
			"""
			if not (self.program_offering and self.course and self.academic_year):
					return False

			# Pull the selected AY's start/end once
			ay_row = frappe.db.get_value(
					"Academic Year",
					self.academic_year,
					["year_start_date", "year_end_date"],
					as_dict=True,
			)
			ay_start = ay_row.year_start_date if ay_row else None
			ay_end   = ay_row.year_end_date   if ay_row else None

			params = {
					"offering": self.program_offering,
					"course": self.course,
					"sel_ay": self.academic_year,
					"sel_ay_start": ay_start,
					"sel_ay_end": ay_end,
			}

			# NOTE:
			# 1) AY-range check: selected AY's start must fall within start/end AYs on the POC row (if provided)
			# 2) DATE-range overlap: the AY window [ay_start, ay_end] must overlap with [from_date, to_date] if those are provided.
			#    - If only from_date is set → require ay_end >= from_date
			#    - If only to_date   is set → require ay_start <= to_date
			#    - If both are set         → require (ay_end >= from_date) AND (ay_start <= to_date)
			row = frappe.db.sql(
					"""
					SELECT 1
					FROM `tabProgram Offering Course` poc
					LEFT JOIN `tabAcademic Year` ay_start ON ay_start.name = poc.start_academic_year
					LEFT JOIN `tabAcademic Year` ay_enday ON ay_enday.name = poc.end_academic_year
					WHERE poc.parenttype = 'Program Offering'
						AND poc.parent = %(offering)s
						AND poc.course = %(course)s
						AND (
									-- AY-range satisfied (if provided)
									(ay_start.year_start_date IS NULL OR %(sel_ay_start)s >= ay_start.year_start_date)
							AND (ay_enday.year_start_date IS NULL OR %(sel_ay_start)s <= ay_enday.year_start_date)
						)
						AND (
									-- DATE-range overlap (if provided)
									(poc.from_date IS NULL OR %(sel_ay_end)s   >= poc.from_date)
							AND (poc.to_date   IS NULL OR %(sel_ay_start)s <= poc.to_date)
						)
					LIMIT 1
					""",
					params,
			)

			return bool(row)

	def _validate_course_scoping(self):
		"""Hard guard for Course groups: the chosen Course must be part of the Program Offering and valid for the AY."""
		if self.group_based_on == "Course":
			if not self.program_offering:
				frappe.throw(_("Please select a Program Offering for a Course-based group."))
			if not self.course:
				frappe.throw(_("Please select a Course."))
			if not self._course_in_offering_for_ay():
				frappe.throw(_("Selected Course is not offered for this Program Offering in the chosen Academic Year."))

	@property
	def is_whole_day_group(self) -> bool:
		"""Return True if this group is configured as a whole-day attendance group."""
		scope = (getattr(self, "attendance_scope", None) or "").strip() or "Per Block"
		return scope == "Whole Day"


@frappe.whitelist()
def get_students(program_offering: str = None,
                 academic_year: str = None,
                 group_based_on: str = None,
                 course: str = None,
                 cohort: str = None,
                 term: str = None,
                 student_group: str = None,
                 limit: int = 500,
                 start: int = 0):
	"""
	Return students eligible for this Student Group, aligned to Program Offering + AY.

	- Course-based group → students with a Program Enrollment in (offering, AY)
	  AND at least one Program Enrollment Course row matching the selected course,
	  and not dropped (dropped_date is NULL). We also try to skip obvious 'Dropped' statuses.
	- Cohort-based group → students with Program Enrollment in (offering, AY) and matching cohort.
	- Other/Activity → manual selection → return [].

	Args come directly from the client (see get_student_filters in student_group.js).
	"""

	# Guardrails
	if not (program_offering and academic_year):
		return []

	group_based_on = (group_based_on or "").strip()

	# Activity / Other → manual selection only
	if group_based_on in {"Activity", "Other"}:
		return []

	# Base WHERE (Program Enrollment anchored to Offering + AY)
	where = [
		"pe.program_offering = %(program_offering)s",
		"pe.academic_year = %(academic_year)s",
	]
	params = {
		"program_offering": program_offering,
		"academic_year": academic_year,
		"limit": int(limit or 500),
		"start": int(start or 0),
	}

	# Optional: skip archived enrollments if present
	where.append("(pe.archived IS NULL OR pe.archived = 0)")

	join = ""
	post_where = ""

	# Course-based
	if group_based_on == "Course":
		if not course:
			return []  # no course selected → nothing to fetch yet

		join = """
			INNER JOIN `tabProgram Enrollment Course` pec
				ON pec.parenttype = 'Program Enrollment'
				AND pec.parent = pe.name
				AND pec.course = %(course)s
				AND (pec.dropped_date IS NULL)
		"""
		params["course"] = course

		# If 'status' exists and you use a 'Dropped' value, exclude it defensively
		post_where = """
			AND (pec.status IS NULL OR pec.status NOT IN ('Dropped'))
		"""

	# Cohort-based
	elif group_based_on == "Cohort":
		if not cohort:
			return []  # no cohort selected
		where.append("pe.cohort = %(cohort)s")
		params["cohort"] = cohort

	# Else (unexpected types) → fall back to offering+AY only, which is generally safe
	# but since you explicitly gate types, leaving as-is is fine.

	sql = f"""
		SELECT
			pe.student        AS student,
			COALESCE(pe.student_name, st.student_full_name) AS student_name,
			1 AS active
		FROM `tabProgram Enrollment` pe
		LEFT JOIN `tabStudent` st ON st.name = pe.student
		{join}
		WHERE {" AND ".join(where)}
		{post_where}
		ORDER BY COALESCE(st.student_full_name, pe.student_name) ASC, pe.student ASC
		LIMIT %(limit)s OFFSET %(start)s
	"""

	rows = frappe.db.sql(sql, params, as_dict=True)

	# Defensive: remove null/empty student ids
	rows = [r for r in rows if r.get("student")]

	return rows


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def allowed_school_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	List schools allowed for this SG:
	- If program_offering present: intersection(descendants(AY.school), descendants(PO.school))
	- Else: descendants(AY.school)
	"""
	ay = (filters or {}).get("academic_year")
	po = (filters or {}).get("program_offering")
	if not ay:
		return []

	ay_school = frappe.db.get_value("Academic Year", ay, "school")
	if not ay_school:
		return []

	ay_branch = descendants_inclusive(ay_school)
	allowed = ay_branch

	if po:
		po_school = frappe.db.get_value("Program Offering", po, "school")
		if po_school:
			po_branch = descendants_inclusive(po_school)
			allowed = ay_branch.intersection(po_branch)
			if not allowed:
				return []

	# Build a single nested-set envelope to keep the query fast
	min_lft = max_rgt = None
	for s in allowed:
		lft, rgt = get_school_lftrgt(s)
		if lft is None:
			continue
		min_lft = lft if min_lft is None else min(min_lft, lft)
		max_rgt = rgt if max_rgt is None else max(max_rgt, rgt)

	if min_lft is None:
		return []

	return frappe.db.sql(
		"""
		SELECT sc.name
		FROM `tabSchool` sc
		WHERE sc.lft >= %s AND sc.rgt <= %s
		  AND sc.name LIKE %s
		ORDER BY sc.lft ASC
		LIMIT %s OFFSET %s
		""",
		(min_lft, max_rgt, f"%{txt}%", page_len, start),
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def fetch_students(doctype, txt, searchfield, start, page_len, filters):
	gb = (filters or {}).get("group_based_on")
	po = (filters or {}).get("program_offering")
	ay = (filters or {}).get("academic_year")
	term = (filters or {}).get("term")
	cohort = (filters or {}).get("cohort")
	course = (filters or {}).get("course")
	sg = (filters or {}).get("student_group")

	like_txt = (f"%{txt}%" if txt else "%")

	# Activity/Other → free search among enabled students
	if gb in {"Other", "Activity"}:
		return frappe.db.sql(
			f"""
			SELECT name, student_full_name
			FROM `tabStudent`
			WHERE enabled = 1
			  AND (`{searchfield}` LIKE %s OR student_full_name LIKE %s)
			ORDER BY idx DESC, name
			LIMIT %s, %s
			""",
			(like_txt, like_txt, start, page_len)
		)

	# Offering+AY required for Course/Cohort flows
	if not (po and ay):
		return []

	# Get enrolled students (offering-first)
	enrolled = get_program_enrollment_offering_first(
		program_offering=po,
		academic_year=ay,
		term=term,
		cohort=cohort if gb == "Cohort" else None,
		course=course if gb == "Course" else None,
		exclude_in_group=sg if (gb == "Course" and course and term) else None,
	)

	existing = set(get_existing_students(sg)) if sg else set()
	candidates = [d.student for d in (enrolled or []) if d.student not in existing]
	if not candidates:
		return []

	placeholders = build_in_clause_placeholders(candidates)
	args = tuple(candidates + [like_txt, like_txt, start, page_len])

	return frappe.db.sql(
		f"""
		SELECT name, student_full_name
		FROM `tabStudent`
		WHERE name IN ({placeholders})
		  AND (`{searchfield}` LIKE %s OR student_full_name LIKE %s)
		ORDER BY idx DESC, name
		LIMIT %s, %s
		""",
		args,
	)


def get_program_enrollment_offering_first(program_offering: str,
                                          academic_year: str,
                                          term: str | None = None,
                                          cohort: str | None = None,
                                          course: str | None = None,
                                          exclude_in_group: str | None = None):
	conditions = [
		"pe.program_offering = %(po)s",
		"pe.academic_year = %(ay)s",
		"(pe.archived IS NULL OR pe.archived = 0)"
	]
	params = {"po": program_offering, "ay": academic_year}

	joins = ""
	if course or term:
		joins = "INNER JOIN `tabProgram Enrollment Course` pec ON pec.parent = pe.name AND pec.parenttype='Program Enrollment'"

	if term:
		conditions.append("pec.term_start = %(term)s")
		params["term"] = term
	if cohort:
		conditions.append("pe.cohort = %(cohort)s")
		params["cohort"] = cohort
	if course:
		conditions.append("pec.course = %(course)s")
		params["course"] = course

	if exclude_in_group and course and term:
		conditions.append("""
			pe.student NOT IN (
				SELECT sgs.student
				FROM `tabStudent Group` sg
				INNER JOIN `tabStudent Group Student` sgs ON sgs.parent = sg.name
				WHERE sg.name != %(exclude_group)s
				  AND sg.group_based_on = 'Course'
				  AND sg.course = %(course)s
				  AND sg.academic_year = %(ay)s
				  AND sg.term = %(term)s
			)
		""")
		params["exclude_group"] = exclude_in_group

	return frappe.db.sql(
		f"""
		SELECT pe.student, COALESCE(pe.student_name, st.student_full_name) AS student_name
		FROM `tabProgram Enrollment` pe
		LEFT JOIN `tabStudent` st ON st.name = pe.student
		{joins}
		WHERE {" AND ".join(conditions)}
		ORDER BY COALESCE(st.student_full_name, pe.student_name) ASC, pe.student ASC
		""",
		params,
		as_dict=1
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def schedule_picker_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	Return School Schedules whose School Calendar belongs to the selected Academic Year
	and whose School is in the user-school's ancestor chain.
	"""
	ay = filters.get("academic_year")
	if not ay:
		return []

	# current school on the Academic Year doc
	school = frappe.db.get_value("Academic Year", ay, "school")
	if not school:
		return []

	allowed_schools = get_ancestor_schools(school)  # self + parents

	# school-calendar ids that match AY + allowed schools
	cal_ids = frappe.db.get_all(
		"School Calendar",
		filters={
			"academic_year": ay,
			"school": ["in", allowed_schools],
		},
		pluck="name",
	)
	if not cal_ids:
		return []

	like = f"%{txt}%"
	rows = frappe.db.sql(
		"""
		SELECT
			name,
			rotation_days
		FROM `tabSchool Schedule`
		WHERE school_calendar IN %(cals)s
			AND (name LIKE %(like)s OR schedule_name LIKE %(like)s)
		ORDER BY idx, name
		LIMIT %(start)s, %(len)s
		""",
		dict(cals=tuple(cal_ids), like=like, start=start, len=page_len),
	)
	return rows


def get_program_enrollment(academic_year, term=None, program=None, cohort=None, course=None, exclude_in_group=None):
	conditions = ["pe.academic_year = %(academic_year)s"]
	params = {"academic_year": academic_year}

	joins = ""
	if course or term:
		joins = "INNER JOIN `tabProgram Enrollment Course` pec ON pec.parent = pe.name"

	if term:
		conditions.append("pec.term_start = %(term)s")
		params["term"] = term
	if program:
		conditions.append("pe.program = %(program)s")
		params["program"] = program
	if cohort:
		conditions.append("pe.cohort = %(cohort)s")
		params["cohort"] = cohort
	if course:
		conditions.append("pec.course = %(course)s")
		params["course"] = course

	# Exclude students already assigned to another group for same course+term+year
	if exclude_in_group and course and term:
		conditions.append("""
			pe.student NOT IN (
				SELECT sgs.student
				FROM `tabStudent Group` sg
				INNER JOIN `tabStudent Group Student` sgs ON sgs.parent = sg.name
				WHERE sg.name != %(exclude_group)s
					AND sg.group_based_on = 'Course'
					AND sg.course = %(course)s
					AND sg.academic_year = %(academic_year)s
					AND sg.term = %(term)s
			)
		""")
		params["exclude_group"] = exclude_in_group

	query = f"""
		SELECT pe.student, pe.student_name
		FROM `tabProgram Enrollment` pe
		{joins}
		WHERE {" AND ".join(conditions)}
		ORDER BY pe.student_name ASC
	"""

	return frappe.db.sql(query, params, as_dict=1)


def get_existing_students(student_group: str) -> list[str]:
	"""Returns a list of student IDs already in the student group"""
	return frappe.db.sql_list('''
		SELECT student FROM `tabStudent Group Student` WHERE parent = %s
	''', (student_group,))


def build_in_clause_placeholders(values: list) -> str:
	"""Returns a string like '%s, %s, %s' based on list length"""
	return ', '.join(['%s'] * len(values))


########################## Permissions ##########################
##### Used for school descendants .
#################################################################

# --- small, local helpers (no extra round-trips where possible) ---

def get_school_lftrgt(school: str) -> tuple[int, int] | tuple[None, None]:
	if not school:
		return (None, None)
	return frappe.db.get_value("School", school, ["lft", "rgt"], as_dict=False) or (None, None)

def is_same_or_descendant(maybe_ancestor: str, node: str) -> bool:
	"""True if node is the same as maybe_ancestor or a descendant in the School nested set."""
	if not (maybe_ancestor and node):
		return False
	al, ar = get_school_lftrgt(maybe_ancestor)
	nl, nr = get_school_lftrgt(node)
	return (al is not None and nl is not None) and (al <= nl <= nr <= ar)

def descendants_inclusive(school: str) -> set[str]:
	"""Return school ∪ all descendants (names) as a set. Efficient single query on lft/rgt."""
	if not school:
		return set()
	lft, rgt = get_school_lftrgt(school)
	if lft is None:
		return set()
	rows = frappe.db.sql(
		"""
		SELECT name
		FROM `tabSchool`
		WHERE lft >= %s AND rgt <= %s
		""",
		(lft, rgt),
		as_dict=True,
	)
	return {r["name"] for r in rows}

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def offering_ay_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return AYs that belong to filters.program_offering (desc by name)."""
	offering = (filters or {}).get("program_offering")
	if not offering:
		return []
	return frappe.db.sql(
		"""
		SELECT ay.name
		FROM `tabProgram Offering Academic Year` poay
		INNER JOIN `tabAcademic Year` ay ON ay.name = poay.academic_year
		WHERE poay.parenttype='Program Offering' AND poay.parent=%s
		  AND ay.name LIKE %s
		ORDER BY ay.name DESC
		LIMIT %s OFFSET %s
		""",
		(offering, f"%{txt}%", page_len, start),
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def offering_course_query(doctype, txt, searchfield, start, page_len, filters):
    """
    List Courses from Program Offering Course, valid for the selected Program Offering
    and (optionally) Academic Year + Term. Uses proper *overlap* logic for date windows:
      - if poc.from_date is set  → ay.year_end_date   >= poc.from_date
      - if poc.to_date   is set  → ay.year_start_date <= poc.to_date
    Returns (name, label).
    """
    offering = (filters or {}).get("program_offering")
    selected_ay = (filters or {}).get("academic_year")
    selected_term = (filters or {}).get("term")  # optional

    if not offering:
        return []

    txt_like = f"%{txt}%"
    args = {
        "offering": offering,
        "txt": txt_like,
        "start": start,
        "page_len": page_len,
        "ay": selected_ay,
    }

    # Optional term window (only if columns exist and a term is selected)
    term_clause = ""
    try:
        has_start_term = frappe.db.has_column("Program Offering Course", "start_academic_term")
        has_end_term   = frappe.db.has_column("Program Offering Course", "end_academic_term")
    except Exception:
        has_start_term = has_end_term = False

    if selected_term and has_start_term and has_end_term:
        term_clause = """
            AND (
                    (poc.start_academic_term IS NULL OR poc.start_academic_term <= %(term)s)
                AND (poc.end_academic_term   IS NULL OR poc.end_academic_term   >= %(term)s)
            )
        """
        args["term"] = selected_term

    # AY/date windows are applied only when an AY is selected (and we can read its dates)
    ay_clause = ""
    if selected_ay:
        ay_start = frappe.db.get_value("Academic Year", selected_ay, "year_start_date")
        ay_end   = frappe.db.get_value("Academic Year", selected_ay, "year_end_date")
        args["ay_start_date"] = ay_start
        args["ay_end_date"]   = ay_end

        # AY-range window (compare against AYs referenced on POC rows by start_AY/end_AY)
        # and DATE-range window with proper overlap checks
        ay_clause = """
            LEFT JOIN `tabAcademic Year` ay_start ON ay_start.name = poc.start_academic_year
            LEFT JOIN `tabAcademic Year` ay_enday ON ay_enday.name = poc.end_academic_year
            WHERE poc.parenttype='Program Offering'
              AND poc.parent = %(offering)s
              AND (poc.course LIKE %(txt)s OR c.course_name LIKE %(txt)s)
              AND (
                    (ay_start.year_start_date IS NULL OR %(ay_start_date)s >= ay_start.year_start_date)
                AND (ay_enday.year_start_date  IS NULL OR %(ay_start_date)s <= ay_enday.year_start_date)
              )
              AND (
                    (poc.from_date IS NULL OR %(ay_end_date)s   >= poc.from_date)
                AND (poc.to_date   IS NULL OR %(ay_start_date)s <= poc.to_date)
              )
              {term_clause}
        """.format(term_clause=term_clause)
    else:
        # No AY selected → just list by parent (no windows)
        ay_clause = """
            WHERE poc.parenttype='Program Offering'
              AND poc.parent = %(offering)s
              AND (poc.course LIKE %(txt)s OR c.course_name LIKE %(txt)s)
        """

    sql = f"""
        SELECT
            poc.course                                  AS name,
            COALESCE(c.course_name, poc.course)         AS label
        FROM `tabProgram Offering Course` poc
        LEFT JOIN `tabCourse` c ON c.name = poc.course
        {ay_clause}
        ORDER BY label ASC, name ASC
        LIMIT %(page_len)s OFFSET %(start)s
    """

    return frappe.db.sql(sql, args)


########################## Permissions ##########################
##### Used in other parts
#################################################################

def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user
	current_user = frappe.get_doc("User", frappe.session.user)
	roles = [role.role for role in current_user.roles]

	if "Student" in roles:
		return """(name in (select parent from `tabStudent Group Student` where user_id=%(user)s))""" % {
			"user": frappe.db.escape(user),
			}

	if "Instructor" in roles:
		return """(name in (select parent from `tabStudent Group Instructor` where user_id=%(user)s))""" % {
				"user": frappe.db.escape(user),
				}
	super_viewer = ["Administrator", "System Manager", "Academic Assistant", "Academic Admin", "Schedule Maker"]
	for role in roles:
		if role in super_viewer:
			return ""


def on_doctype_update():
	frappe.db.add_index("Student Group", ["program_offering", "academic_year"])
