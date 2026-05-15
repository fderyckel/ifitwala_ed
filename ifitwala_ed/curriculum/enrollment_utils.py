# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from ifitwala_ed.assessment.grade_scale_utils import grade_label_to_numeric


def resolve_min_numeric_score(min_grade, grade_scale, cache=None):
    min_grade = (min_grade or "").strip()
    if not min_grade:
        return None

    try:
        return float(min_grade)
    except (TypeError, ValueError):
        pass

    grade_value = grade_label_to_numeric(grade_scale, min_grade, cache=cache)
    if grade_value is None:
        frappe.throw(
            _("Min grade '{min_grade}' not found in Grade Scale '{grade_scale}'.").format(
                min_grade=min_grade,
                grade_scale=grade_scale,
            )
        )

    return grade_value
