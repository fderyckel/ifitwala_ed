import frappe
from frappe.utils import today, add_days

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


