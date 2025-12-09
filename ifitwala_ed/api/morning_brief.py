# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/morning_brief.py

import frappe
from frappe.utils import today, add_days, getdate, formatdate, strip_html
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools

from ifitwala_ed.api.org_comm_utils import check_audience_match

@frappe.whitelist()
def get_briefing_widgets():
	user = frappe.session.user
	roles = frappe.get_roles(user)

	widgets = {}
	widgets["today_label"] = formatdate(today(), "dddd, dd MMMM yyyy")

	# 1. TOP: ORGANIZATIONAL COMMUNICATION
	widgets["announcements"] = get_daily_bulletin(user, roles)

	# 2. BOTTOM: STAFF BIRTHDAYS
	# Visible to all staff roles
	if any(r in roles for r in ["Academic Staff", "Employee", "System Manager", "Instructor"]):
		widgets["staff_birthdays"] = get_staff_birthdays()

	# 3. ANALYTICS (Admin Only)
	if "Academic Admin" in roles or "System Manager" in roles:
		widgets["clinic_volume"] = get_clinic_activity()
		widgets["admissions_pulse"] = get_admissions_pulse()
		widgets["critical_incidents"] = get_critical_incidents_count()

	# 4. INSTRUCTOR CONTEXT
	if "Instructor" in roles:
		my_groups = get_my_student_groups(user)
		if my_groups:
			widgets["medical_context"] = get_medical_context(my_groups)
			widgets["grading_velocity"] = get_pending_grading_tasks(my_groups)
			widgets["my_student_birthdays"] = get_my_student_birthdays(my_groups)

	# 5. LOGS FEED (Admin & Leads)
	if "Academic Admin" in roles or "System Manager" in roles or "Grade Level Lead" in roles:
		widgets["student_logs"] = get_recent_student_logs(user)

	# 6. ATTENDANCE PULSE
	# Admin: 30-day trend
	if "Academic Admin" in roles or "System Manager" in roles or "Academic Assistant" in roles:
		widgets["attendance_trend"] = get_attendance_trend(user)

	# Instructor: My absent students today
	if "Instructor" in roles:
		if my_groups: # Re-use my_groups from Section 4
			widgets["my_absent_students"] = get_my_absent_students(my_groups)
		else:
			# If Section 4 didn't run (e.g. only Instructor role but logic flow), fetch groups
			my_groups = get_my_student_groups(user)
			if my_groups:
				widgets["my_absent_students"] = get_my_absent_students(my_groups)

	return widgets

# ==============================================================================
# SECTION 1: DAILY BULLETIN (Org Communication)
# ==============================================================================

def get_daily_bulletin(user, roles):
	system_today = getdate(today())

	# Use SQL to handle OR condition for brief_end_date (>= today OR NULL)
	sql = """
		SELECT
			name,
			title,
			message,
			communication_type,
			priority,
			brief_end_date,
			brief_start_date,
			interaction_mode,
			allow_private_notes,
			allow_public_thread
		FROM `tabOrg Communication`
		WHERE status = 'Published'
		AND portal_surface IN ('Morning Brief', 'Everywhere')
		AND brief_start_date <= %s
		AND (brief_end_date >= %s OR brief_end_date IS NULL)
		ORDER BY priority DESC, brief_order ASC, creation DESC
		LIMIT 50
	"""
	comms = frappe.db.sql(sql, (system_today, system_today), as_dict=True)

	employee = frappe.db.get_value("Employee", {"user_id": user},
		["name", "school", "organization", "department"],
		as_dict=True
	)

	visible_comms = []

	for c in comms:
		# Expiry Check (Already filtered in query, but double check)
		if c.brief_end_date and getdate(c.brief_end_date) < system_today:
			continue

		if check_audience_match(c.name, user, roles, employee):
			visible_comms.append({
				"name": c.name,
				"title": c.title,
				"content": strip_html(c.message or ""),
				"type": c.communication_type,
				"priority": c.priority,
				"interaction_mode": c.interaction_mode,
				"allow_public_thread": c.allow_public_thread,
				"allow_private_notes": c.allow_private_notes
			})

	return visible_comms

# ==============================================================================
# SECTION 2: ANALYTICS (Admin & Instructor)
# ==============================================================================

def get_clinic_activity():
	"""Count of Student Patient Visits for the last 3 days."""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["school"], as_dict=True)

	filters = {"docstatus": 1}
	if employee and employee.school:
		filters["school"] = employee.school

	dates = [today(), add_days(today(), -1), add_days(today(), -2)]
	data = []
	for d in dates:
		filters["date"] = d
		count = frappe.db.count("Student Patient Visit", filters)
		data.append({"date": formatdate(d, "dd-MMM"), "count": count})
	return data

def get_admissions_pulse():
	"""Weekly new applications count."""
	start_date = add_days(today(), -7)
	results = frappe.db.sql("""
		SELECT COUNT(name) as count, application_status
		FROM `tabStudent Applicant`
		WHERE creation >= %s
		GROUP BY application_status
	""", (start_date), as_dict=True)

	total = sum([r['count'] for r in results])
	return {"total_new_weekly": total, "breakdown": results}

def get_critical_incidents_count():
	"""Count of Open logs marked as 'Requires Follow Up'."""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["school"], as_dict=True)

	filters = {
		"requires_follow_up": 1,
		"follow_up_status": "Open",
		"docstatus": 1
	}

	if employee and employee.school:
		filters["school"] = employee.school

	return frappe.db.count("Student Log", filters)


def get_my_student_groups(user: str) -> list[str]:
	"""Return Student Group names where this user is an instructor.

	Priority:
	1) Employee.user_id → Student Group Instructor.instructor (Link to Employee)
	2) If no match and SGI has `user_id` column → match on that.
	"""
	if not user or user == "Guest":
		return []

	groups: list[str] = []

	# 1) Primary path: Employee → instructor
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if employee:
		groups = frappe.db.get_all(
			"Student Group Instructor",
			filters={"instructor": employee},
			pluck="parent",
		)

	if groups:
		# Deduplicate while preserving order
		return list(dict.fromkeys(groups))

	# 2) Fallback path: direct User link on child table (if present)
	# This protects you if you later move to a User-based link
	if frappe.db.has_column("Student Group Instructor", "user_id"):
		groups = frappe.db.get_all(
			"Student Group Instructor",
			filters={"user_id": user},
			pluck="parent",
		)
		if groups:
			return list(dict.fromkeys(groups))

	return []



def get_pending_grading_tasks(group_names):
	"""Count of past-due, graded tasks for the instructor."""
	if not group_names: return 0
	groups_formatted = "', '".join(group_names)
	return frappe.db.sql(f"""
		SELECT COUNT(name) FROM `tabTask`
		WHERE student_group IN ('{groups_formatted}')
		AND is_graded = 1 AND is_published = 1
		AND status != 'Closed' AND due_date < CURDATE()
	""")[0][0]

def get_medical_context(group_names):
	"""Fetches medical info for students in the instructor's groups."""
	if not group_names:
		return []

	groups_formatted = "', '".join(group_names)

	return frappe.db.sql(
		f"""
		SELECT DISTINCT
			s.student_first_name AS first_name,
			s.student_last_name AS last_name,
			sp.medical_info,
			sp.allergies,
			sp.food_allergies
		FROM `tabStudent Group Student` sgs
		INNER JOIN `tabStudent` s ON sgs.student = s.name
		INNER JOIN `tabStudent Patient` sp ON sp.student = s.name
		WHERE sgs.parent IN ('{groups_formatted}')
			AND sgs.active = 1
			AND sp.medical_info IS NOT NULL
			AND sp.medical_info != ''
		""",
		as_dict=True,
	)



# ==============================================================================
# SECTION 3: STUDENT LOGS FEED
# ==============================================================================

def get_recent_student_logs(user):
	from_date = add_days(today(), -1)
	filters = {
		"date": (">=", from_date),
		"log_type": ("!=", "Medical")
	}

	# FIX: Only fetch 'school' (removed default_school)
	employee = frappe.db.get_value("Employee", {"user_id": user},
		["name", "school"],
		as_dict=True
	)

	if employee and employee.school:
		# FIX: Use utility function get_descendant_schools
		# Admin/Leads at Parent School see logs from Child Schools
		schools = get_descendant_schools(employee.school)
		if schools:
			filters["school"] = ("in", schools)

	logs = frappe.get_all("Student Log",
		fields=["name", "student_name", "student_photo", "log_type", "date", "requires_follow_up", "follow_up_status", "log"],
		filters=filters,
		order_by="date desc, time desc",
		limit=50
	)

	formatted_logs = []
	for l in logs:
		raw_text = strip_html(l.log or "")
		snippet = (raw_text[:120] + '...') if len(raw_text) > 120 else raw_text

		status_color = "gray"
		if l.requires_follow_up:
			if l.follow_up_status == "Open": status_color = "red"
			elif l.follow_up_status == "Completed": status_color = "green"

		formatted_logs.append({
			"name": l.name,
			"student_name": l.student_name,
			"student_photo": l.student_photo,
			"log_type": l.log_type,
			"date_display": formatdate(l.date, "dd-MMM"),
			"snippet": snippet,
			"full_content": l.log,
			"status_color": status_color
		})

	return formatted_logs


# ==============================================================================
# SECTION 4: COMMUNITY PULSE (Birthdays)
# ==============================================================================

def get_staff_birthdays():
	"""
	Active employees with birthdays today or next 3 days.
	Handles year wrap-around (e.g. Dec 31 -> Jan 2).
	"""
	start_md = formatdate(add_days(today(), -4), "MM-dd")
	end_md = formatdate(add_days(today(), 4), "MM-dd")

	condition = "DATE_FORMAT(employee_date_of_birth, '%%m-%%d') BETWEEN %s AND %s"
	if start_md > end_md:
		condition = "(DATE_FORMAT(employee_date_of_birth, '%%m-%%d') >= %s OR DATE_FORMAT(employee_date_of_birth, '%%m-%%d') <= %s)"

	sql = f"""
		SELECT
			employee_full_name as name,
			employee_image as image,
			employee_date_of_birth as date_of_birth
		FROM
			`tabEmployee`
		WHERE
			status = 'Active'
			AND employee_date_of_birth IS NOT NULL
			AND {condition}
		ORDER BY
			DATE_FORMAT(employee_date_of_birth, '%%%%m-%%%%d') ASC
	"""
	return frappe.db.sql(sql, (start_md, end_md), as_dict=True)


def get_my_student_birthdays(group_names):
	"""
	Active students in my groups with birthdays ±4 days.
	"""
	if not group_names:
		return []

	groups_formatted = "', '".join(group_names)

	start_md = formatdate(add_days(today(), -4), "MM-dd")
	end_md = formatdate(add_days(today(), 4), "MM-dd")

	# Handle year wrap (Dec→Jan)
	condition = "DATE_FORMAT(s.student_date_of_birth, '%%m-%%d') BETWEEN %s AND %s"
	if start_md > end_md:
		condition = (
			"(DATE_FORMAT(s.student_date_of_birth, '%%m-%%d') >= %s "
			"OR DATE_FORMAT(s.student_date_of_birth, '%%m-%%d') <= %s)"
		)

	sql = f"""
		SELECT DISTINCT
			s.student_first_name AS first_name,
			s.student_last_name AS last_name,
			s.student_image AS image,
			s.student_date_of_birth AS date_of_birth
		FROM `tabStudent Group Student` sgs
		INNER JOIN `tabStudent` s ON sgs.student = s.name
		WHERE sgs.parent IN ('{groups_formatted}')
			AND sgs.active = 1
			AND s.student_date_of_birth IS NOT NULL
			AND {condition}
		ORDER BY DATE_FORMAT(s.student_date_of_birth, '%%%%m-%%%%d') ASC
	"""

	return frappe.db.sql(sql, (start_md, end_md), as_dict=True)



# ==============================================================================
# SECTION 5: ATTENDANCE PULSE
# ==============================================================================

def get_attendance_trend(user):
	"""
	Returns daily absence count for the last 30 days for the user's school.
	"""
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["school"], as_dict=True)
	if not employee or not employee.school:
		return []

	# Get last 30 days
	end_date = today()
	start_date = add_days(end_date, -30)

	# Count absences (where count_as_present = 0)
	# We group by date.
	sql = """
		SELECT
			sa.attendance_date as date,
			COUNT(*) as count
		FROM `tabStudent Attendance` sa
		INNER JOIN `tabStudent Attendance Code` sac ON sa.attendance_code = sac.name
		WHERE sa.school = %s
		AND sa.attendance_date BETWEEN %s AND %s
		AND sa.docstatus = 1
		AND sac.count_as_present = 0
		GROUP BY sa.attendance_date
		ORDER BY sa.attendance_date ASC
	"""

	results = frappe.db.sql(sql, (employee.school, start_date, end_date), as_dict=True)

	# Fill in missing dates with 0
	# Create a dictionary of existing data
	data_map = {getdate(r.date): r.count for r in results}

	final_data = []
	current_date = getdate(start_date)
	target_date = getdate(end_date)

	while current_date <= target_date:
		# Format date as string for frontend? Or keep as object?
		# Frontend expects string usually, but let's match previous format if any.
		# The query returns date object or string depending on driver.
		# Let's format as YYYY-MM-DD
		d_str = formatdate(current_date, "yyyy-mm-dd")
		count = data_map.get(current_date, 0)
		final_data.append({"date": d_str, "count": count})
		current_date = add_days(current_date, 1)

	return final_data

def get_my_absent_students(group_names):
	"""
	Returns list of students in my groups who are absent TODAY.
	"""
	if not group_names: return []
	groups_formatted = "', '".join(group_names)

	# We want students in these groups who have an attendance record TODAY
	# with a code that counts as absent.

	sql = f"""
		SELECT
			sa.student_name,
			sa.attendance_code,
			sa.student_group,
			sa.remark,
			s.student_photo,
			sac.color as status_color
		FROM `tabStudent Attendance` sa
		INNER JOIN `tabStudent` s ON sa.student = s.name
		INNER JOIN `tabStudent Attendance Code` sac ON sa.attendance_code = sac.name
		WHERE sa.attendance_date = CURDATE()
		AND sa.student_group IN ('{groups_formatted}')
		AND sa.docstatus = 1
		AND sac.count_as_present = 0
	"""


	return frappe.db.sql(sql, as_dict=True)

@frappe.whitelist()
def get_critical_incidents_details():
	"""
	Returns detailed list of Open logs marked as 'Requires Follow Up'.
	"""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["school"], as_dict=True)

	filters = {
		"requires_follow_up": 1,
		"follow_up_status": "Open",
		"docstatus": 1
	}

	if employee and employee.school:
		filters["school"] = employee.school

	logs = frappe.get_all("Student Log",
		filters=filters,
		fields=["name", "student_name", "student_photo", "log_type", "date", "log"],
		order_by="date desc, creation desc"
	)

	for l in logs:
		l.date_display = formatdate(l.date, "dd-MMM")
		raw_text = strip_html(l.log or "")
		l.snippet = (raw_text[:100] + '...') if len(raw_text) > 100 else raw_text

	return logs

@frappe.whitelist()
def get_clinic_visits_trend(time_range="1M"):
	"""
	Returns daily visit counts for the specified range.
	time_range: '1M', '3M', '6M', 'YTD'
	"""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["school"], as_dict=True)

	# Default to user's school, or global if no school assigned (unlikely for staff)
	school_filter = {}
	if employee and employee.school:
		school_filter = {"school": employee.school}

	end_date = today()
	start_date = add_days(end_date, -30) # Default 1M

	if time_range == "3M":
		start_date = add_days(end_date, -90)
	elif time_range == "6M":
		start_date = add_days(end_date, -180)
	elif time_range == "YTD":
		# Academic year start? Or calendar year? Let's assume Academic Year starts Aug 1st?
		# Or just Calendar Year for now as requested "the year so far".
		# Let's use Calendar Year Jan 1st for simplicity unless Academic Year is standard.
		# User said "based on academic year".
		# Let's try to find the current Academic Year.
		academic_year = frappe.db.get_value("Academic Year", {"current": 1}, "year_start_date")
		if academic_year:
			start_date = academic_year
		else:
			# Fallback to Jan 1st of current year
			import datetime
			start_date = f"{datetime.date.today().year}-01-01"

	# Fetch data
	school_condition = "AND school = %(school)s" if school_filter else ""

	sql = f"""
		SELECT date, COUNT(*) as count
		FROM `tabStudent Patient Visit`
		WHERE docstatus = 1
		AND date BETWEEN %(start_date)s AND %(end_date)s
		{school_condition}
		GROUP BY date
		ORDER BY date ASC
	"""

	visits = frappe.db.sql(sql, {
		"school": school_filter.get("school"),
		"start_date": start_date,
		"end_date": end_date
	}, as_dict=True)

	# Fill gaps? Charts usually handle gaps, but filling with 0 is safer for line charts.
	data_map = {getdate(v.date): v.count for v in visits}
	final_data = []

	curr = getdate(start_date)
	end = getdate(end_date)

	while curr <= end:
		d_str = formatdate(curr, "yyyy-mm-dd")
		final_data.append({
			"date": d_str,
			"count": data_map.get(curr, 0)
		})
		curr = add_days(curr, 1)

	return {
		"data": final_data,
		"school": employee.school if employee else "All Schools",
		"range": time_range
	}
