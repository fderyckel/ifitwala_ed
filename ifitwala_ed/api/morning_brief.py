# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/morning_brief.py


import frappe
from frappe.utils import today, add_days, getdate, formatdate, strip_html

@frappe.whitelist()
def get_briefing_widgets():
	"""
	Central Dispatcher for the Morning Briefing Dashboard.
	Aggregates data based on the user's role and context.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)

	widgets = {}

	# ---------------------------------------
	# 1. TOP SECTION: DAILY BULLETIN
	# ---------------------------------------
	# Fetches Org Communications targeted to this user
	widgets["announcements"] = get_daily_bulletin(user, roles)

	# ---------------------------------------
	# 2. MIDDLE LEFT: ANALYTICS & CONTEXT
	# ---------------------------------------
	# Academic Admin / System Manager
	if "Academic Admin" in roles or "System Manager" in roles:
		widgets["clinic_volume"] = get_clinic_activity()
		widgets["admissions_pulse"] = get_admissions_pulse()
		widgets["critical_incidents"] = get_critical_incidents_count()

	# Instructors
	if "Instructor" in roles:
		my_groups = get_my_student_groups(user)
		if my_groups:
			widgets["medical_context"] = get_medical_context(my_groups)
			widgets["grading_velocity"] = get_pending_grading_tasks(my_groups)

	# ---------------------------------------
	# 3. MIDDLE RIGHT: LOGS FEED
	# ---------------------------------------
	# Visible to Admin and Grade Leads for qualitative context
	if "Academic Admin" in roles or "System Manager" in roles or "Grade Level Lead" in roles:
		widgets["student_logs"] = get_recent_student_logs(user)

	# ---------------------------------------
	# 4. BOTTOM SECTION: COMMUNITY PULSE
	# ---------------------------------------
	if "Academic Staff" in roles or "Employee" in roles:
		widgets["staff_birthdays"] = get_staff_birthdays()

	return widgets


# ==============================================================================
# SECTION 1: DAILY BULLETIN (Org Communication)
# ==============================================================================

def get_daily_bulletin(user, roles):
	"""
	Fetches 'Org Communication' based on:
	1. Status = Published
	2. Surface = Morning Brief OR Everywhere
	3. Date = System Today falls within brief_start_date
	4. Audience = Matches User's School, Role, or Team
	"""
	# FIX: Use Frappe System Time, not SQL CURDATE()
	system_today = getdate(today())

	# Fetch Candidates
	comms = frappe.get_all("Org Communication",
		filters={
			"status": "Published",
			"portal_surface": ["in", ["Morning Brief", "Everywhere"]],
			"brief_start_date": ("<=", system_today)
		},
		fields=["name", "title", "message", "communication_type", "priority", "brief_end_date", "brief_start_date"],
		order_by="priority desc, brief_order asc, creation desc"
	)

	# Context for Audience Matching
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "school", "organization", "department"], as_dict=True)

	visible_comms = []

	for c in comms:
		# FIX: Date Expiry Check using Python Date
		if c.brief_end_date and getdate(c.brief_end_date) < system_today:
			continue

		# Audience Check
		if check_audience_match(c.name, user, roles, employee):
			visible_comms.append({
				"title": c.title,
				"content": c.message,
				"type": c.communication_type,
				"priority": c.priority
			})

	return visible_comms

def check_audience_match(comm_name, user, roles, employee):
	"""
	Checks if the user belongs to any of the audiences defined in the communication.
	"""
	if "System Manager" in roles: return True

	audiences = frappe.get_all("Org Communication Audience",
		filters={"parent": comm_name},
		fields=["target_group", "school", "team", "program"]
	)

	if not audiences: return False

	for aud in audiences:
		# 1. School Mismatch Check
		if aud.school and employee and employee.school != aud.school:
			continue

		match_found = False

		# 2. Target Group Logic
		if aud.target_group == "Whole Staff":
			match_found = True
		# FIX: Explicitly check for 'Instructor' role alongside 'Academic Staff' role
		elif aud.target_group == "Academic Staff" and ("Academic Staff" in roles or "Instructor" in roles):
			match_found = True
		elif aud.target_group == "Support Staff" and "Academic Staff" not in roles:
			match_found = True
		elif aud.target_group == "Whole Community":
			match_found = True

		# 3. Team Logic
		if aud.team and employee and employee.department == aud.team:
			match_found = True

		if match_found:
			return True

	return False


# ==============================================================================
# SECTION 2: ANALYTICS (Admin & Instructor)
# ==============================================================================

def get_clinic_activity():
	"""Count of Student Patient Visits for the last 3 days."""
	dates = [today(), add_days(today(), -1), add_days(today(), -2)]
	data = []
	for d in dates:
		count = frappe.db.count("Student Patient Visit", {"date": d, "docstatus": 1})
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
	return frappe.db.count("Student Log", {
		"requires_follow_up": 1,
		"follow_up_status": "Open",
		"docstatus": 1
	})

def get_my_student_groups(user):
	"""Helper: Get Groups where current user is an instructor."""
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee: return []
	return [x[0] for x in frappe.db.sql("SELECT parent FROM `tabStudent Group Instructor` WHERE instructor = %s", (employee))]

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
	if not group_names: return []
	groups_formatted = "', '".join(group_names)

	return frappe.db.sql(f"""
		SELECT DISTINCT s.first_name, s.last_name, sp.medical_info, sp.allergies, sp.food_allergies
		FROM `tabStudent Group Student` sgs
		INNER JOIN `tabStudent` s ON sgs.student = s.name
		INNER JOIN `tabStudent Patient` sp ON sp.student = s.name
		WHERE sgs.parent IN ('{groups_formatted}') AND sgs.active = 1
		AND (sp.medical_info IS NOT NULL AND sp.medical_info != '')
	""", as_dict=True)


# ==============================================================================
# SECTION 3: STUDENT LOGS FEED
# ==============================================================================

def get_recent_student_logs(user):
	"""
	Fetches logs from the last 48 hours for context.
	Scopes results to the User's School (and children).
	"""
	from_date = add_days(today(), -1) # Yesterday + Today

	filters = {
		"date": (">=", from_date),
		"docstatus": 1
	}

	# School Scoping
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "school"], as_dict=True)
	if employee and employee.school:
		schools = get_descendants("School", employee.school)
		if schools:
			filters["school"] = ("in", schools)

	logs = frappe.get_all("Student Log",
		fields=["name", "student_name", "student_photo", "log_type", "date", "requires_follow_up", "follow_up_status", "log"],
		filters=filters,
		order_by="date desc, time desc",
		limit=30
	)

	formatted_logs = []
	for l in logs:
		# Use strip_html to create a clean text snippet for the card view
		raw_text = strip_html(l.log or "")
		snippet = (raw_text[:90] + '...') if len(raw_text) > 90 else raw_text

		# Visual Status Color
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
			"status_color": status_color
		})

	return formatted_logs

def get_descendants(doctype, parent_name):
	"""Recursive helper for Tree structures (Nested Set)."""
	try:
		node = frappe.db.get_value(doctype, parent_name, ["lft", "rgt", "is_group"], as_dict=True)
		if node and node.is_group:
			return [x.name for x in frappe.get_all(doctype, filters={"lft": (">=", node.lft), "rgt": ("<=", node.rgt)})]
	except Exception:
		pass
	return [parent_name]


# ==============================================================================
# SECTION 4: COMMUNITY PULSE (Birthdays)
# ==============================================================================

def get_staff_birthdays():
	"""
	Active employees with birthdays today or next 3 days.
	FIX: Calculates MM-DD strings in Python to force System Time usage.
	"""
	# Get MM-DD strings from Frappe System Time
	start_md = formatdate(today(), "MM-dd")
	end_md = formatdate(add_days(today(), 3), "MM-dd")

	# We pass these python strings to SQL to avoid DB timezone issues
	sql = """
		SELECT
			employee_full_name as name,
			employee_image as image,
			DATE_FORMAT(employee_date_of_birth, '%%d-%%b') as birthday_display
		FROM
			`tabEmployee`
		WHERE
			status = 'Active'
			AND employee_date_of_birth IS NOT NULL
			AND DATE_FORMAT(employee_date_of_birth, '%%m-%%d') BETWEEN %s AND %s
		ORDER BY
			DATE_FORMAT(employee_date_of_birth, '%%m-%%d') ASC
	"""
	return frappe.db.sql(sql, (start_md, end_md), as_dict=True)
