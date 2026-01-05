# ifitwala_ed/assessment/gradebook_utils.py

import frappe
from frappe import _
from typing import List, Dict
from frappe.utils.caching import redis_cache

@redis_cache(ttl=86400)
def get_levels_for_criterion(assessment_criteria: str) -> List[Dict]:
    """
    Return list of dicts [{level: <str>, points: <float>}, …] for one Assessment Criteria
    Points are not stored per level; callers may map levels to points separately.
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

    rows = frappe.parse_json(rows) if isinstance(rows, str) else (rows or [])
    if not isinstance(rows, list):
        frappe.throw(_("Invalid payload: rows must be a list."))
    for r in rows:
        if not isinstance(r, dict):
            frappe.throw(_("Invalid payload: each row must be an object."))

    criteria_on = frappe.db.get_value("Task", task, "criteria")
    if not criteria_on:
        frappe.throw(_("Cannot write rubric scores because Task is not in Criteria mode."))

    seen = set()
    for r in rows:
        crt = (r.get("assessment_criteria") or "").strip()
        if not crt:
            frappe.throw(_("Assessment Criteria is required in each row."))
        if crt in seen:
            frappe.throw(_("Duplicate criterion {0} for student {1}").format(crt, student))
        seen.add(crt)
        r["assessment_criteria"] = crt

    sp = frappe.db.savepoint("upsert_task_criterion_scores")
    try:
        frappe.db.delete(
            "Task Criterion Score",
            {"parent": task, "parenttype": "Task", "student": student}
        )

        fields = [
            "parent",
            "parenttype",
            "parentfield",
            "student",
            "assessment_criteria",
            "level",
            "level_points",
            "feedback",
        ]
        values = []
        for r in rows:
            values.append((
                task,
                "Task",
                "task_criterion_score",
                student,
                r.get("assessment_criteria"),
                r.get("level"),
                float(r.get("level_points") or 0),
                r.get("feedback"),
            ))
        if values:
            frappe.db.bulk_insert("Task Criterion Score", fields=fields, values=values)
    except Exception:
        frappe.db.rollback(save_point=sp)
        raise

    suggestion = recompute_student_rubric_suggestion(task, student)
    return {"suggestion": suggestion}
