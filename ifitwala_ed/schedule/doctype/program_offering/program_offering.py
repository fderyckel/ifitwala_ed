# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, is_leaf_school

# -------------------------
# small DB helpers (used by validate)
# -------------------------

def _ay_fields(ay: str):
	"""Return (school, year_start_date, year_end_date) for Academic Year."""
	if not ay:
		return (None, None, None)
	return frappe.db.get_value(
		"Academic Year",
		ay,
		["school", "year_start_date", "year_end_date"],
		as_dict=False
	) or (None, None, None)

def _term_fields(term: str):
	"""Return (school, academic_year, term_start_date, term_end_date) for Term."""
	if not term:
		return (None, None, None, None)
	return frappe.db.get_value(
		"Term",
		term,
		["school", "academic_year", "term_start_date", "term_end_date"],
		as_dict=False
	) or (None, None, None, None)

def _assert(cond: bool, msg: str):
	if not cond:
		frappe.throw(msg)

# -------------------------
# main document
# -------------------------

class ProgramOffering(Document):

	def validate(self):
		self._validate_required()
		_assert(
			is_leaf_school(self.school),
			_("Program Offering must be anchored on a child (leaf) school with no descendants.")
		)
		allowed = self._allowed_ancestor_schools()

		# 1) Validate AY spine (child table)
		ay_rows = self._validate_offering_ays(allowed)

		# 2) Validate head Start/End against AY span (and basic ordering)
		self._validate_head_window_against_ays(ay_rows)

		# 3) Validate course rows
		self._validate_offering_courses(ay_rows, allowed)

		# 4) Status sanity
		if self.status not in ("Planned", "Active", "Archived"):
			frappe.throw(_("Invalid Status: {0}").format(self.status))
		
		self._validate_catalog_membership()

	# -------------------------
	# helpers
	# -------------------------

	def _validate_required(self):
		_assert(self.program, _("Program is required."))
		_assert(self.school, _("School is required."))

	def _allowed_ancestor_schools(self) -> set[str]:
		if not self.school:
			return set()
		return set(get_ancestor_schools(self.school))

	def _validate_offering_ays(self, allowed_schools: set[str]) -> list[dict]:
		rows = list(self.offering_academic_years or [])
		_assert(rows, _("At least one Academic Year is required."))

		seen = set()
		cols = []
		for idx, r in enumerate(rows, start=1):
			_assert(r.academic_year, _("Row {0}: Academic Year is required.").format(idx))
			ay = r.academic_year
			ay_school, ay_start, ay_end = _ay_fields(ay)
			_assert(ay_school, _("Row {0}: Academic Year {1} has no School set.")
			        .format(idx, get_link_to_form("Academic Year", ay)))
			_assert(ay_school in allowed_schools,
			        _("Row {0}: Academic Year {1} belongs to {2}, which is outside the offering school's ancestry.")
			        .format(idx, get_link_to_form("Academic Year", ay), get_link_to_form("School", ay_school)))
			_assert(ay_start and ay_end,
			        _("Row {0}: Academic Year {1} must have start and end dates.")
			        .format(idx, get_link_to_form("Academic Year", ay)))

			_assert(ay not in seen, _("Duplicate Academic Year: {0}.").format(ay))
			seen.add(ay)
			cols.append({"name": ay, "start": getdate(ay_start), "end": getdate(ay_end), "school": ay_school})

		cols.sort(key=lambda x: x["start"])

		for i in range(1, len(cols)):
			prev, curr = cols[i-1], cols[i]
			_assert(prev["end"] < curr["start"],
			        _("Academic Years overlap: {0} ({1}→{2}) and {3} ({4}→{5}).").format(
			            prev["name"], frappe.format(prev["start"], {"fieldtype": "Date"}),
			            frappe.format(prev["end"], {"fieldtype": "Date"}),
			            curr["name"], frappe.format(curr["start"], {"fieldtype": "Date"}),
			            frappe.format(curr["end"], {"fieldtype": "Date"}),
			        ))
		return cols

	def _validate_head_window_against_ays(self, ay_rows: list[dict]):
		if not (self.start_date or self.end_date):
			return

		_assert(ay_rows, _("Offering dates require at least one Academic Year."))

		head_start = getdate(self.start_date) if self.start_date else None
		head_end = getdate(self.end_date) if self.end_date else None
		if head_start and head_end:
			_assert(head_start <= head_end, _("Start Date cannot be after End Date."))

		min_ay = min(r["start"] for r in ay_rows)
		max_ay = max(r["end"] for r in ay_rows)

		if head_start:
			_assert(min_ay <= head_start <= max_ay,
			        _("Start Date {0} must lie within the spanning Academic Years ({1} → {2}).")
			        .format(frappe.format(head_start, {"fieldtype": "Date"}),
			                frappe.format(min_ay, {"fieldtype": "Date"}),
			                frappe.format(max_ay, {"fieldtype": "Date"})))
		if head_end:
			_assert(min_ay <= head_end <= max_ay,
			        _("End Date {0} must lie within the spanning Academic Years ({1} → {2}).")
			        .format(frappe.format(head_end, {"fieldtype": "Date"}),
			                frappe.format(min_ay, {"fieldtype": "Date"}),
			                frappe.format(max_ay, {"fieldtype": "Date"})))

	def _validate_offering_courses(self, ay_rows: list[dict], allowed_schools: set[str]):
		if not getattr(self, "offering_courses", None):
			return

		ay_index = {r["name"]: r for r in ay_rows}
		min_ay = min(r["start"] for r in ay_rows)
		max_ay = max(r["end"] for r in ay_rows)

		head_start = getdate(self.start_date) if self.start_date else None
		head_end = getdate(self.end_date) if self.end_date else None

		for idx, row in enumerate(self.offering_courses, start=1):
			_assert(row.course, _("Row {0}: Course is required.").format(idx))
			_assert(row.start_academic_year, _("Row {0}: Start Academic Year is required.").format(idx))
			_assert(row.end_academic_year, _("Row {0}: End Academic Year is required.").format(idx))

			start_ay = ay_index.get(row.start_academic_year)
			end_ay = ay_index.get(row.end_academic_year)
			_assert(start_ay, _("Row {0}: Start AY {1} must be listed in Offering Academic Years.")
			        .format(idx, get_link_to_form("Academic Year", row.start_academic_year)))
			_assert(end_ay, _("Row {0}: End AY {1} must be listed in Offering Academic Years.")
			        .format(idx, get_link_to_form("Academic Year", row.end_academic_year)))

			_assert(start_ay["start"] <= end_ay["end"],
			        _("Row {0}: Start AY must not be after End AY.").format(idx))

			start_term_dt = start_ay["start"]
			end_term_dt = end_ay["end"]

			if row.start_term:
				ts_school, ts_ay, ts_start, ts_end = _term_fields(row.start_term)
				_assert(ts_ay == row.start_academic_year,
				        _("Row {0}: Start Term {1} must belong to Start AY {2}.")
				        .format(idx, get_link_to_form("Term", row.start_term),
				                get_link_to_form("Academic Year", row.start_academic_year)))
				_assert(ts_school in allowed_schools,
				        _("Row {0}: Start Term {1} belongs to {2}, outside the offering school's ancestry.")
				        .format(idx, get_link_to_form("Term", row.start_term),
				                get_link_to_form("School", ts_school)))
				_assert(ts_start, _("Row {0}: Start Term {1} is missing term_start_date.")
				        .format(idx, get_link_to_form("Term", row.start_term)))
				start_term_dt = getdate(ts_start)

			if row.end_term:
				te_school, te_ay, te_start, te_end = _term_fields(row.end_term)
				_assert(te_ay == row.end_academic_year,
				        _("Row {0}: End Term {1} must belong to End AY {2}.")
				        .format(idx, get_link_to_form("Term", row.end_term),
				                get_link_to_form("Academic Year", row.end_academic_year)))
				_assert(te_school in allowed_schools,
				        _("Row {0}: End Term {1} belongs to {2}, outside the offering school's tree.")
				        .format(idx, get_link_to_form("Term", row.end_term),
				                get_link_to_form("School", te_school)))
				_assert(te_start or te_end, _("Row {0}: End Term {1} is missing dates.")
				        .format(idx, get_link_to_form("Term", row.end_term)))
				end_term_dt = getdate(te_end) if te_end else getdate(te_start)

			if row.start_term and row.end_term:
				_assert(start_term_dt <= end_term_dt,
				        _("Row {0}: Start Term must not be after End Term.").format(idx))

			row_start = getdate(row.from_date) if row.from_date else start_term_dt
			row_end = getdate(row.to_date) if row.to_date else end_term_dt
			_assert(row_start <= row_end, _("Row {0}: From Date cannot be after To Date.").format(idx))

			_assert(min_ay <= row_start <= max_ay,
			        _("Row {0}: Start {1} must lie within offering Academic Years ({2} → {3}).").format(
			            idx, frappe.format(row_start, {"fieldtype": "Date"}),
			            frappe.format(min_ay, {"fieldtype": "Date"}),
			            frappe.format(max_ay, {"fieldtype": "Date"})))
			_assert(min_ay <= row_end <= max_ay,
			        _("Row {0}: End {1} must lie within offering Academic Years ({2} → {3}).").format(
			            idx, frappe.format(row_end, {"fieldtype": "Date"}),
			            frappe.format(min_ay, {"fieldtype": "Date"}),
			            frappe.format(max_ay, {"fieldtype": "Date"})))

			if head_start:
				_assert(head_start <= row_start,
				        _("Row {0}: Start {1} is before Offering Start Date {2}.").format(
				            idx, frappe.format(row_start, {"fieldtype": "Date"}),
				            frappe.format(head_start, {"fieldtype": "Date"})))
			if head_end:
				_assert(row_end <= head_end,
				        _("Row {0}: End {1} is after Offering End Date {2}.").format(
				            idx, frappe.format(row_end, {"fieldtype": "Date"}),
				            frappe.format(head_end, {"fieldtype": "Date"})))

			if row.start_term and row.from_date:
				_assert(start_term_dt <= getdate(row.from_date),
				        _("Row {0}: From Date is earlier than Start Term window.").format(idx))
			if row.end_term and row.to_date:
				_assert(getdate(row.to_date) <= end_term_dt,
				        _("Row {0}: To Date is later than End Term window.").format(idx))

	def _validate_catalog_membership(self):
		"""If a course isn't in the Program's catalog, require non_catalog + reason."""
		if not getattr(self, "offering_courses", None):
			return

		# Gather catalog set quickly
		catalog_courses = set()
		if frappe.db.table_exists("Program Course"):
			for r in frappe.get_all(
				"Program Course",
				filters={"parent": self.program},
				fields=["course"],
				limit=2000,
			):
				if r.get("course"):
					catalog_courses.add(r["course"])

		for idx, row in enumerate(self.offering_courses, start=1):
			course = row.course
			if not course:
				continue

			is_in_catalog = course in catalog_courses
			is_exception = int(row.get("non_catalog") or 0) == 1

			if not is_in_catalog and not is_exception:
				frappe.throw(_("Row {0}: Course {1} is not in the Program catalog. "
				               "Either add it to Program Course, or mark this row as Non-catalog and provide a justification.")
				             .format(idx, frappe.utils.get_link_to_form("Course", course)))

			if is_exception:
				# Optional: require a reason if field exists
				if "exception_reason" in row.as_dict() and not (row.get("exception_reason") or "").strip():
					frappe.throw(_("Row {0}: Please provide an Exception Justification for the non-catalog course {1}.")
					             .format(idx, frappe.utils.get_link_to_form("Course", course)))


# -------------------------
# one whitelisted helper used by the client
# -------------------------

def _coerce_list(x) -> list[str]:
	if isinstance(x, str):
		try:
			return frappe.parse_json(x) or []
		except Exception:
			return []
	return list(x or [])

@frappe.whitelist()
def compute_program_offering_defaults(program: str, school: str, ay_names=None):
	"""
	Return {"start_date": date|None, "end_date": date|None, "offering_title": str|None}
	- start_date = earliest AY start
	- end_date   = latest AY end
	- offering_title = "<ORG_ABBR> <PROG_ABBR> Cohort of YYYY"
	  (YYYY from latest AY end; if no ends, from latest start)
	"""
	def _list(x):
		if isinstance(x, str):
			try:
				return frappe.parse_json(x) or []
			except Exception:
				return []
		return list(x or [])

	ays = _list(ay_names)

	# Abbreviations (server-side; bypass UI perms)
	prog_abbr = frappe.db.get_value("Program", program, "program_abbreviation")

	org_name = frappe.db.get_value("School", school, "organization")
	org_abbr = None
	if org_name:
		row = frappe.db.sql(
			"select abbr from `tabOrganization` where name = %s",
			(org_name,),
			as_dict=False,
		)
		if row and row[0] and row[0][0]:
			org_abbr = row[0][0]

	# AY envelope
	min_start, max_end = None, None
	if ays:
		for r in frappe.get_all(
			"Academic Year",
			filters={"name": ["in", ays]},
			fields=["year_start_date", "year_end_date"],
		):
			if r.get("year_start_date"):
				sd = getdate(r["year_start_date"])
				min_start = sd if not min_start or sd < min_start else min_start
			if r.get("year_end_date"):
				ed = getdate(r["year_end_date"])
				max_end = ed if not max_end or ed > max_end else max_end

	cohort_year = max_end.year if max_end else (min_start.year if min_start else None)
	title = f"{org_abbr} {prog_abbr} Cohort of {cohort_year}" if (org_abbr and prog_abbr and cohort_year) else None

	return {"start_date": min_start, "end_date": max_end, "offering_title": title}


@frappe.whitelist()
def program_course_options(program: str) -> list:
	"""
	Return catalog items for a Program from Program Course, tolerant of schema:
	- required flag may be named 'required' or 'is_required'
	- 'subject_group' may not exist
	Output:
	[{"course":..., "course_name":..., "required_by_default":0/1, "subject_group":""}, ...]
	"""
	if not program:
		return []

	results: list[dict] = []

	if frappe.db.table_exists("Program Course"):
		meta = frappe.get_meta("Program Course")
		fields = ["course"]
		# detect required field name
		req_field = "required" if meta.has_field("required") else ("is_required" if meta.has_field("is_required") else None)
		if req_field:
			fields.append(req_field)
		has_group = meta.has_field("subject_group")
		if has_group:
			fields.append("subject_group")
		# include optional course_name on Program Course if you have it (not required)
		if meta.has_field("course_name"):
			fields.append("course_name")

		pc_rows = frappe.get_all(
			"Program Course",
			filters={"parent": program},
			fields=fields,
			limit=2000,
		)

		courses = [r["course"] for r in pc_rows if r.get("course")]
		if courses:
			# Pull Course names (fallback label)
			course_names = {r["name"]: (r.get("course_name") or r["name"]) for r in frappe.get_all(
				"Course", filters={"name": ["in", courses]}, fields=["name", "course_name"], limit=len(courses)
			)}
			for r in pc_rows:
				c = r.get("course")
				if not c:
					continue
				required_flag = 0
				if req_field:
					required_flag = 1 if (r.get(req_field) or 0) else 0
				results.append({
					"course": c,
					"course_name": (r.get("course_name") or course_names.get(c) or c),
					"required_by_default": required_flag,
					"subject_group": (r.get("subject_group") or "") if has_group else "",
				})
			if results:
				return results

	# Fallback: all Course (trim)
	for r in frappe.get_all("Course", fields=["name", "course_name"], limit=1000):
		results.append({
			"course": r["name"],
			"course_name": r.get("course_name") or r["name"],
			"required_by_default": 0,
			"subject_group": "",
		})
	return results


@frappe.whitelist()
def hydrate_catalog_rows(program: str, course_names: str) -> list:
	"""
	Given a JSON list of Course names, return ready Program Offering Course rows,
	mapping Program Course defaults (supports 'required' or 'is_required').
	"""
	try:
		names = frappe.parse_json(course_names) or []
	except Exception:
		names = []
	if not names:
		return []

	# Base info from Course
	course_info = {r["name"]: (r.get("course_name") or r["name"]) for r in frappe.get_all(
		"Course", filters={"name": ["in", names]}, fields=["name", "course_name"], limit=len(names)
	)}

	pc_map = {}
	if frappe.db.table_exists("Program Course"):
		meta = frappe.get_meta("Program Course")
		fields = ["course"]
		req_field = "required" if meta.has_field("required") else ("is_required" if meta.has_field("is_required") else None)
		if req_field:
			fields.append(req_field)
		has_group = meta.has_field("subject_group")
		if has_group:
			fields.append("subject_group")

		for r in frappe.get_all(
			"Program Course",
			filters={"parent": program, "course": ["in", names]},
			fields=fields,
			limit=len(names),
		):
			pc_map[r["course"]] = {
				"required": 1 if (r.get(req_field) or 0) else 0 if req_field else 0,
				"elective_group": (r.get("subject_group") or "") if has_group else "",
			}

	rows = []
	for nm in names:
		base = pc_map.get(nm, {"required": 0, "elective_group": ""})
		rows.append({
			"course": nm,
			"course_name": course_info.get(nm) or nm,
			"required": base["required"],
			"elective_group": base["elective_group"],
			"non_catalog": 0,
			"catalog_ref": f"{program}::{nm}",
		})
	return rows


@frappe.whitelist()
def hydrate_non_catalog_rows(course_names: str, exception_reason: str = "") -> list:
	"""
	Given a JSON list of Course names, return minimal rows flagged as non-catalog.
	"""
	try:
		names = frappe.parse_json(course_names) or []
	except Exception:
		names = []
	if not names:
		return []

	course_info = {r["name"]: r.get("course_name") for r in frappe.get_all(
		"Course", filters={"name": ["in", names]}, fields=["name", "course_name"], limit=len(names)
	)}

	return [{
		"course": nm,
		"course_name": course_info.get(nm) or nm,
		"required": 0,
		"elective_group": "",
		"non_catalog": 1,
		"exception_reason": exception_reason or "",
		"catalog_ref": "",
	} for nm in names]
