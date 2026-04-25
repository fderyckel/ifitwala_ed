# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def grade_scale_threshold_map(grade_scale, cache=None):
    if not grade_scale:
        frappe.throw(_("Grade Scale is required."))

    if cache is not None and grade_scale in cache:
        return cache[grade_scale]

    rows = frappe.db.get_all(
        "Grade Scale Interval",
        filters={"parent": grade_scale, "parenttype": "Grade Scale"},
        fields=["grade_code", "boundary_interval"],
    )

    grade_map = {}
    for row in rows:
        code = (row.get("grade_code") or "").strip()
        if not code:
            continue
        try:
            value = float(row.get("boundary_interval") or 0)
        except (TypeError, ValueError):
            value = 0.0
        grade_map[code] = value

    if cache is not None:
        cache[grade_scale] = grade_map
    return grade_map


def grade_intervals(grade_scale, cache=None):
    return sorted(
        ((boundary, code) for code, boundary in grade_scale_threshold_map(grade_scale, cache=cache).items()),
        key=lambda item: item[0],
    )


def grade_label_to_numeric(grade_scale, grade_code, cache=None):
    grade_code = (grade_code or "").strip()
    if not grade_code:
        return None

    grade_map = grade_scale_threshold_map(grade_scale, cache=cache)
    return grade_map.get(grade_code)


def resolve_grade_symbol(grade_scale, grade_symbol, cache=None):
    grade_symbol = (grade_symbol or "").strip()
    if not grade_symbol:
        frappe.throw(_("Grade symbol is required."))

    grade_map = grade_scale_threshold_map(grade_scale, cache=cache)
    if grade_symbol not in grade_map:
        allowed = sorted(grade_map.keys())
        preview = ", ".join(allowed[:10])
        if len(allowed) > 10:
            preview = f"{preview}, ..."
        frappe.throw(
            _("Grade symbol '{grade_symbol}' is not valid for scale {grade_scale}. Allowed: {allowed_symbols}").format(
                grade_symbol=grade_symbol,
                grade_scale=grade_scale,
                allowed_symbols=preview or _("(none configured)"),
            )
        )
    return grade_map[grade_symbol]


def grade_label_from_score(grade_scale, numeric_score, cache=None):
    if numeric_score is None or not grade_scale:
        return None

    selected = None
    for boundary, code in grade_intervals(grade_scale, cache=cache):
        try:
            boundary_value = float(boundary or 0)
        except Exception:
            boundary_value = 0.0
        if numeric_score >= boundary_value:
            selected = code
    return selected


def resolve_grade_for_score(grade_scale, numeric_score, cache=None):
    grade_symbol = grade_label_from_score(grade_scale, numeric_score, cache=cache)
    if not grade_symbol:
        return None, None
    return grade_symbol, resolve_grade_symbol(grade_scale, grade_symbol, cache=cache)
