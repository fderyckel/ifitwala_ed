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
		self.validate_program_and_course()
		self.validate_mandatory_fields()
		self.validate_size()
		self.validate_students()
		self.validate_and_set_child_table_fields()
		validate_duplicate_student(self.students)
		self.validate_rotation_clashes()
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

	def validate_term(self) -> None:
		term_year = frappe.get_doc("Term", self.term)
		if self.academic_year != term_year.academic_year:
			frappe.throw(_("The term {0} does not belong to the academic year {1}.").format(self.term, self.academic_year))

	def validate_program_and_course(self) -> None:
		"""Validates the course against the program if group_based_on is 'Course'."""
		# Added: Condition to check group_based_on and program before validating.
		if self.group_based_on == "Course" and self.program:
			if not self.course:
				frappe.throw(_("Course is required when Group Based On is Course and a Program is selected."))

			# Changed: Use frappe.db.exists for efficient existence check.
			if not frappe.db.exists("Program Course", {"parent": self.program, "course": self.course}):
				frappe.throw(_("{0} is not a valid course for the {1} program. Please select a different course or the appropriate program."
							).format(get_link_to_form("Course", self.course), get_link_to_form("Program", self.program))
				)

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
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		SELECT name
		FROM `tabAcademic Year`
		WHERE name LIKE %(txt)s
		ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
		LIMIT %(start)s, %(page_len)s
	""", {
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len
	})

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
##### Used for scheduling. 
#################################################################



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
		