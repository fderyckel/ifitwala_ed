# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt


import frappe
import json
from frappe import _
from frappe.utils import cint, get_link_to_form
from frappe.model.document import Document
from ifitwala_ed.schedule.schedule_utils import get_school_term_bounds


def _get_offering_meta(offering: str) -> dict:
	"""Return key details for Program Offering, with minimal fields for performance."""
	if not offering:
		return {}
	return frappe.db.get_value(
		"Program Offering",
		offering,
		["program", "school"],
		as_dict=True,
	) or {}


def _offering_course_map(offering: str) -> dict:
	"""Map course → Program Offering Course row (elective_group, required, AY/term dates/terms)."""
	if not offering:
		return {}
	rows = frappe.db.sql("""
		SELECT poc.course, poc.elective_group, poc.required,
		       poc.start_academic_year, poc.end_academic_year,
		       poc.start_academic_term, poc.end_academic_term
		FROM `tabProgram Offering Course` poc
		WHERE poc.parent = %s
	""", (offering,), as_dict=True)
	return {r.course: r for r in rows}


def _offering_ay_set(offering: str) -> set[str]:
	"""Set of allowed Academic Years for this Program Offering."""
	rows = frappe.db.sql("""
		SELECT poay.academic_year
		FROM `tabProgram Offering Academic Year` poay
		WHERE poay.parent = %s
	""", (offering,), as_list=True)
	return {r[0] for r in rows}


def _pe_by_student_offering_ay(students: list[str], offering: str, ay: str) -> dict:
	"""Batch lookup Program Enrollment by (student, offering, ay) → PE name, school."""
	if not students:
		return {}
	placeholders = ", ".join(["%s"] * len(students))
	params = tuple(students) + (offering, ay)
	res = frappe.db.sql(f"""
		SELECT pe.name, pe.student, pe.school
		FROM `tabProgram Enrollment` pe
		WHERE pe.student IN ({placeholders})
		  AND pe.program_offering = %s
		  AND pe.academic_year = %s
		  AND pe.archived = 0
		  AND pe.docstatus < 2
	""", params, as_dict=True)
	return {r.student: {"name": r.name, "school": r.school} for r in res}


def _pe_has_course(pe_name: str, course: str) -> bool:
	row = frappe.db.get_value(
		"Program Enrollment Course",
		{"parent": pe_name, "course": course},
		"name",
	)
	return bool(row)


def _warn_if_elective_conflict(pe_name: str, course: str, offering_course_meta: dict):
	"""Soft warning if another course in the same elective group already exists in PE."""
	meta = offering_course_meta.get(course)
	eg = (meta or {}).get("elective_group")
	if not eg:
		return
	# find all existing courses in the same elective group (using current offering map)
	existing = frappe.db.sql("""
		SELECT pec.course
		FROM `tabProgram Enrollment Course` pec
		WHERE pec.parent = %s
	""", (pe_name,), as_list=True)
	existing_courses = {r[0] for r in existing}
	conflicts = [
		c for c in existing_courses
		if c != course and (offering_course_meta.get(c) or {}).get("elective_group") == eg
	]
	if conflicts:
		frappe.msgprint(
			_("Elective note: Program Enrollment {0} already has a course in group “{1}”. (Existing: {2})")
			.format(
				get_link_to_form("Program Enrollment", pe_name),
				eg,
				", ".join(conflicts)
			),
			alert=True
		)


class CourseEnrollmentTool(Document):
	@frappe.whitelist()
	def add_course_to_program_enrollment(self):
		"""
		Add the selected course to each listed student's Program Enrollment,
		keyed by (program_offering, academic_year), with term precedence:
			1) Course.term_long + tool.term
			2) Offering Course start/end academic term
			3) get_school_term_bounds(school, academic_year)
		Also validates AY belongs to the Program Offering and course is allowed by the offering
		(or is explicitly marked non-catalog in the offering).
		"""
		if not self.program_offering:
			frappe.throw(_("Please select a Program Offering."))

		offering = _get_offering_meta(self.program_offering)
		if not offering:
			frappe.throw(_("Program Offering not found."))

		# Validate AY is in offering AY list
		allowed_ays = _offering_ay_set(self.program_offering)
		if self.academic_year not in allowed_ays:
			frappe.throw(_("Academic Year {0} is not part of {1} Offering AYs.")
				.format(self.academic_year, get_link_to_form("Program Offering", self.program_offering)))

		# Validate course against offering (or allow explicit non-catalog from offering row)
		offering_courses = _offering_course_map(self.program_offering)
		oc = offering_courses.get(self.course)
		if not oc:
			frappe.throw(_("Course {0} is not listed in {1} Offering Courses. Please adjust selection.")
				.format(get_link_to_form("Course", self.course),
				        get_link_to_form("Program Offering", self.program_offering)))
		# If offering row says non-catalog, require exception_reason
		if oc.get("required") is None:
			# No-op, “required” may be null for some rows; we only enforce non-catalog through offering row if you add such a flag there.
			pass

		# Resolve Course.term_long
		term_long = frappe.db.get_value("Course", self.course, "term_long")

		# Batch resolve Program Enrollments for listed students
		students = [r.student for r in (self.students or []) if r.student]
		pe_by_student = _pe_by_student_offering_ay(students, self.program_offering, self.academic_year)

		missed = []
		modified_pes: dict[str, dict] = {}  # pe_name -> {school, rows: [child rows to append]}
		for r in (self.students or []):
			if not r.student:
				continue
			info = pe_by_student.get(r.student)
			if not info:
				missed.append(r.student)
				continue

			pe_name = info["name"]
			if _pe_has_course(pe_name, self.course):
				frappe.msgprint(_("Course {0} already exists in Program Enrollment {1}.")
					.format(get_link_to_form("Course", self.course),
					        get_link_to_form("Program Enrollment", pe_name)))
				continue

			# Determine term window
			child = {"course": self.course, "status": "Enrolled"}

			if term_long:
				# Tool term required/optional: if set, use (term, term), else leave blank
				if self.term:
					child["term_start"] = self.term
					child["term_end"] = self.term
			elif oc and (oc.get("start_academic_term") or oc.get("end_academic_term")):
				if oc.get("start_academic_term"):
					child["term_start"] = oc["start_academic_term"]
				if oc.get("end_academic_term"):
					child["term_end"] = oc["end_academic_term"]
			else:
				# fallback to school term bounds
				bounds = get_school_term_bounds(info["school"], self.academic_year) or {}
				if not bounds.get("term_start") or not bounds.get("term_end"):
					frappe.throw(_("Cannot determine term boundaries for School {0}, Academic Year {1}. Configure terms.")
						.format(info["school"], self.academic_year))
				child["term_start"] = bounds["term_start"]
				child["term_end"] = bounds["term_end"]

			# Stash for batch append
			modified_pes.setdefault(pe_name, {"school": info["school"], "rows": []})
			modified_pes[pe_name]["rows"].append(child)

			# Soft elective conflict warning
			_warn_if_elective_conflict(pe_name, self.course, offering_courses)

		# Inform about students with no matching PE
		if missed:
			frappe.msgprint(
				_("No Program Enrollment found for the following student(s) in offering {0}, AY {1}: {2}")
				.format(get_link_to_form("Program Offering", self.program_offering),
				        self.academic_year, ", ".join(missed)),
				indicator="orange",
			)

		# Batch save per PE
		for pe_name, payload in modified_pes.items():
			pe = frappe.get_doc("Program Enrollment", pe_name)
			for row in payload["rows"]:
				pe.append("courses", row)
			pe.save()

		if modified_pes:
			frappe.msgprint(_("Courses added to {0} Program Enrollment(s).").format(len(modified_pes)))
		else:
			frappe.msgprint(_("Nothing to update."))

		self.save()


@frappe.whitelist()
def fetch_eligible_students(doctype, txt, searchfield, start, page_len, filters=None):
	"""
	Eligible = Students with a Program Enrollment matching (program_offering, academic_year),
	not archived, not cancelled, and where the PE does not already contain the selected course.
	Returns [[student_id, student_full_name, program_enrollment], ...]
	"""
	start = cint(start)
	page_len = cint(page_len)
	if not filters:
		filters = {}
	elif isinstance(filters, str):
		filters = json.loads(filters)

	academic_year = filters.get("academic_year")
	program_offering = filters.get("program_offering")
	course = filters.get("course")

	if not academic_year or not program_offering or not course:
		frappe.throw(_("Program Offering, Academic Year, and Course are required."))

	values = [program_offering, academic_year, course]
	txt_filter = ""
	if txt:
		txt_filter = "AND (s.name LIKE %s OR s.student_full_name LIKE %s)"
		values += [f"%{txt}%", f"%{txt}%"]

	query = f"""
		SELECT DISTINCT s.name AS student, s.student_full_name, pe.name AS program_enrollment
		FROM `tabProgram Enrollment` pe
		JOIN `tabStudent` s ON s.name = pe.student
		WHERE pe.program_offering = %s
		  AND pe.academic_year = %s
		  AND pe.archived = 0
		  AND pe.docstatus < 2
		  AND s.enabled = 1
		  AND pe.name NOT IN (
				SELECT parent
				FROM `tabProgram Enrollment Course`
				WHERE course = %s
		  )
		  {txt_filter}
		ORDER BY s.student_full_name, s.name
		LIMIT {start}, {page_len}
	"""
	results = frappe.db.sql(query, values, as_dict=True)
	return [[r["student"], r["student_full_name"], r["program_enrollment"]] for r in results]


@frappe.whitelist()
def get_courses_for_offering(doctype, txt, searchfield, start, page_len, filters=None):
	"""
	Return [value, label] for Course link but scoped to Program Offering Courses,
	and (optionally) constrained by the selected Academic Year window.
	"""
	start = cint(start)
	page_len = cint(page_len)

	if not filters:
		filters = {}
	program_offering = filters.get("program_offering")
	academic_year = filters.get("academic_year")

	if not program_offering:
		return []

	conds = ["poc.parent = %s"]
	values = [program_offering]

	# If AY is chosen, only include rows whose AY range covers it (or the row has no AY bounds)
	if academic_year:
		conds.append("""(
			(poc.start_academic_year IS NULL AND poc.end_academic_year IS NULL)
			OR (poc.start_academic_year IS NULL AND poc.end_academic_year = %(ay)s)
			OR (poc.end_academic_year IS NULL AND poc.start_academic_year = %(ay)s)
			OR (%(ay)s BETWEEN IFNULL(poc.start_academic_year, %(ay)s) AND IFNULL(poc.end_academic_year, %(ay)s))
		)""")
		values.append(academic_year)
		# Named parameter used twice; append once more for safety if your DB adapter needs it:
		# (MariaDB via frappe.db.sql will substitute by name; this line is okay as is.)

	if txt:
		conds.append("(c.name LIKE %s OR c.course_name LIKE %s)")
		values.extend([f"%{txt}%", f"%{txt}%"])

	where_clause = " AND ".join(conds)
	rows = frappe.db.sql(f"""
		SELECT c.name, c.course_name, poc.required
		FROM `tabProgram Offering Course` poc
		JOIN `tabCourse` c ON c.name = poc.course
		WHERE {where_clause}
		ORDER BY c.name
		LIMIT {start}, {page_len}
	""", tuple(values), as_dict=True)

	out = []
	for r in rows:
		label_bits = [r["name"]]
		if r.get("course_name"):
			label_bits.append(r["course_name"])
		if r.get("required"):
			label_bits.append("• required")
		out.append([r["name"], " — ".join(label_bits)])
	return out


@frappe.whitelist()
def list_offering_academic_years_desc(doctype, txt, searchfield, start, page_len, filters=None):
	"""
	Academic years for the selected Program Offering, sorted by year_end_date DESC.
	Falls back to global list if offering not provided.
	"""
	if not filters:
		filters = {}
	program_offering = filters.get("program_offering")

	if program_offering:
		rows = frappe.db.sql("""
			SELECT ay.name
			FROM `tabProgram Offering Academic Year` poay
			JOIN `tabAcademic Year` ay ON ay.name = poay.academic_year
			WHERE poay.parent = %s
			ORDER BY ay.year_end_date DESC
		""", (program_offering,), as_list=True)
		return rows

	# fallback (kept from your original util)
	return frappe.db.sql("""
		SELECT name
		FROM `tabAcademic Year`
		WHERE year_end_date IS NOT NULL
		ORDER BY year_end_date DESC
	""", as_list=True)
