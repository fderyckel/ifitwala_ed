# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_link_to_form
from ifitwala_ed.schedule.schedule_utils import validate_duplicate_student
from ifitwala_ed.schedule.schedule_utils import check_slot_conflicts, get_conflict_rule
from ifitwala_ed.schedule.schedule_utils import get_effective_schedule
from ifitwala_ed.utilities.school_tree import (
    get_ancestor_schools,          # for the picker
    get_first_ancestor_with_doc    # for automatic lookup
)
from ifitwala_ed.schedule.attendance_utils import invalidate_meeting_dates

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

		self.validate_mandatory_fields()
		self.validate_size()
		self.validate_students()
		self.validate_and_set_child_table_fields()
		validate_duplicate_student(self.students)
		self.validate_rotation_clashes()

		self._derive_program()



		########
		# Auto-fill school_schedule if missing and based on course
		if self.group_based_on == "Course" and not self.school_schedule:
			school = frappe.db.get_value("Program", self.program, "school")
			if not school:
				frappe.throw(_("{0} has no linked school. Please update the Program.").format(
					get_link_to_form("Program", self.program)
				))
			
			self.school_schedule = get_effective_schedule(self.academic_year, school)


		############	
		self._validate_schedule_rows()

		if self.group_based_on in ["Course", "Activity"]:
			if self.term: 
				self.title = self.student_group_abbreviation + "/" + self.term
			else: 
				self.title = self.student_group_abbreviation + "/" + self.academic_year
		elif self.group_based_on == "Cohort":
			self.title = self.student_group_abbreviation + "/" + self.cohort
		else:
			self.title = self.student_group_abbreviation

  	# ── Overlap detection ───────────────────────────────────────────────
		if not getattr(self, "_conflict_checked", False):
			conflicts = check_slot_conflicts(self)
			if conflicts:
				# turn the dict into readable bullets
				lines = []
				for cat, items in conflicts.items():
					for entry in items:
						# entry = (entity, rotation, block)
						ent, rot, blk = entry
						if isinstance(ent, (list, tuple)):
							ent = ", ".join(ent)
						lines.append(f"• {cat.title()}: <b>{ent}</b> — Day {rot}, Block {blk}")

				msg = "<br>".join(lines)
				title = _("Scheduling conflicts detected")

				if get_conflict_rule() == "Hard":
					frappe.throw(msg, title=title)
				else:
					frappe.msgprint(msg, alert=True, title=title)

			self._conflict_checked = True					

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
				uid = (getattr(r, "user_id", "") or "").strip()
				ins = (getattr(r, "instructor", "") or "").strip()
				if uid:
					keys.add(("uid", uid))
				elif ins:
					keys.add(("ins", ins))
			return keys

		prev_instr = instructor_keys(old)
		curr_instr = instructor_keys(self)
		self.flags._sg_instructors_changed = (prev_instr != curr_instr)

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

		# ----- MEETING-DATES invalidation (NEW) -----
		if bool(getattr(self.flags, "_sg_meeting_dates_changed", False)):
			invalidate_meeting_dates(self.name)
			self.flags._sg_meeting_dates_changed = False

		# cleanup flags
		self.flags._sg_students_added = set()
		self.flags._sg_students_removed = set()
		self.flags._sg_instructors_changed = False

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

			# Check program enrollment (optional)
			if self.program:
				if not frappe.db.exists("Program Enrollment", {
					"student": student.student,
					"program": self.program,
					"academic_year": self.academic_year
				}):
					frappe.throw(_("Student {0} ({1}) is not enrolled in the program {2} for academic year {3}.").format(
						student.student_name,
						student.student,
						get_link_to_form("Program", self.program),
						self.academic_year
					))

			# Check cohort (optional)
			if self.cohort:
				if not frappe.db.exists("Program Enrollment", {
					"student": student.student,
					"cohort": self.cohort,
					"academic_year": self.academic_year
				}):
					frappe.throw(_("Student {0} ({1}) is not part of the cohort {2}.").format(
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

	def validate_rotation_clashes(self):
		"""
		Check duplicates across student, instructor, location
		within the same School Calendar & School hierarchy.
		"""
		key_sets = {
			"student": set(),
			"instructor": set(),
			"location": set()
		}

		for row in self.student_group_schedule:
			hash_base = f"{row.rotation_day}:{row.block_number}"
			# students
			for s in self.students:
				key = f"{hash_base}:{s.student}"
				if key in key_sets["student"]:
					frappe.throw(_("Student clash on rotation {0} block {1} ({2})")
								.format(row.rotation_day, row.block_number, s.student))
				key_sets["student"].add(key)

			# instructors (child table student_group_instructor)
			for instr in self.instructors:
				key = f"{hash_base}:{instr.instructor}"
				if key in key_sets["instructor"]:
					frappe.throw(_("Instructor clash on rotation {0} block {1} ({2})")
								.format(row.rotation_day, row.block_number, instr.instructor))
				key_sets["instructor"].add(key)

			# location
			key = f"{hash_base}:{row.location}"
			if key in key_sets["location"]:
				frappe.throw(_("Location clash on rotation {0} block {1} ({2})")
							.format(row.rotation_day, row.block_number, row.location))
			key_sets["location"].add(key)

	def _get_school_schedule(self):
		"""
		Returns the School Schedule to validate against.

		• If Program is set  → walk the school tree (self + parents)
			until we find the first School Schedule owned by that school.
		• If Program is blank → rely on the explicit school_schedule field.
		"""
		if self.program:
			base_school = frappe.db.get_value("Program", self.program, "school")
			allowed = get_ancestor_schools(base_school)    # self + parents

			res = frappe.db.sql("""
				SELECT ss.name
				FROM `tabSchool Schedule` ss
				JOIN `tabSchool Calendar` sc ON sc.name = ss.school_calendar
				WHERE ss.school IN %(schools)s
				AND sc.academic_year = %(ay)s
				LIMIT 1
			""", dict(schools=tuple(allowed), ay=self.academic_year))

			if not res:
				frappe.throw(_("No School Schedule found for school {0} in academic year {1}.")
					.format(base_school, self.academic_year))
			return frappe.get_cached_doc("School Schedule", res[0][0])

		# fall-back when no program
		if not self.school_schedule:
			frappe.throw(_("Please choose a School Schedule or set a Program."))
		return frappe.get_cached_doc("School Schedule", self.school_schedule)		
	
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



	def _derive_program(self):
		if not self.program and self.program_offering:
			self.program = frappe.db.get_value("Program Offering", self.program_offering, "program")

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
		"""Return True if self.course is present in Program Offering Course and valid for self.academic_year."""
		if not (self.program_offering and self.course and self.academic_year):
			return False

		# We compare the Academic Year's start_date against start/end AYs and date ranges
		# Join to Academic Year to use year_start_date for stable comparisons when AY names don't sort naturally.
		row = frappe.db.sql(
			"""
			SELECT 1
			FROM `tabProgram Offering Course` poc
			LEFT JOIN `tabAcademic Year` ay_sel  ON ay_sel.name = %(selected_ay)s
			LEFT JOIN `tabAcademic Year` ay_start ON ay_start.name = poc.start_academic_year
			LEFT JOIN `tabAcademic Year` ay_end   ON ay_end.name   = poc.end_academic_year
			WHERE poc.parenttype = 'Program Offering'
				AND poc.parent = %(offering)s
				AND poc.course = %(course)s
				AND (
					-- AY window satisfied (if provided)
					(ay_start.year_start_date IS NULL OR ay_sel.year_start_date >= ay_start.year_start_date)
				AND (ay_end.year_start_date   IS NULL OR ay_sel.year_start_date <= ay_end.year_start_date)
				)
				AND (
					-- Date window satisfied (if provided)
					(poc.from_date IS NULL OR ay_sel.year_start_date >= poc.from_date)
				AND (poc.to_date   IS NULL OR ay_sel.year_start_date <= poc.to_date)
				)
			LIMIT 1
			""",
			{
				"offering": self.program_offering,
				"course": self.course,
				"selected_ay": self.academic_year,
			},
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

@frappe.whitelist()
def get_students(academic_year, group_based_on, term=None, program=None, cohort=None, course=None):
	enrolled_students = get_program_enrollment(academic_year, term, program, cohort, course)

	if enrolled_students:
		student_list = []
		for s in enrolled_students:
			if frappe.db.get_value("Student", s.student, "enabled"):
				s.update({"active": 1})
			else:
				s.update({"active": 0})
			student_list.append(s)
		return student_list
	else:
		frappe.msgprint(_("No students found"))
		return []


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def fetch_students(doctype, txt, searchfield, start, page_len, filters):
	group_based_on = filters.get("group_based_on")

	if group_based_on == "Other":
		# Students with no enrollment requirement
		return frappe.db.sql(f"""
			SELECT name, student_full_name 
			FROM `tabStudent`
			WHERE enabled = 1
				AND (`{searchfield}` LIKE %s OR student_full_name LIKE %s)
			ORDER BY idx DESC, name
			LIMIT %s, %s
		""", (f"%{txt}%", f"%{txt}%", start, page_len))

	elif group_based_on == "Activity":
		# May become specific in future (e.g., filter by activity type or tag)
		return frappe.db.sql(f"""
			SELECT name, student_full_name 
			FROM `tabStudent`
			WHERE enabled = 1
				AND (`{searchfield}` LIKE %s OR student_full_name LIKE %s)
			ORDER BY idx DESC, name
			LIMIT %s, %s
		""", (f"%{txt}%", f"%{txt}%", start, page_len))

	elif group_based_on == "Course":
		enrolled_students = get_program_enrollment(
			academic_year=filters.get('academic_year'),
			term=filters.get('term'),
			program=filters.get('program'),
			cohort=filters.get('cohort'),
			course=filters.get('course'), 
			exclude_in_group=filters.get('student_group') 
		)

	elif group_based_on == "Cohort":
		enrolled_students = get_program_enrollment(
			academic_year=filters.get('academic_year'),
			term=filters.get('term'),
			program=filters.get('program'),
			cohort=filters.get('cohort'),
			course=None
		)

	else:
		return []

	# Shared logic for course or cohort results
	existing_students = get_existing_students(filters.get('student_group'))

	student_ids = [
		d.student for d in enrolled_students 
		if d.student not in existing_students
	] if enrolled_students else []

	if not student_ids:
		return []

	placeholders = build_in_clause_placeholders(student_ids)
	args = tuple(student_ids + [f"%{txt}%", f"%{txt}%", start, page_len])

	query = f"""
		SELECT name, student_full_name 
		FROM `tabStudent`
		WHERE name IN ({placeholders})
			AND (`{searchfield}` LIKE %s OR student_full_name LIKE %s)
		ORDER BY idx DESC, name
		LIMIT %s, %s
	"""

	return frappe.db.sql(query, args)


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
	List Courses from Program Offering Course, valid for the selected Academic Year (and optional Term filter).
	"""
	offering = (filters or {}).get("program_offering")
	selected_ay = (filters or {}).get("academic_year")
	selected_term = (filters or {}).get("term")  # optional

	if not (offering and selected_ay):
		return []

	# Base filter: in this offering and name LIKE
	params = {
		"offering": offering,
		"txt": f"%{txt}%",
		"selected_ay": selected_ay,
		"start": start,
		"page_len": page_len,
	}

	# Optional term overlap filter (inclusive boundary check if both ends exist)
	term_clause = ""
	if selected_term:
		term_clause = """
			AND (
				(poc.start_academic_term IS NULL OR poc.start_academic_term <= %(term)s)
			AND (poc.end_academic_term   IS NULL OR poc.end_academic_term   >= %(term)s)
			)
		"""
		params["term"] = selected_term

	return frappe.db.sql(
		f"""
		SELECT poc.course
		FROM `tabProgram Offering Course` poc
		LEFT JOIN `tabAcademic Year` ay_sel  ON ay_sel.name = %(selected_ay)s
		LEFT JOIN `tabAcademic Year` ay_start ON ay_start.name = poc.start_academic_year
		LEFT JOIN `tabAcademic Year` ay_end   ON ay_end.name   = poc.end_academic_year
		WHERE poc.parenttype='Program Offering'
		  AND poc.parent = %(offering)s
		  AND poc.course LIKE %(txt)s
		  AND (
				(ay_start.year_start_date IS NULL OR ay_sel.year_start_date >= ay_start.year_start_date)
			AND (ay_end.year_start_date   IS NULL OR ay_sel.year_start_date <= ay_end.year_start_date)
		  )
		  AND (
				(poc.from_date IS NULL OR ay_sel.year_start_date >= poc.from_date)
			AND (poc.to_date   IS NULL OR ay_sel.year_start_date <= poc.to_date)
		  )
		  {term_clause}
		ORDER BY poc.course ASC
		LIMIT %(page_len)s OFFSET %(start)s
		""",
		params,
	)


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
	super_viewer = ["Administrator", "System Manager", "Academic Admin", "Schedule Maker"]
	for role in roles:
		if role in super_viewer:
			return ""
		

def on_doctype_update():
	frappe.db.add_index("Student Group", ["program_offering", "academic_year"])