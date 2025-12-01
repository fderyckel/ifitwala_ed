# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/morning_brief.py


import frappe
from frappe.utils import today, add_days, getdate, formatdate, strip_html

@frappe.whitelist()
def get_briefing_widgets():
	user = frappe.session.user
	roles = frappe.get_roles(user)

	widgets = {}

	# 1. TOP: ANNOUNCEMENTS
	widgets["announcements"] = get_daily_bulletin(user, roles)

	# 2. BOTTOM: STAFF BIRTHDAYS
	if any(r in roles for r in ["Academic Staff", "Employee", "System Manager", "Instructor"]):
		widgets["staff_birthdays"] = get_staff_birthdays()

	# 3. ANALYTICS (Admin)
	if "Academic Admin" in roles or "System Manager" in roles:
		widgets["clinic_volume"] = get_clinic_activity()
		widgets["admissions_pulse"] = get_admissions_pulse()
		widgets["critical_incidents"] = get_critical_incidents_count()

	# 4. INSTRUCTOR
	if "Instructor" in roles:
		my_groups = get_my_student_groups(user)
		if my_groups:
			widgets["medical_context"] = get_medical_context(my_groups)
			widgets["grading_velocity"] = get_pending_grading_tasks(my_groups)
			widgets["my_student_birthdays"] = get_my_student_birthdays(my_groups)

	# 5. LOGS FEED
	if "Academic Admin" in roles or "System Manager" in roles or "Grade Level Lead" in roles:
		widgets["student_logs"] = get_recent_student_logs(user)

	return widgets


# ==============================================================================
# SECTION 1: DAILY BULLETIN (Org Communication)
# ==============================================================================

def get_daily_bulletin(user, roles):
	system_today = getdate(today())

	comms = frappe.get_all("Org Communication",
		filters={
			"status": "Published",
			"portal_surface": ["in", ["Morning Brief", "Everywhere"]],
			"brief_start_date": ("<=", system_today)
		},
		fields=["name", "title", "message", "communication_type", "priority", "brief_end_date", "brief_start_date"],
		order_by="priority desc, brief_order asc, creation desc"
	)

	employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "school", "organization", "department"], as_dict=True)

	visible_comms = []

	for c in comms:
		# Expiry Check
		if c.brief_end_date and getdate(c.brief_end_date) < system_today:
			continue

		if check_audience_match(c.name, user, roles, employee):
			visible_comms.append({
				"title": c.title,
				"content": c.message,
				"type": c.communication_type,
				"priority": c.priority
			})

	return visible_comms

def check_audience_match(comm_name, user, roles, employee):
	if "System Manager" in roles: return True

	audiences = frappe.get_all("Org Communication Audience",
		filters={"parent": comm_name},
		fields=["target_group", "school", "team", "program"]
	)

	if not audiences: return False

	for aud in audiences:
		# 1. Broad Categories (Check these first for speed)
		if aud.target_group == "Whole Community": return True
		if aud.target_group == "Whole Staff": return True # Authenticated user = Staff

		# 2. Role Based
		if aud.target_group == "Academic Staff" and ("Academic Staff" in roles or "Instructor" in roles):
			return True
		if aud.target_group == "Support Staff" and "Academic Staff" not in roles:
			return True

		# 3. Context Based (Requires Employee Record)
		if not employee: continue # Cannot check school/team without employee record

		# School Check: If audience has school, user must match
		if aud.school and employee.school != aud.school:
			continue

		# Team Check
		if aud.team and employee.department == aud.team:
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
	from_date = add_days(today(), -1)
	filters = {"date": (">=", from_date)} # docstatus removed for testing drafts

	employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "school"], as_dict=True)
	if employee and employee.school:
		schools = get_descendants("School", employee.school)
		if schools: filters["school"] = ("in", schools)

	logs = frappe.get_all("Student Log",
		fields=["name", "student_name", "student_photo", "log_type", "date", "requires_follow_up", "follow_up_status", "log"],
		filters=filters,
		order_by="date desc, time desc",
		limit=50
	)

	formatted_logs = []
	for l in logs:
		# Full content for the Dialog
		full_content = l.log or ""
		# Snippet for the Card
		raw_text = strip_html(full_content)
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
			"full_content": full_content, # Sending full HTML for the modal
			"status_color": status_color
		})

	return formatted_logs

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
