# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/doctype/program_offering/program_offering.py

import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, is_leaf_school, get_descendant_schools
from typing import Optional, Union, Sequence

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
		self._apply_default_span_to_rows()

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
		"""
		For each Program Offering Course row, validate:
			- start/end AY exist in the AY spine and are ordered (start ≤ end by time)
			- if terms are given: term.school ∈ allowed, term.ay matches the row AY, and dates ordered
			- compute an effective [row_start,row_end] using (from/to) or terms or AY bounds
			- ensure effective window is inside head [start_date,end_date] if head dates are set
			- ensure effective window sits within the spanned AY envelope
		"""
		if not getattr(self, "offering_courses", None):
			return

		# quick lookups
		ay_index = {r["name"]: r for r in ay_rows}
		min_ay = min(r["start"] for r in ay_rows)
		max_ay = max(r["end"]   for r in ay_rows)

		head_start = getdate(self.start_date) if self.start_date else None
		head_end   = getdate(self.end_date) if self.end_date else None

		for idx, row in enumerate(self.offering_courses, start=1):
			_assert(row.course, _("Row {0}: Course is required.").format(idx))
			_assert(row.start_academic_year, _("Row {0}: Start Academic Year is required.").format(idx))
			_assert(row.end_academic_year,   _("Row {0}: End Academic Year is required.").format(idx))

			start_ay = ay_index.get(row.start_academic_year)
			end_ay   = ay_index.get(row.end_academic_year)
			_assert(start_ay, _("Row {0}: Start AY {1} must be listed in Offering Academic Years.")
							.format(idx, get_link_to_form("Academic Year", row.start_academic_year)))
			_assert(end_ay,   _("Row {0}: End AY {1} must be listed in Offering Academic Years.")
							.format(idx, get_link_to_form("Academic Year", row.end_academic_year)))

			# AY ordering by dates
			_assert(start_ay["start"] <= end_ay["end"],
							_("Row {0}: Start AY must not be after End AY.").format(idx))

			# Use actual child fieldnames
			start_term_name = getattr(row, "start_academic_term", None)
			end_term_name   = getattr(row, "end_academic_term", None)

			# defaults to AY envelope
			start_term_dt = start_ay["start"]
			end_term_dt   = end_ay["end"]

			# Start term (optional)
			if start_term_name:
				ts_school, ts_ay, ts_start, ts_end = _term_fields(start_term_name)
				_assert(ts_ay == row.start_academic_year,
								_("Row {0}: Start Term {1} must belong to Start AY {2}.")
								.format(idx, get_link_to_form("Term", start_term_name),
												get_link_to_form("Academic Year", row.start_academic_year)))
				_assert(ts_school in allowed_schools,
								_("Row {0}: Start Term {1} belongs to {2}, outside the offering school's tree.")
								.format(idx, get_link_to_form("Term", start_term_name),
												get_link_to_form("School", ts_school)))
				_assert(ts_start, _("Row {0}: Start Term {1} is missing term_start_date.")
								.format(idx, get_link_to_form("Term", start_term_name)))
				start_term_dt = getdate(ts_start)

			# End term (optional)
			if end_term_name:
				te_school, te_ay, te_start, te_end = _term_fields(end_term_name)
				_assert(te_ay == row.end_academic_year,
								_("Row {0}: End Term {1} must belong to End AY {2}.")
								.format(idx, get_link_to_form("Term", end_term_name),
												get_link_to_form("Academic Year", row.end_academic_year)))
				_assert(te_school in allowed_schools,
								_("Row {0}: End Term {1} belongs to {2}, outside the offering school's tree.")
								.format(idx, get_link_to_form("Term", end_term_name),
												get_link_to_form("School", te_school)))
				_assert(te_start or te_end,
								_("Row {0}: End Term {1} is missing dates.")
								.format(idx, get_link_to_form("Term", end_term_name)))
				end_term_dt = getdate(te_end) if te_end else getdate(te_start)

			# If both terms given, enforce term ordering
			if start_term_name and end_term_name:
				_assert(start_term_dt <= end_term_dt,
								_("Row {0}: Start Term must not be after End Term.").format(idx))

			# Effective row span
			row_start = getdate(row.from_date) if row.from_date else start_term_dt
			row_end   = getdate(row.to_date)   if row.to_date   else end_term_dt
			_assert(row_start <= row_end, _("Row {0}: From Date cannot be after To Date.").format(idx))

			# Inside AY envelope
			_assert(min_ay <= row_start <= max_ay,
							_("Row {0}: From Date out of Academic Year span.").format(idx))
			_assert(min_ay <= row_end <= max_ay,
							_("Row {0}: To Date out of Academic Year span.").format(idx))

			# Inside head window if set
			if head_start:
				_assert(head_start <= row_start,
								_("Row {0}: From Date is before Offering Start Date.").format(idx))
			if head_end:
				_assert(row_end <= head_end,
								_("Row {0}: To Date is after Offering End Date.").format(idx))

			# If terms + explicit dates both exist, keep explicit inside term windows
			if start_term_name and row.from_date:
				_assert(start_term_dt <= getdate(row.from_date),
								_("Row {0}: From Date is earlier than Start Term window.").format(idx))
			if end_term_name and row.to_date:
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


	def _get_ay_envelope(self) -> tuple[str | None, str | None]:
		"""Return (start_ay, end_ay) from the ordered Table MultiSelect rows."""
		ay_names = [r.academic_year for r in (self.offering_academic_years or []) if r.academic_year]
		if not ay_names:
			return (None, None)
		return (ay_names[0], ay_names[-1])

	def _apply_default_span_to_rows(self) -> None:
		"""Copy the parent AY envelope into child rows if missing."""
		start_ay, end_ay = self._get_ay_envelope()
		if not start_ay or not end_ay:
			return

		changed = False
		for row in (self.offering_courses or []):
			# Set defaults only if empty—admins can still override per row later
			if not getattr(row, "start_academic_year", None):
				row.start_academic_year = start_ay
				changed = True
			if not getattr(row, "end_academic_year", None):
				row.end_academic_year = end_ay
				changed = True


# -------------------------
# one whitelisted helper used by the client
# -------------------------

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
def program_course_options(
    program: str,
    search: str = "",
    exclude_courses: Optional[Union[str, Sequence[str]]] = None,
):
    """
    Return catalog rows for a Program (Program Course child table),
    excluding any already-present course names and matching an optional search term.
    Each row -> { "course", "course_name", "required" }
    """

    # Coerce exclude_courses to a python list[str]
    if isinstance(exclude_courses, str):
        try:
            exclude = frappe.parse_json(exclude_courses) or []
        except Exception:
            exclude = []
    elif exclude_courses:
        exclude = list(exclude_courses)
    else:
        exclude = []

    filters = {"parent": program}
    if exclude:
        filters["course"] = ["not in", exclude]

    or_filters = []
    if search:
        like = f"%{search}%"
        or_filters = [{"course": ["like", like]}, {"course_name": ["like", like]}]

    pc_rows = frappe.get_all(
        "Program Course",
        filters=filters,
        or_filters=or_filters,
        fields=["course", "course_name", "required"],
        order_by="idx asc",
        limit=2000,
    )

    # normalize booleans/ints to 0/1 for the client
    out = []
    for r in pc_rows:
        out.append(
            {
                "course": r.get("course"),
                "course_name": r.get("course_name") or r.get("course"),
                "required": 1 if r.get("required") else 0,
            }
        )

    return out


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


@frappe.whitelist()
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
	txt = (txt or "").strip()
	school = (filters or {}).get("school")
	conds, params = [], []

	if school:
		conds.append("ay.school = %s")
		params.append(school)
	if txt:
		conds.append("(ay.name LIKE %(txt)s OR ay.academic_year_name LIKE %(txt)s)")

	where_sql = "WHERE " + " AND ".join(conds) if conds else ""
	sql = f"""
		SELECT ay.name AS value, ay.academic_year_name AS description
		FROM `tabAcademic Year` ay
		{where_sql}
		ORDER BY ay.year_start_date DESC, ay.name DESC
		LIMIT %(page_len)s OFFSET %(start)s
	"""
	return [
		[r.get("value"), r.get("description") or r.get("value")]
		for r in frappe.db.sql(
			sql,
			tuple(params),
			as_dict=True,
			values={"txt": f"%{txt}%", "page_len": int(page_len or 20), "start": int(start or 0)},
		)
	]


def _user_school_chain(user: str) -> list[str]:
	"""
	Return the list of schools the user can act on:
	- Leaf school users: [self]
	- Parent school users: [self + descendants]
	"""
	user_school = frappe.defaults.get_user_default("school", user)
	if not user_school:
		return []

	# get_descendant_schools(user_school) in your utilities already includes self.
	# If the school is a leaf, that call returns [self] anyway — but we keep the branch explicit for clarity.
	if is_leaf_school(user_school):
		return [user_school]

	return get_descendant_schools(user_school)


def get_permission_query_conditions(user: str):
	"""
	Limit list views to Program Offerings in the user's school tree.
	Admins/System Managers see everything.
	"""
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return None

	schools = _user_school_chain(user)
	if not schools:
		return "1=0"

	in_list = ", ".join(frappe.db.escape(s) for s in schools)
	return f"`tabProgram Offering`.`school` in ({in_list})"


def has_permission(doc, ptype: str, user: str) -> bool:
	"""
	Doc-level enforcement:
	- Read/Write/Delete allowed iff doc.school is in user's school tree
	- Admin/System Manager bypass
	- For Create (doc is usually None), defer to Role Permission Manager; restrict via link field filters in the UI.
	"""
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	# For create, Frappe calls this with doc=None; leave it to RPR + link-field filters.
	if not doc:
		return True

	schools = _user_school_chain(user)
	if not schools:
		return False

	return doc.school in schools


def on_doctype_update():
	frappe.db.add_index("Program Offering", ["program", "school"])

