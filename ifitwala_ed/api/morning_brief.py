import frappe
from frappe.utils import today, add_days, formatdate


@frappe.whitelist()
def get_morning_briefing_stats():
	"""
	Aggregates critical metrics for the Morning Briefing dashboard.
	Optimized with SQL and Role-Aware scopes.
	"""
	user_grades = get_allowed_grades()

	# If user has specific restrictions but no grades are returned, they see nothing.
	if user_grades == []:
		return {
			"absent_today": 0,
			"late_today": 0,
			"critical_logs": 0,
			"at_risk_count": 0
		}

	# SQL Filter Generation
	# We assume the 'Student' table holds the grade_level info
	grade_condition = ""
	if user_grades:
		grades_formatted = "', '".join(user_grades)
		grade_condition = f"AND s.grade_level IN ('{grades_formatted}')"

	stats = {
		"absent_today": get_attendance_count("Absent", grade_condition),
		"late_today": get_attendance_count("Late", grade_condition),
		"critical_logs": get_critical_log_count(grade_condition),
		# Placeholder for the advanced logic in next steps
		"at_risk_count": 0
	}

	return stats

def get_allowed_grades():
	"""
	Returns None if user is Admin/Academic Admin (Full Access).
	Returns a list of Grade Levels if restricted.
	Returns [] if restricted but no permissions found.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)

	# Full Access Roles
	if "System Manager" in roles or "Academic Admin" in roles:
		return None

	# Check User Permissions for 'Grade Level' (assuming that's the linkage)
	# This pulls from the standard Frappe User Permission document
	user_perms = frappe.get_user_permissions(user)
	if not user_perms:
		return [] # No specific permissions defined, so no access

	allowed_grades = []
	for perm in user_perms.get("Program", []): # Or 'Grade Level' depending on setup
		allowed_grades.append(perm.get("doc"))

	# Fallback: if they are linked via a 'Grade Level Lead' doctype assignment
	# (We can expand this based on your specific assignment logic)

	return allowed_grades

def get_attendance_count(status, grade_condition):
	"""
	Counts students with specific attendance status for TODAY.
	"""
	date = today()

	sql = f"""
		SELECT
			COUNT(sa.name)
		FROM
			`tabStudent Attendance` sa
		INNER JOIN
			`tabStudent` s ON sa.student = s.name
		WHERE
			sa.attendance_date = %s
			AND sa.status = %s
			AND sa.docstatus = 1
			{grade_condition}
	"""

	return frappe.db.sql(sql, (date, status))[0][0]

def get_critical_log_count(grade_condition):
	"""
	Counts logs that require follow-up and are still Open/In Progress.
	(Replaces previous Severity logic)
	"""
	start_date = add_days(today(), -7)

	sql = f"""
		SELECT
			COUNT(sl.name)
		FROM
			`tabStudent Log` sl
		INNER JOIN
			`tabStudent` s ON sl.student = s.name
		WHERE
			sl.date >= %s
			AND sl.requires_follow_up = 1
			AND sl.follow_up_status IN ('Open', 'In Progress')
			{grade_condition}
	"""

	return frappe.db.sql(sql, (start_date))[0][0]

@frappe.whitelist()
def get_risk_watchlist():
	"""
	Returns a list of students flagged for:
	1. High Velocity (Rapid increase in logs)
	2. Ghosting (Sudden high absenteeism)
	"""
	user_grades = get_allowed_grades()

	# Security: Return empty if restricted and no permissions found
	if user_grades == []:
		return []

	grade_condition = ""
	if user_grades:
		grades_formatted = "', '".join(user_grades)
		grade_condition = f"AND s.grade_level IN ('{grades_formatted}')"

	# 1. Detect Velocity (Behavior)
	velocity_students = get_velocity_risks(grade_condition)

	# 2. Detect Ghosting (Attendance)
	ghosting_students = get_ghosting_risks(grade_condition)

	# 3. Merge Data
	# We want a unified list. A student might be in both.
	watchlist = {}

	for s in velocity_students:
		if s['student'] not in watchlist:
			watchlist[s['student']] = {
				'student_name': s['student_name'],
				'image': s['image'],
				'grade': s['grade_level'],
				'risks': []
			}
		watchlist[s['student']]['risks'].append('High Behavior Velocity')

	for s in ghosting_students:
		if s['student'] not in watchlist:
			watchlist[s['student']] = {
				'student_name': s['student_name'],
				'image': s['image'],
				'grade': s['grade_level'],
				'risks': []
			}
		watchlist[s['student']]['risks'].append('Potential Ghosting')

	return list(watchlist.values())


def get_velocity_risks(grade_condition):
	"""
	Finds students with > 3 logs in the last 30 days.
	"""
	start_date = add_days(today(), -30)

	sql = f"""
		SELECT
			sl.student,
			s.first_name as student_name,
			s.image,
			s.grade_level,
			COUNT(sl.name) as log_count
		FROM
			`tabStudent Log` sl
		INNER JOIN
			`tabStudent` s ON sl.student = s.name
		WHERE
			sl.date >= %s
			{grade_condition}
		GROUP BY
			sl.student
		HAVING
			log_count >= 3
	"""
	return frappe.db.sql(sql, (start_date), as_dict=True)


def get_ghosting_risks(grade_condition):
	"""
	Finds students with >= 3 absences in the last 5 days.
	"""
	start_date = add_days(today(), -5)

	sql = f"""
		SELECT
			sa.student,
			s.first_name as student_name,
			s.image,
			s.grade_level,
			COUNT(sa.name) as absent_count
		FROM
			`tabStudent Attendance` sa
		INNER JOIN
			`tabStudent` s ON sa.student = s.name
		WHERE
			sa.attendance_date >= %s
			AND sa.status = 'Absent'
			{grade_condition}
		GROUP BY
			sa.student
		HAVING
			absent_count >= 3
	"""
	return frappe.db.sql(sql, (start_date), as_dict=True)


@frappe.whitelist()
def get_briefing_widgets():
	"""
	Dispatcher: Returns widgets based on User Role.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)

	widgets = {}

	# 1. TOP: ORGANIZATIONAL COMMUNICATION (Targeted Bulletin)
	widgets["announcements"] = get_daily_bulletin(user, roles)

	# 2. BOTTOM: STAFF BIRTHDAYS
	if "Academic Staff" in roles or "Employee" in roles:
		widgets["staff_birthdays"] = get_staff_birthdays()

	# 3. ANALYTICS (Admin)
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

	# 5. LOGS FEED
	if "Academic Admin" in roles or "System Manager" in roles or "Grade Level Lead" in roles:
		widgets["student_logs"] = get_recent_student_logs(user)

	return widgets


# ==============================================================================
# 1. DAILY BULLETIN (ORG COMMUNICATION)
# ==============================================================================

def get_daily_bulletin(user, roles):
	"""
	Fetches 'Org Communication' based on:
	1. Status = Published
	2. Surface = Morning Brief OR Everywhere
	3. Date = Today falls within brief_start_date and brief_end_date
	4. Audience = Matches User's School, Role, or Team
	"""

	# 1. Fetch Candidates (Time & Surface)
	current_date = today()

	# We fetch the child table 'audiences' eagerly to filter in Python
	# Note: We order by Priority (Critical first), then Brief Order
	comms = frappe.get_all("Org Communication",
		filters={
			"status": "Published",
			"portal_surface": ["in", ["Morning Brief", "Everywhere"]],
			"brief_start_date": ("<=", current_date),
			# OR condition for end_date is harder in get_all, so we filter end_date in python or raw sql
			# Keeping it simple: Fetch all active started, filter expired in loop
		},
		fields=["name", "title", "message", "communication_type", "priority", "brief_end_date", "organization", "school"],
		order_by="priority desc, brief_order asc, creation desc"
	)

	# 2. Get User Context for Audience Matching
	# We need the employee record to know their School and Organization
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "school", "organization", "department"], as_dict=True)

	visible_comms = []

	for c in comms:
		# Date Expiry Check
		if c.brief_end_date and getdate(c.brief_end_date) < getdate(current_date):
			continue

		# Audience Check
		if check_audience_match(c.name, user, roles, employee):
			visible_comms.append({
				"title": c.title,
				"content": c.message, # Rich Text
				"type": c.communication_type,
				"priority": c.priority
			})

	return visible_comms

def check_audience_match(comm_name, user, roles, employee):
	"""
	Checks if the user belongs to any of the audiences defined in the communication.
	"""
	if "System Manager" in roles: return True # Gods see all

	audiences = frappe.get_all("Org Communication Audience",
		filters={"parent": comm_name},
		fields=["target_group", "school", "team", "program"]
	)

	# If no audience rows defined (rare case), default to hidden or visible?
	# Usually safe to hide if not explicitly targeted.
	if not audiences: return False

	for aud in audiences:
		# 1. School Mismatch Check (If audience row specifies a school, user must be in it)
		if aud.school and employee and employee.school != aud.school:
			continue # Skip this row, user is in wrong school

		# 2. Target Group Logic
		if aud.target_group == "Whole Staff":
			return True # User is authenticated, so they are staff

		if aud.target_group == "Academic Staff" and ("Academic Staff" in roles or "Instructor" in roles):
			return True

		if aud.target_group == "Support Staff" and "Academic Staff" not in roles:
			# simplistic check, relies on your Role setup
			return True

		if aud.target_group == "Whole Community":
			return True

		# 3. Team Logic (If you have a Team/Department structure)
		if aud.team and employee and employee.department == aud.team:
			return True

	return False


# ==============================================================================
# NEW: STUDENT LOGS FEED
# ==============================================================================

def get_recent_student_logs(user):
	"""
	Fetches logs from the last 2 days.
	Filters by User's School (and children) + Program (and children).
	"""
	# 1. Timebox: Last 48 hours (Today + Yesterday)
	from_date = add_days(today(), -1)

	filters = {
		"date": (">=", from_date),
		"docstatus": 1 # Only submitted logs
	}

	# 2. Scoping: Get User's Employee Record for School/Program context
	employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "school"], as_dict=True)

	if employee and employee.school:
		# Recursive School Filter
		schools = get_descendants("School", employee.school)
		if schools:
			filters["school"] = ("in", schools)

	# 3. Fetch Data
	logs = frappe.get_all("Student Log",
		fields=[
			"name", "student_name", "student_photo",
			"log_type", "date", "time",
			"requires_follow_up", "follow_up_status",
			"log", "school", "program"
		],
		filters=filters,
		order_by="date desc, time desc",
		limit=50
	)

	# 4. Format for Feed
	formatted_logs = []
	for l in logs:
		# Snippet generation
		raw_text = strip_html(l.log or "")
		snippet = (raw_text[:100] + '...') if len(raw_text) > 100 else raw_text

		# Status Color Logic
		status_color = "gray"
		if l.requires_follow_up:
			if l.follow_up_status == "Open": status_color = "red"
			elif l.follow_up_status == "In Progress": status_color = "orange"
			elif l.follow_up_status == "Completed": status_color = "green"

		formatted_logs.append({
			"name": l.name,
			"student_name": l.student_name,
			"student_photo": l.student_photo,
			"log_type": l.log_type,
			"date_display": formatdate(l.date, "dd-MMM"),
			"snippet": snippet,
			"status_color": status_color,
			"school": l.school,
			"program": l.program
		})

	return formatted_logs

def get_descendants(doctype, parent_name):
	"""
	Helper to get a node and all its children.
	Supports both Nested Set (lft/rgt) and simple parent/child logic.
	"""
	try:
		# Check if Nested Set
		meta = frappe.get_meta(doctype)
		if meta.has_field("lft") and meta.has_field("rgt"):
			node = frappe.db.get_value(doctype, parent_name, ["lft", "rgt", "is_group"], as_dict=True)
			if node and node.is_group:
				return [x.name for x in frappe.get_all(doctype, filters={
					"lft": (">=", node.lft),
					"rgt": ("<=", node.rgt)
				})]
	except Exception:
		pass

	# Default: Return just the parent if no tree structure found
	return [parent_name]

# ==============================================================================
# UNIVERSAL LOGIC
# ==============================================================================

def get_staff_birthdays():
	"""
	Returns active employees with birthdays today or in the next 3 days.
	"""
	# FIX: Changed %%d-%%b to %d-%b so MySQL formats the date instead of escaping it
	sql = """
		SELECT
			employee_full_name as name,
			employee_image as image,
			DATE_FORMAT(employee_date_of_birth, '%d-%b') as birthday_display,
			employee_date_of_birth
		FROM
			`tabEmployee`
		WHERE
			status = 'Active'
			AND employee_date_of_birth IS NOT NULL
			AND (
				DATE_FORMAT(employee_date_of_birth, '%m-%d') BETWEEN
				DATE_FORMAT(CURDATE(), '%m-%d') AND
				DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL 3 DAY), '%m-%d')
			)
		ORDER BY
			DATE_FORMAT(employee_date_of_birth, '%m-%d') ASC
	"""
	return frappe.db.sql(sql, as_dict=True)

# ==============================================================================
# ADMIN LOGIC
# ==============================================================================

def get_clinic_activity():
	"""
	Returns count of student visits for the last 3 days to spot spikes.
	Schema: Student Patient Visit (date)
	"""
	dates = [today(), add_days(today(), -1), add_days(today(), -2)]
	data = []

	for d in dates:
		count = frappe.db.count("Student Patient Visit", {"date": d, "docstatus": 1})
		data.append({"date": formatdate(d, "dd-MMM"), "count": count})

	return data

def get_admissions_pulse():
	"""
	Returns count of new applications received in the last 7 days.
	Schema: Student Applicant (creation, application_status)
	"""
	start_date = add_days(today(), -7)

	sql = """
		SELECT
			COUNT(name) as count,
			application_status
		FROM
			`tabStudent Applicant`
		WHERE
			creation >= %s
		GROUP BY
			application_status
	"""
	results = frappe.db.sql(sql, (start_date), as_dict=True)

	# Format for UI: Total new + Status breakdown
	total = sum([r['count'] for r in results])
	return {"total_new_weekly": total, "breakdown": results}

def get_critical_incidents_count():
	"""
	Recycled from Phase 1: High severity/Follow-up required logs.
	"""
	# Using the 'Other' logic + requires_follow_up as discussed
	return frappe.db.count("Student Log", {
		"requires_follow_up": 1,
		"follow_up_status": "Open",
		"docstatus": 1
	})

# ==============================================================================
# INSTRUCTOR LOGIC
# ==============================================================================

def get_my_student_groups(user):
	"""
	Helper: Returns list of Student Group names where current user is an instructor.
	Schema: Student Group (name) -> Student Group Instructor (instructor) -> User linkage
	"""
	# We need to map User -> Employee to find them in the Instructor child table
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return []

	sql = """
		SELECT DISTINCT parent
		FROM `tabStudent Group Instructor`
		WHERE instructor = %s
	"""
	return [x[0] for x in frappe.db.sql(sql, (employee))]

def get_my_student_birthdays(group_names):
	"""
	Returns students in the instructor's groups who have birthdays today.
	"""
	if not group_names: return []

	groups_formatted = "', '".join(group_names)

	# FIX: Changed %%m-%%d to %m-%d
	sql = f"""
		SELECT DISTINCT
			s.first_name,
			s.last_name,
			s.student_image
		FROM
			`tabStudent Group Student` sgs
		INNER JOIN
			`tabStudent` s ON sgs.student = s.name
		WHERE
			sgs.parent IN ('{groups_formatted}')
			AND sgs.active = 1
			AND DATE_FORMAT(s.date_of_birth, '%m-%d') = DATE_FORMAT(CURDATE(), '%m-%d')
	"""
	return frappe.db.sql(sql, as_dict=True)

def get_medical_context(group_names):
	"""
	Returns Medical Notes for students in the instructor's groups.
	Schema: Student Patient (student, medical_info)
	"""
	if not group_names: return []

	groups_formatted = "', '".join(group_names)

	# Fetch students with non-empty medical info
	sql = f"""
		SELECT DISTINCT
			s.first_name,
			s.last_name,
			sp.medical_info,
			sp.allergies,
			sp.food_allergies
		FROM
			`tabStudent Group Student` sgs
		INNER JOIN
			`tabStudent` s ON sgs.student = s.name
		INNER JOIN
			`tabStudent Patient` sp ON sp.student = s.name
		WHERE
			sgs.parent IN ('{groups_formatted}')
			AND sgs.active = 1
			AND (sp.medical_info IS NOT NULL AND sp.medical_info != '')
	"""
	return frappe.db.sql(sql, as_dict=True)

def get_pending_grading_tasks(group_names):
	"""
	Returns count of Tasks for these groups that are Graded, Past Due, and Published.
	Schema: Task (is_graded, due_date, status, student_group)
	"""
	if not group_names: return 0

	groups_formatted = "', '".join(group_names)

	sql = f"""
		SELECT COUNT(name)
		FROM `tabTask`
		WHERE
			student_group IN ('{groups_formatted}')
			AND is_graded = 1
			AND is_published = 1
			AND status != 'Closed'
			AND due_date < CURDATE()
	"""
	count = frappe.db.sql(sql)[0][0]
	return count

# ==============================================================================
# COUNSELOR LOGIC
# ==============================================================================

def get_risk_watchlist_summary():
	"""
	Simplified Phase 1 Logic for the Widget view.
	"""
	# Placeholder for the full logic we wrote in Phase 1
	# In a real widget, we might just return the COUNT of high-risk students
	return {
		"count": 0, # Connect to Phase 1 'get_risk_watchlist' count
		"description": "Students flagged for velocity or ghosting"
	}
