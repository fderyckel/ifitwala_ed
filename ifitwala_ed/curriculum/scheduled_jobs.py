from __future__ import annotations

import frappe

from ifitwala_ed.curriculum.doctype.course_plan.course_plan import activate_due_course_plan_rollovers


def run_daily_course_plan_activation():
    logger = frappe.logger("ifitwala.curriculum", allow_site=True)
    try:
        return activate_due_course_plan_rollovers()
    except Exception:
        logger.exception("Daily Course Plan activation sweep failed.")
        raise
