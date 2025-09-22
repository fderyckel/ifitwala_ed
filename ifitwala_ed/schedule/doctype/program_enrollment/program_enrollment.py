# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe 
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_link_to_form
from ifitwala_ed.schedule.schedule_utils import get_school_term_bounds
from ifitwala_ed.utilities.school_tree import get_effective_record, ParentRuleViolation
from frappe.utils.nestedset import get_ancestors_of
from ifitwala_ed.utilities.school_tree import get_descendant_schools
from typing import Optional, Sequence

class ProgramEnrollment(Document):

	def validate(self):

		# 0) Require program_offering, resolve it once
		if not getattr(self, "program_offering", None):
			frappe.throw(_("Program Offering is required."))

		off = _offering_core(self.program_offering)
		if not off:
			frappe.throw(_("Invalid Program Offering {0}.").format(get_link_to_form("Program Offering", self.program_offering)))

		# 1) Mirror authoritative values from offering
		if not self.program:
			self.program = off.program
		elif self.program != off.program:
			frappe.throw(_("Enrollment Program {0} does not match Program Offering's Program {1}.")
				.format(get_link_to_form("Program", self.program), get_link_to_form("Program", off.program)))

		# School/cohort always mirror offering (program no longer carries school)
		self.school = off.school
		if off.student_cohort:
			self.cohort = off.student_cohort

		# 2) Academic Year must come from offering AY spine
		ay_spine = _offering_ay_spine(self.program_offering)
		ay_names = [r["academic_year"] for r in ay_spine]
		if self.academic_year:
			if self.academic_year not in ay_names:
				frappe.throw(_("Academic Year {0} is not part of Program Offering {1}.")
					.format(get_link_to_form("Academic Year", self.academic_year), get_link_to_form("Program Offering", self.program_offering)))
		else:
			if len(ay_names) == 1:
				self.academic_year = ay_names[0]
			else:
				frappe.throw(_("Please choose an Academic Year from this Program Offering: {0}.").format(", ".join(ay_names)))

		self._resolve_academic_year()
		self._validate_offering_ay_membership()
		self._validate_school_and_cohort_lock()
		self._validate_terms_membership_and_order()
		self._validate_dropped_requires_date()
		self.validate_duplicate_course()
		self.validate_duplication()

		if not self.student_name:
			self.student_name = frappe.db.get_value("Student", self.student, "student_full_name")
		if not self.courses:
			self.extend("courses", self.get_courses()) 

		if self.academic_year: 
			year_dates = frappe.get_doc("Academic Year", self.academic_year)
			if self.enrollment_date: 
				if getdate(self.enrollment_date) < getdate(year_dates.year_start_date): 
					frappe.throw(_("The enrollment date for this program is before the start of the academic year {0}. The academic year starts on {1}.  Please revise the date.").format(
						get_link_to_form("Academic Year", self.academic_year), 
						year_dates.year_start_date
					))
				if getdate(self.enrollment_date) > getdate(year_dates.year_end_date): 
					frappe.throw(_("The enrollment date for this program is after the start of the academic year {0}. The academic year ends on {1}.  Please revise the date.").format(
						get_link_to_form("Academic Year", self.academic_year), 
						year_dates.year_end_date
					))
		self._validate_course_terms()		

	def before_submit(self):
		self.validate_only_one_active_enrollment()

	def on_submit(self):
		self.update_student_joining_date()


	def _resolve_academic_year(self):
		allowed_schools = [self.school] + get_ancestors_of("School", self.school)

		# 1 ▸ autofill if left blank
		if not self.academic_year:
			self.academic_year = get_effective_record(
				"Academic Year",
				self.school,
				extra_filters={"archived": 0},	
			)
			if not self.academic_year:
				raise ParentRuleViolation(
					_("No active Academic Year found for {0} or its ancestors.")
					.format(self.school)
				)
			return

		# 2 ▸ validate manual pick
		ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school")
		if ay_school not in allowed_schools:
			raise ParentRuleViolation(
				_("Academic Year {0} belongs to {1}, which is outside the allowed hierarchy.")
				.format(self.academic_year, ay_school)
			)
		

	def validate_only_one_active_enrollment(self): 
		"""
    Checks if there's another active (archived=0) Program Enrollment for the same student.
    Raises an error if another active enrollment is found.
    """ 
		if self.archived: 
			return # if archived is checked. 
		
		existing_enrollment = frappe.db.get_value( 
			"Program Enrollment", 
			{ 
				"student": self.student, 
				"archived": 0,  # Check for active enrollments 
				"name": ("!=", self.name)  # Exclude the current document 
			}, 
			["name", "program", "academic_year"],  # Retrieve name, program and year for the error message 
			as_dict=True
		) 
		
		if existing_enrollment: 
			frappe.throw(_( 
				"Student {0} already has an active Program Enrollment for program {1} in academic year {2}.  See {3}."
			).format( 
					self.student_name, 
					get_link_to_form("Program", existing_enrollment.program), 
					existing_enrollment.academic_year, 
					get_link_to_form("Program Enrollment", existing_enrollment.name)
					),title=_("Active Enrollment Exists") # added for better UI message.
      )


	def validate_duplicate_course(self):
		"""ensure courses belong to Program Offering Course spans; prevent duplicates."""
		seen_courses = set()
		off_idx = _offering_courses_index(self.program_offering)

		for row in self.courses:
			# duplicate
			if row.course in seen_courses:
				frappe.throw(_("Course {0} entered twice.").format(get_link_to_form("Course", row.course)))
			seen_courses.add(row.course)

			# existence in offering
			if row.course not in off_idx:
				frappe.throw(_("Course {0} is not part of Program Offering {1}.").format(
					get_link_to_form("Course", row.course),
					get_link_to_form("Program Offering", self.program_offering))
				)

			# compute enrollment window within chosen AY (narrow by terms if provided)
			enr_ay_start, enr_ay_end = _ay_bounds_for(self.program_offering, self.academic_year)
			enr_start, enr_end = enr_ay_start, enr_ay_end
			if row.term_start:
				_school_1, _ay_1, ts_start, _term_end_ignored = _term_meta(row.term_start)
				if ts_start:
					enr_start = max(enr_start, getdate(ts_start))
			if row.term_end:
				_school_2, _ay_2, te_start, te_end = _term_meta(row.term_end)
				if te_end or te_start:
					enr_end = min(enr_end, getdate(te_end) if te_end else getdate(te_start))

			if enr_start and enr_end and enr_start > enr_end:
				frappe.throw(
					_("For course <b>{0}</b>: The start term window is after the end term window.")
					.format(row.course or "")
				)

			# require overlap with at least one offering span
			ok = any((enr_start <= span["end"]) and (span["start"] <= enr_end) for span in off_idx[row.course])
			if not ok:
				frappe.throw(_("Course {0} is not delivered during the selected Academic Year/Term window for this Program Offering.")
					.format(get_link_to_form("Course", row.course)))

	# you cannot enroll twice for the same offering and year
	def validate_duplication(self): 
		existing_enrollment_name = frappe.db.exists("Program Enrollment", { 
			"student": self.student, 
			"program_offering": self.program_offering, 
			"academic_year": self.academic_year, 
			"name": ("!=", self.name)
		})
		if existing_enrollment_name: 
			student_name = self.student_name or frappe.db.get_value("student", self.student, "student_name")
			link_to_existing_enrollment = get_link_to_form("Program Enrollment", existing_enrollment_name)
			frappe.throw(_("Student {0} is already enrolled in this Program Offering for this academic year. See {1}").format(student_name, link_to_existing_enrollment)) 


	def _validate_offering_ay_membership(self):
		"""Enrollment AY must belong to the Program Offering spine."""
		if not (self.program_offering and self.academic_year):
			return
		ay_names = _offering_ay_names(self.program_offering)
		if self.academic_year not in ay_names:
			frappe.throw(
				_("Academic Year {0} is not part of Program Offering {1}.")
				.format(
					get_link_to_form("Academic Year", self.academic_year),
					get_link_to_form("Program Offering", self.program_offering),
				)
			)


	def _validate_terms_membership_and_order(self):
		"""Hard guards on each row's term selection:
		- Term order: end >= start (when both are set and have dates)
		- Term membership: each term's AY must be allowed (enrollment AY and/or offering spine)
		"""
		if not getattr(self, "courses", None):
			return

		# Build the allowed AY set
		allowed_ays = set()
		if self.academic_year:
			allowed_ays.add(self.academic_year)
		# Include all AYs from the offering spine
		allowed_ays.update(_offering_ay_names(self.program_offering) or [])

		# Batch-fetch term metadata
		term_names = {r.term_start for r in self.courses if r.term_start} | {r.term_end for r in self.courses if r.term_end}
		meta = _term_meta_many(term_names)

		# Collect violations for a single, crisp error
		membership_violations = []  # [(course, fld_name, term_name, term_ay)]
		order_violations = []       # [(course, term_start, start_date, term_end, end_date)]

		for r in self.courses:
			ts = r.term_start and meta.get(r.term_start) or None
			te = r.term_end and meta.get(r.term_end) or None

			# Membership checks
			if ts and ts.academic_year and allowed_ays and ts.academic_year not in allowed_ays:
				membership_violations.append((r.course, "term_start", r.term_start, ts.academic_year))
			if te and te.academic_year and allowed_ays and te.academic_year not in allowed_ays:
				membership_violations.append((r.course, "term_end", r.term_end, te.academic_year))

			# Order check (only if both dates exist)
			if ts and te and ts.term_start_date and te.term_end_date:
				if te.term_end_date < ts.term_start_date:
					order_violations.append((r.course, r.term_start, ts.term_start_date, r.term_end, te.term_end_date))

		# Throw with consolidated messages (if any)
		err_lines = []
		if membership_violations:
			err_lines.append("<b>Terms must belong to the selected Academic Year or the Program Offering span:</b>")
			for course, fld, term, term_ay in membership_violations:
				err_lines.append(f"• {frappe.bold(course or '')} — {frappe.bold(fld)} = {term} (AY {term_ay})")

		if order_violations:
			if err_lines:
				err_lines.append("")  # blank line between sections
			err_lines.append("<b>Term order invalid (End before Start):</b>")
			for course, tstart, dstart, tend, dend in order_violations:
				err_lines.append(f"• {frappe.bold(course or '')} — {tstart} ({dstart}) → {tend} ({dend})")

		if err_lines:
			frappe.throw("<br>".join(err_lines))


	def _validate_school_and_cohort_lock(self):
		if not self.program_offering:
			return
		off = _offering_core(self.program_offering)
		if not off:
			# earlier validate() already checks, but keep this idempotent
			return
		if off.get("school") and self.school and self.school != off["school"]:
			frappe.throw(_("School must match Program Offering ({0}).").format(off["school"]))
		target_cohort = off.get("student_cohort")
		if target_cohort and self.cohort and self.cohort != target_cohort:
			frappe.throw(_("Cohort must match Program Offering ({0}).").format(target_cohort))



	def _validate_dropped_requires_date(self):
		missing = [r.course for r in (self.courses or []) if r.status == "Dropped" and not r.dropped_date]
		if missing:
			lines = "<br>".join(f"• {frappe.bold(c or '')}" for c in missing)
			frappe.throw(_("Dropped courses require a Dropped Date:<br>{0}").format(lines))

	# If a student is in a program offering and that offering has required courses,
	# load those that overlap the chosen Academic Year (AY).
	@frappe.whitelist()
	def get_courses(self):
		# Defensive: require offering + AY
		if not (self.program_offering and self.academic_year):
			return []

		# Bounds for the selected AY slice within the offering
		enr_ay_start, enr_ay_end = _ay_bounds_for(self.program_offering, self.academic_year)
		if not (enr_ay_start and enr_ay_end):
			return []

		# Build an index of offering courses with effective spans
		off_idx = _offering_courses_index(self.program_offering)

		rows = []
		# Include only REQUIRED courses that overlap the enrollment AY
		for course, spans in off_idx.items():
			if not any(span.get("required") for span in spans):
				continue
			# Does any span overlap the AY window?
			has_overlap = any((enr_ay_start <= s["end"]) and (s["start"] <= enr_ay_end) for s in spans)
			if not has_overlap:
				continue

			item = {"course": course, "status": "Enrolled"}

			# Optional, same behavior you had: if course doesn’t declare long-term bounds,
			# default term_start/term_end to the school’s AY term bounds for convenience.
			bounds = None
			if self.school:
				bounds = get_school_term_bounds(self.school, self.academic_year)

			term_long = frappe.db.get_value("Course", course, "term_long")
			if not term_long and bounds:
				item["term_start"] = bounds.get("term_start")
				item["term_end"]   = bounds.get("term_end")

			rows.append(item)

		return rows


	# This will update the joining date on the student doctype in function of the joining date of the program.
	def update_student_joining_date(self):
		date = frappe.db.sql("""select min(enrollment_date) from `tabProgram Enrollment` where student= %s""", self.student)
		if date and date[0] and date[0][0]:
			frappe.db.set_value("Student", self.student, "student_joining_date", date[0][0])


	# Ensure all courses use terms from one valid source: either the school or the fallback ancestor, and term_start <= term_end.
	def _validate_course_terms(self):
		valid_terms, source_school = get_terms_for_ay_with_fallback(self.school, self.academic_year)
		if not valid_terms:
			return  # No terms anywhere—let other validations handle this situation

		for row in self.courses:
			# Check valid terms
			if row.term_start and row.term_start not in valid_terms:
				frappe.throw(
					_("Term Start '{0}' must be from {1} for Academic Year '{2}'.").format(
						row.term_start, source_school, self.academic_year
					),
					title=_("Invalid Term Start")
				)
			if row.term_end and row.term_end not in valid_terms:
				frappe.throw(
					_("Term End '{0}' must be from {1} for Academic Year '{2}'.").format(
						row.term_end, source_school, self.academic_year
					),
					title=_("Invalid Term End")
				)

			# Check order: term_start <= term_end
			if row.term_start and row.term_end:
				if row.term_start == row.term_end:
					continue  # ok if same
				term_start_doc = frappe.get_doc("Term", row.term_start)
				term_end_doc = frappe.get_doc("Term", row.term_end)
				if getdate(term_start_doc.term_start_date) > getdate(term_end_doc.term_start_date):
					frappe.throw(
						_("For course <b>{0}</b>: The start term <b>{1}</b> ({2}) must not be after the end term <b>{3}</b> ({4}).")
						.format(
							row.course or "",
							row.term_start, term_start_doc.term_start_date,
							row.term_end, term_end_doc.term_start_date
						),
						title=_("Invalid Term Sequence")
					)
		


# -------------------------
# Program Offering helpers
# -------------------------

def _offering_ay_names(offering: str) -> list[str]:
	"""Return the ordered list of Academic Year names in the Program Offering."""
	if not offering:
		return []
	rows = frappe.get_all(
		"Program Offering Academic Year",
		filters={"parent": offering},
		fields=["academic_year"],
		order_by="year_start_date asc",
		pluck="academic_year",
	)
	return rows or []

def _offering_core(offering_name: str) -> dict | None:
	"""Return head fields of Program Offering (strict field names)."""
	if not offering_name:
		return None
	return frappe.db.get_value(
		"Program Offering",
		offering_name,
		["program", "school", "student_cohort", "start_date", "end_date"],
		as_dict=True,
	)


def _offering_ay_spine(offering_name: str) -> list[dict]:
	rows = frappe.get_all(
		"Program Offering Academic Year",
		filters={"parent": offering_name, "parenttype": "Program Offering"},
		fields=["academic_year", "year_start_date as start", "year_end_date as end"],
		order_by="year_start_date asc"
	)
	return [{"academic_year": r["academic_year"], "start": getdate(r["start"]), "end": getdate(r["end"])} for r in rows]


def _ay_bounds_for(offering_name: str, ay_name: str) -> tuple[object, object]:
	"""(start,end) of an AY from the offering spine; avoids fetching the AY doc."""
	for r in _offering_ay_spine(offering_name):
		if r["academic_year"] == ay_name:
			return r["start"], r["end"]
	return (None, None)


def _term_meta(term: str) -> tuple[str | None, str | None, object | None, object | None]:
	"""(school, academic_year, term_start_date, term_end_date) for Term."""
	return frappe.db.get_value(
		"Term", term, ["school", "academic_year", "term_start_date", "term_end_date"], as_dict=False
	) or (None, None, None, None)

def _term_meta_many(term_names: set[str]) -> dict[str, dict]:
	"""Batch fetch term metadata to minimize DB round-trips."""
	if not term_names:
		return {}
	rows = frappe.get_all(
		"Term",
		filters={"name": ("in", list(term_names))},
		fields=["name", "school", "academic_year", "term_start_date", "term_end_date"],
	)
	return {r.name: r for r in rows}


def _compute_effective_course_span(offering_name: str, roc: dict) -> tuple[object, object]:
	"""
	From a Program Offering Course row dict (keys: start_academic_year, end_academic_year,
	term_start, term_end, from_date, to_date), compute effective (start_dt, end_dt).
	"""
	say, eay = roc.get("start_academic_year"), roc.get("end_academic_year")
	s_ay_start, _s_ay_end = _ay_bounds_for(offering_name, say)
	_e_ay_start, e_ay_end = _ay_bounds_for(offering_name, eay)
	if not (s_ay_start and e_ay_end):
		# sentinel impossible span if spine missing
		return (getdate("1900-01-01"), getdate("1899-12-31"))

	start_dt = s_ay_start
	end_dt = e_ay_end

	if roc.get("term_start"):
		ts_school, ts_ay, t_start, t_end_ignored = _term_meta(roc["term_start"])
		if t_start:
			start_dt = max(start_dt, getdate(t_start))
	if roc.get("term_end"):
		te_school, te_ay, t2_start, t2_end = _term_meta(roc["term_end"])
		if t_end or t_start:
			end_dt = min(end_dt, getdate(t_end) if t_end else getdate(t_start))

	if roc.get("from_date"):
		start_dt = max(start_dt, getdate(roc["from_date"]))
	if roc.get("to_date"):
		end_dt = min(end_dt, getdate(roc["to_date"]))

	return (start_dt, end_dt)


def _offering_courses_index(offering_name: str) -> dict[str, list[dict]]:
	"""
	Index: course -> list of effective spans.
	Each span: {'start': d, 'end': d, 'start_ay':..., 'end_ay':..., 'term_start':..., 'term_end':..., 'required': 0/1}
	"""
	rows = frappe.get_all(
		"Program Offering Course",
		filters={"parent": offering_name, "parenttype": "Program Offering"},
		fields=["course","start_academic_year","end_academic_year","term_start","term_end","from_date","to_date","required","idx"],
		order_by="idx asc"
	)
	idx: dict[str, list[dict]] = {}
	for r in rows:
		s, e = _compute_effective_course_span(offering_name, r)
		item = {
			"start": s, "end": e,
			"start_ay": r.get("start_academic_year"), "end_ay": r.get("end_academic_year"),
			"term_start": r.get("term_start"), "term_end": r.get("term_end"),
			"required": r.get("required") or 0
		}
		idx.setdefault(r["course"], []).append(item)
	return idx


# from JS to filter out students that have already been enrolled for a given year and/or term
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_students(doctype, txt, searchfield, start, page_len, filters):
	page_len = 50

	if not filters.get("academic_year"):
		return []

	enrolled_students = frappe.db.get_values(
    "Program Enrollment",
    filters={
        "academic_year": filters.get("academic_year")
    },
    fieldname="student"
	) or []

	# Efficient and clean conversion to list of dicts (if you want it)
	excluded_students = [d[0] for d in enrolled_students] or [""]

	# Build SQL
	sql = f"""
		SELECT name, student_full_name 
		FROM tabStudent
		WHERE 
			enabled = 1
			AND name NOT IN ({', '.join(['%s'] * len(excluded_students))})
			AND (
			  name LIKE %s
        OR student_full_name LIKE %s
			)
		ORDER BY idx DESC, name
		LIMIT %s, %s
	"""

	# Params: excluded list + search text + pagination
	#params = excluded_students + [f"%{txt}%", start, page_len]
	params = excluded_students + [f"%{txt}%", f"%{txt}%", start, page_len]

	return frappe.db.sql(sql, params)

# from JS to display AY in descending order 
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_academic_years(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe.parse_json(filters) if isinstance(filters, str) else filters or {}

	school = filters.get("school")
	if not school:
		return []

	def find_school_with_ay(school):
		# Search for AYs for this school, else walk up to parent
		while school:
			ay_exists = frappe.db.exists("Academic Year", {"school": school})
			if ay_exists:
				return school
			# Standard NestedSet parent
			parent = frappe.db.get_value("School", school, "parent_school")
			if not parent or parent == school:
				break
			school = parent
		return None

	target_school = find_school_with_ay(school)
	if not target_school:
		return []

	conditions = ["school = %(school)s"]
	values = {"school": target_school}

	if txt:
		conditions.append("name LIKE %(txt)s")
		values["txt"] = f"%{txt}%"

	where_clause = "WHERE " + " AND ".join(conditions)

	return frappe.db.sql(f"""
		SELECT name
		FROM `tabAcademic Year`
		{where_clause}
		ORDER BY year_start_date DESC
		LIMIT %(start)s, %(page_len)s
	""", {
		**values,
		"start": start,
		"page_len": page_len
	})


@frappe.whitelist()
def get_program_courses_for_enrollment(program_offering):
	if not program_offering:
		return []
	courses = frappe.get_all(
		"Program Offering Course",
		filters={"parent": program_offering, "parenttype": "Program Offering"},
		pluck="course",
		order_by="idx asc"
	)
	return [c for c in courses if c]

@frappe.whitelist()
def get_offering_ay_spine(offering: str):
	if not offering:
		return []
	rows = frappe.get_all(
		"Program Offering Academic Year",
		filters={"parent": offering, "parenttype": "Program Offering"},
		fields=["academic_year", "year_start_date", "year_end_date"],
		order_by="year_start_date asc",
		ignore_permissions=True,  # child table; safe + required for client use
	)
	return rows


def get_terms_for_ay_with_fallback(school, academic_year):
    """Returns (terms, source_school) for the best available school: leaf, else nearest ancestor with terms for AY."""
    if not (school and academic_year):
        return [], None
    # 1. Try direct school first
    terms = frappe.db.get_values(
        "Term",
        {"school": school, "academic_year": academic_year},
        "name"
    )
    if terms:
        return [t[0] for t in terms], school
    # 2. Fallback to ancestors in order
    current_school = frappe.get_doc("School", school)
    ancestors = frappe.get_all("School", filters={
        "lft": ["<", current_school.lft],
        "rgt": [">", current_school.rgt]
    }, fields=["name"], order_by="lft desc")
    for ancestor in ancestors:
        ancestor_terms = frappe.db.get_values(
            "Term",
            {"school": ancestor.name, "academic_year": academic_year},
            "name"
        )
        if ancestor_terms:
            return [t[0] for t in ancestor_terms], ancestor.name
    return [], None

@frappe.whitelist()
def get_valid_terms_with_fallback(school, academic_year):
    terms, source_school = get_terms_for_ay_with_fallback(school, academic_year)
    return {
        "valid_terms": terms,
        "source_school": source_school
    }


@frappe.whitelist()
def candidate_courses_for_add_multiple(program_offering: str, academic_year: str, existing: Optional[Sequence[str]] = None):
	"""
	Return candidate courses from Program Offering that overlap the selected Academic Year,
	excluding 'existing'. Each row includes minimal display info and convenience hints.
	"""
	if not (program_offering and academic_year):
		return []

	# Normalize 'existing' (can arrive as JSON string)
	if isinstance(existing, str):
		try:
			existing = frappe.parse_json(existing) or []
		except Exception:
			existing = []
	existing_set = set(existing or [])

	enr_ay_start, enr_ay_end = _ay_bounds_for(program_offering, academic_year)
	if not (enr_ay_start and enr_ay_end):
		return []

	off_idx = _offering_courses_index(program_offering)
	off = _offering_core(program_offering)
	school = off.get("school") if off else None

	out = []
	for course, spans in off_idx.items():
		if course in existing_set:
			continue
		# Overlap with selected AY slice?
		if not any((enr_ay_start <= s["end"]) and (s["start"] <= enr_ay_end) for s in spans):
			continue

		row = {
			"course": course,
			"course_name": frappe.db.get_value("Course", course, "course_name"),
			"required": 1 if any(s.get("required") for s in spans) else 0,
		}

		# Suggest term bounds for non-term-long courses
		if school:
			term_long = frappe.db.get_value("Course", course, "term_long")
			if not term_long:
				bounds = get_school_term_bounds(school, academic_year)
				if bounds:
					row["suggested_term_start"] = bounds.get("term_start")
					row["suggested_term_end"] = bounds.get("term_end")

		out.append(row)

	# Sort: required first, then by earliest span start, then by name
	def _first_start(cname: str):
		try:
			return min(s["start"] for s in off_idx.get(cname, []))
		except ValueError:
			return enr_ay_start

	out.sort(key=lambda r: (-(r["required"]), _first_start(r["course"]), (r["course_name"] or r["course"])))
	return out



@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(
        """
        SELECT name
        FROM `tabAcademic Year`
        WHERE name LIKE %(txt)s
        ORDER BY year_start_date DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len
        },
    )

def get_permission_query_conditions(user):
    # Allow full access to Administrator or System Manager
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return "1=0"  # No access if no default school

    descendant_schools = get_descendant_schools(user_school)
    if not descendant_schools:
        return "1=0"
    schools_list = "', '".join(descendant_schools)
    return f"`tabProgram Enrollment`.`school` IN ('{schools_list}')"

def has_permission(doc, user=None):
    if not user:
        user = frappe.session.user

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return False

    descendant_schools = get_descendant_schools(user_school)
    return doc.school in descendant_schools

def on_doctype_update():
	# idempotent: adds only if missing
	frappe.db.add_index("Program Enrollment", ["student"])
	# useful for AY-scoped lookups
	frappe.db.add_index("Program Enrollment", ["student", "academic_year"])
	# Program Enrollment: speed up lookups from Student Referral flow
	frappe.db.add_index("Program Enrollment", ["student", "archived"])	
	# NEW for Program Offering linkage / reporting
	frappe.db.add_index("Program Enrollment", ["program_offering"])
	frappe.db.add_index("Program Enrollment", ["student", "program_offering"])
	frappe.db.add_index("Program Enrollment", ["student", "program_offering", "academic_year"])