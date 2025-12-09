# ifitwala_ed/assessment/gradebook_utils.py

import frappe
from frappe import _
from typing import List, Dict
from frappe.utils.caching import redis_cache

@redis_cache(ttl=86400)
def get_levels_for_criterion(assessment_criteria: str) -> List[Dict]:
    """
    Return list of dicts [{level: <str>, points: <float>}, …] for one Assessment Criteria
    """
    if not assessment_criteria:
        return []
    rows = frappe.get_all(
        "Assessment Criteria Level",
        filters={"parent": assessment_criteria, "parenttype": "Assessment Criteria"},
        fields=["achievement_level as level", "0 as points"],
        order_by="idx asc"
    )
    return rows


def recompute_student_rubric_suggestion(task: str, student: str) -> float:
	"""
	Return the numeric suggestion from rubric rows:

	- Sums level_points of Task Criterion Score for (task, student).
	- DOES NOT write anything to Task Student.
	- Caller is responsible for applying this to mark_awarded if desired.
	"""
	if not (task and student):
		return 0.0

	total = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(level_points), 0)
		FROM `tabTask Criterion Score`
		WHERE parent = %s AND parenttype = 'Task' AND student = %s
		""",
		(task, student),
	)[0][0] or 0.0

	return float(total)



@frappe.whitelist()
def upsert_task_criterion_scores(task: str, student: str, rows: List[Dict]) -> Dict:
    """
    Replace all Task Criterion Score rows for (task, student) with the payload rows.
    Payload rows: [{assessment_criteria, level, level_points, feedback}, …]
    Returns {"suggestion": <float>}
    """
    frappe.only_for(("Instructor", "Academic Admin", "Curriculum Coordinator", "System Manager"))

    if not (task and student):
        frappe.throw(_("Task and Student are required."))

    seen = set()
    for r in rows or []:
        crt = r.get("assessment_criteria")
        if not crt:
            frappe.throw(_("Assessment Criteria is required in each row."))
        key = (student, crt)
        if key in seen:
            frappe.throw(_("Duplicate criterion {0} for student {1}").format(crt, student))
        seen.add(key)

    frappe.db.delete(
        "Task Criterion Score",
        {"parent": task, "parenttype": "Task", "student": student}
    )

    for r in rows or []:
        doc = frappe.get_doc({
            "doctype": "Task Criterion Score",
            "parent": task,
            "parenttype": "Task",
            "parentfield": "task_criterion_score",
            "student": student,
            "assessment_criteria": r.get("assessment_criteria"),
            "level": r.get("level"),
            "level_points": float(r.get("level_points") or 0),
            "feedback": r.get("feedback")
        })
        doc.insert(ignore_permissions=False)

    suggestion = recompute_student_rubric_suggestion(task, student)
    return {"suggestion": suggestion}
