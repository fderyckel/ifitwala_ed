# ifitwala_ed/tests/factories/academic.py

from __future__ import annotations

import frappe
from frappe.utils import nowdate


def make_academic_year(school: str, prefix: str = "AY"):
    ay = frappe.get_doc(
        {
            "doctype": "Academic Year",
            "academic_year_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "school": school,
        }
    )
    ay.insert()
    return ay


def make_term(academic_year: str, school: str | None = None, prefix: str = "Term"):
    term = frappe.get_doc(
        {
            "doctype": "Term",
            "term_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "academic_year": academic_year,
            "school": school,
            "term_type": "Academic",
            "term_start_date": nowdate(),
            "term_end_date": nowdate(),
        }
    )
    term.insert()
    return term
