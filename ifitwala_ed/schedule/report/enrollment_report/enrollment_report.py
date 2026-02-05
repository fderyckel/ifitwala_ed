# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from collections import defaultdict
import frappe
from ifitwala_ed.school_settings.school_settings_utils import get_allowed_schools

def execute(filters=None):
	if not filters:
		filters = {}
	
	report_type = filters.get("report_type", "Program")
	
	if report_type == "Course":
		columns = get_course_columns(filters)
		data = get_course_data(filters)
		chart = get_course_chart_data(data)

	elif report_type == "Cohort": 
		columns = get_cohort_columns(filters)
		data = get_cohort_data(filters)
		chart = get_cohort_chart_data(data)   
		
	else:
		columns = get_program_columns(filters)
		data = get_program_data(filters)
		chart = get_program_chart_data(data, filters)
	
	return columns, data, None, chart

def get_program_columns(filters):
	return [
		{"label": "School", "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 200},
		{"label": "Academic Year", "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 200},
		{"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 200},
		{"label": "Enrollment Count", "fieldname": "enrollment_count", "fieldtype": "Int", "width": 150},
	]

def get_program_data(filters):
	user = frappe.session.user
	school_filter = filters.get("school")
	allowed_schools = get_allowed_schools(user, school_filter)
	if not allowed_schools:
		return []

	conditions = ["pe.school IN %(allowed_schools)s"]
	params = {"allowed_schools": allowed_schools}

	if filters.get("program"):
		conditions.append("pe.program = %(program)s")
		params["program"] = filters["program"]
	if filters.get("academic_year"):
		conditions.append("pe.academic_year = %(academic_year)s")
		params["academic_year"] = filters["academic_year"]

	where_clause = "WHERE " + " AND ".join(conditions)

	sql = f"""
	SELECT
		pe.school AS school,
		sc.abbr AS school_abbr,
		pe.academic_year AS academic_year,
		pe.program AS program,
		COUNT(pe.name) AS enrollment_count,
		ay.year_start_date AS year_start_date
	FROM `tabProgram Enrollment` pe
	LEFT JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
	LEFT JOIN `tabSchool` sc ON pe.school = sc.name
	{where_clause}
	GROUP BY pe.school, sc.abbr, pe.academic_year, pe.program, ay.year_start_date
	ORDER BY ay.year_start_date DESC
	"""
	return frappe.db.sql(sql, params, as_dict=True)

def get_program_chart_data(data, filters=None):

	filters = filters or {}
	school_filter = (filters.get("school") or "").strip() or None
	program_filter = (filters.get("program") or "").strip() or None

	data_sorted = sorted(data, key=lambda x: x.get("year_start_date") or "")

	# 🎯 CASE 3: School + Program selected → Single program, no stacking
	if school_filter and program_filter:
		labels = [row.academic_year for row in data_sorted]
		values = [row.enrollment_count for row in data_sorted]
		return {
			"data": {
				"labels": labels,
				"datasets": [
					{"name": program_filter, "values": values}
				]
			},
			"type": "bar",
			"colors": ["#7cd6fd"],
			"barOptions": {"stacked": False},
			"truncateLegends": False
		}

	# 🎯 CASE 2: School selected → Stack by program per academic year
	if school_filter and not program_filter:
		program_map = defaultdict(lambda: defaultdict(int))  # {program: {year: count}}
		year_set = set()

		for row in data_sorted:
			year = row.academic_year
			program = row.program
			count = row.enrollment_count
			program_map[program][year] += count
			year_set.add(year)

		sorted_years = sorted(year_set)
		datasets = []

		color_palette = [
			"#7cd6fd", "#5e64ff", "#743ee2", "#ffa00a", "#00b0f0", "#ff5858", "#00a65a",
			"#ffa3ef", "#99cc00", "#6b5b95", "#00b894", "#fab1a0"
		]

		for program, year_map in program_map.items():
			values = [year_map.get(year, 0) for year in sorted_years]
			datasets.append({
				"name": program,
				"values": values,
				"chartType": "bar"
			})

		return {
			"data": {
				"labels": sorted_years,
				"datasets": datasets
			},
			"type": "bar",
			"colors": color_palette[:len(datasets)],
			"barOptions": {
				"stacked": True
			}
		}

	import hashlib

	def _hash_color(key: str) -> str:
		"""Return a deterministic hex colour for any string."""
		return "#" + hashlib.md5(key.encode()).hexdigest()[:6]

	# 🎯 CASE 1: No school filter → one dataset, distributed colours
	if not school_filter:
		# 1) aggregate totals for each (AY + School) label
		totals        = defaultdict(int)       # {label: total}
		label_school  = {}                     # {label: abbr}
		year_start    = {}                     # {label: date}

		for r in data:
			lbl = r.academic_year             # already contains "(ISS)"
			totals[lbl]       += r.enrollment_count
			label_school[lbl]  = r.school_abbr
			year_start[lbl]    = r.year_start_date

		# 2) stable chronological order then by school abbr
		labels = sorted(totals.keys(),
						key=lambda label: (year_start[label], label_school[label]))

		# 3) colour map – first N from palette, then md5‑hash fallback
		base_palette = ["#7cd6fd", "#00b894", "#ff9f43",
						"#5e64ff", "#ff5858", "#00b0f0", "#ffa3ef"]
		palette_idx, school_colour = 0, {}

		import hashlib
		def _hash_color(txt):
			return "#" + hashlib.md5(txt.encode()).hexdigest()[:6]

		values, colours = [], []
		for lbl in labels:
			abbr = label_school[lbl]
			if abbr not in school_colour:
				school_colour[abbr] = (base_palette[palette_idx]
										if palette_idx < len(base_palette)
										else _hash_color(abbr))
				palette_idx += 1
			values.append(totals[lbl])
			colours.append(school_colour[abbr])

		return {
			"data": {
				"labels": labels,
				"datasets": [{
					"name": "Enrollments",          # single dataset
					"values": values,
					"chartType": "bar"
				}]
			},
			"type": "bar",
			"colors": colours,                      # one colour per bar
			"barOptions": {
				"stacked": False,
				"distributed": True                 # no side‑gaps
			},
			"truncateLegends": False
		}

def get_cohort_columns(filters):
	return [
		{"label": "Academic Year", "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 200},
		{"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 200},
		{"label": "Enrollment Count", "fieldname": "enrollment_count", "fieldtype": "Int", "width": 150},
	]

def get_cohort_data(filters):
	user = frappe.session.user
	school_filter = filters.get("school")
	allowed_schools = get_allowed_schools(user, school_filter)
	if not allowed_schools or not filters.get("student_cohort"):
		return []

	conditions = ["pe.cohort = %(student_cohort)s", "pe.school IN %(allowed_schools)s"]
	params = {
		"student_cohort": filters["student_cohort"],
		"allowed_schools": allowed_schools
	}

	if filters.get("academic_year"):
		conditions.append("pe.academic_year = %(academic_year)s")
		params["academic_year"] = filters["academic_year"]
	if filters.get("program"):
		conditions.append("pe.program = %(program)s")
		params["program"] = filters["program"]

	where_clause = "WHERE " + " AND ".join(conditions)

	sql = f"""
	SELECT
		pe.academic_year,
		pe.program,
		COUNT(pe.name) as enrollment_count,
		ay.year_start_date
	FROM `tabProgram Enrollment` pe
	LEFT JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
	{where_clause}
	GROUP BY pe.academic_year, pe.program, ay.year_start_date
	ORDER BY ay.year_start_date ASC
	"""
	return frappe.db.sql(sql, params, as_dict=True)

def get_cohort_chart_data(data):

	# program_map[program][year] = count
	program_map = defaultdict(lambda: defaultdict(int))
	year_set = set()

	for row in data:
		year = row.academic_year
		program = row.program
		count = row.enrollment_count

		program_map[program][year] += count
		year_set.add(year)

	sorted_years = sorted(year_set)
	datasets = []

	color_palette = [
		"#7cd6fd", "#5e64ff", "#743ee2", "#ffa00a", "#00b0f0", "#ff5858", "#00a65a",
		"#ffa3ef", "#99cc00", "#6b5b95", "#00b894", "#fab1a0"
	]
	_color_index = 0  # noqa: F841

	for program, year_counts in program_map.items():
		values = [year_counts.get(year, 0) for year in sorted_years]
		datasets.append({
			"name": program,
			"values": values,
			"chartType": "bar"
		})

	return {
		"data": {
			"labels": sorted_years,
			"datasets": datasets
		},
		"type": "bar",
		"colors": color_palette[:len(datasets)],
		"barOptions": {
			"stacked": True
		},
		"truncateLegends": False
	}

def get_course_columns(filters):
	return [
		{"label": "School", "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 200},
		{"label": "Academic Year", "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 150},
		{"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 200},
		{"label": "Course", "fieldname": "course", "fieldtype": "Data", "width": 200},
		{"label": "Status", "fieldname": "status", "fieldtype": "Select", "width": 120},
		{"label": "Enrollment Count", "fieldname": "enrollment_count", "fieldtype": "Int", "width": 150},
	]

def get_course_data(filters):
	user = frappe.session.user
	school_filter = filters.get("school")
	allowed_schools = get_allowed_schools(user, school_filter)
	if not allowed_schools:
		return []

	conditions = ["pe.school IN %(allowed_schools)s"]
	params = {"allowed_schools": allowed_schools}

	if filters.get("academic_year"):
		conditions.append("pe.academic_year = %(academic_year)s")
		params["academic_year"] = filters["academic_year"]
	if filters.get("program"):
		conditions.append("pe.program = %(program)s")
		params["program"] = filters["program"]

	where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

	sql = f"""
	SELECT
		pec.course AS course,
		pe.program AS program,
		pe.school AS school,
		pe.academic_year AS academic_year,
		pec.status AS status,
		COUNT(*) AS enrollment_count
	FROM `tabProgram Enrollment Course` pec
	JOIN `tabProgram Enrollment` pe ON pec.parent = pe.name
	{where_clause}
	GROUP BY pec.course, pe.program, pe.school, pe.academic_year, pec.status
	ORDER BY pe.academic_year DESC, pec.course, pe.program, pe.school
	"""
	return frappe.db.sql(sql, params, as_dict=True)

def get_course_chart_data(data):
	# Build {status: {course: count}} mapping
	dataset_map = defaultdict(lambda: defaultdict(int))
	courses = set()

	for row in data:
		course = row.course
		status = row.status
		count = row.enrollment_count

		dataset_map[status][course] = count
		courses.add(course)

	courses = sorted(courses)

	# Predefined colors per status
	status_colors = {
		"Enrolled": "#7cd6fd",
		"Completed": "#5e64ff",
		"Dropped": "#ff5858"
	}

	datasets = []
	for status, course_map in dataset_map.items():
		values = [course_map.get(course, 0) for course in courses]
		datasets.append({
			"name": status,
			"values": values,
			"chartType": "bar"  # bar is still used, even for stacked
		})

	return {
		"data": {
			"labels": courses,
			"datasets": datasets
		},
		"type": "bar",
		"colors": [status_colors.get(ds["name"], "#999999") for ds in datasets],
		"barOptions": {
			"stacked": True  # <<< enables stacked bars
		},
		"truncateLegends": False  # ensures legend labels don't get cut off
	}

@frappe.whitelist()
def get_academic_years_for_school(doctype, txt, searchfield, start, page_len, filters):
	import json

	if isinstance(filters, str):
		filters = json.loads(filters)
	school = filters.get("school")
	if not school:
		return []

	# Get all ancestors (including self) for the selected school
	school_names = [school]
	from frappe.utils.nestedset import get_ancestors_of
	ancestors = get_ancestors_of("School", school)
	if ancestors:
		school_names.extend([row['name'] for row in ancestors])

	# Fetch all Academic Years referenced in Program Enrollment by these schools
	academic_years = frappe.db.sql("""
		SELECT DISTINCT pe.academic_year
		FROM `tabProgram Enrollment` pe
		WHERE pe.school IN %(school_names)s
		AND pe.academic_year IS NOT NULL
		ORDER BY pe.academic_year DESC
		LIMIT %(page_len)s OFFSET %(start)s
	""", {
		"school_names": school_names,
		"page_len": page_len,
		"start": start,
	})

	return [ (row[0],) for row in academic_years if row[0] ]
