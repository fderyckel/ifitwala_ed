# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from ifitwala_ed.utilities.school_tree import get_descendant_schools

ALLOWED_POLICY_ROLES = {
    "Academic Admin",
    "Academic Assistant",
    "Curriculum Coordinator",
    "System Manager",
    "Administrator",
}

DEFAULT_POLICY_VALUES = {
    "is_active": 1,
    "is_system_default": 1,
    "was_customized": 0,
    "teaching_weight": 1.0,
    "student_weight": 1.0,
    "student_ratio_divisor": 15.0,
    "activity_weight": 1.0,
    "meeting_weight": 0.75,
    "school_event_weight": 0.75,
    "meeting_window_days": 30,
    "future_horizon_days": 14,
    "meeting_blend_mode": "Blended Past + Future",
    "underutilized_threshold": 12.0,
    "high_load_threshold": 24.0,
    "overload_threshold": 30.0,
    "exclude_cancelled_meetings": 1,
    "notes": None,
}

CONFIGURABLE_FIELDS = {
    "is_active",
    "teaching_weight",
    "student_weight",
    "student_ratio_divisor",
    "activity_weight",
    "meeting_weight",
    "school_event_weight",
    "meeting_window_days",
    "future_horizon_days",
    "meeting_blend_mode",
    "underutilized_threshold",
    "high_load_threshold",
    "overload_threshold",
    "exclude_cancelled_meetings",
    "notes",
}


class AcademicLoadPolicy(Document):
    def validate(self):
        self._apply_defaults()
        self._validate_thresholds()
        self._validate_window_values()
        self._validate_single_active_policy()
        self._mark_customization_state()

    def after_insert(self):
        invalidate_academic_load_cache()

    def on_update(self):
        invalidate_academic_load_cache()

    def on_trash(self):
        invalidate_academic_load_cache()

    def _apply_defaults(self):
        for fieldname, value in DEFAULT_POLICY_VALUES.items():
            if self.get(fieldname) in (None, ""):
                self.set(fieldname, value)

    def _validate_thresholds(self):
        underutilized = flt(self.underutilized_threshold)
        high_load = flt(self.high_load_threshold)
        overload = flt(self.overload_threshold)

        if underutilized >= high_load:
            frappe.throw(_("Underutilized Threshold must be lower than High Load Threshold."))

        if high_load >= overload:
            frappe.throw(_("High Load Threshold must be lower than Overload Threshold."))

    def _validate_window_values(self):
        if cint(self.meeting_window_days) <= 0:
            frappe.throw(_("Meeting Window Days must be greater than zero."))

        if cint(self.future_horizon_days) <= 0:
            frappe.throw(_("Future Horizon Days must be greater than zero."))

        if flt(self.student_ratio_divisor) <= 0:
            frappe.throw(_("Student Ratio Divisor must be greater than zero."))

    def _validate_single_active_policy(self):
        if cint(self.is_active or 0) != 1 or not self.school:
            return

        duplicate = frappe.db.get_value(
            "Academic Load Policy",
            {
                "school": self.school,
                "is_active": 1,
                "name": ["!=", self.name],
            },
            "name",
        )
        if duplicate:
            frappe.throw(
                _("School {school} already has an active Academic Load Policy ({policy_name}).").format(
                    school=self.school,
                    policy_name=duplicate,
                )
            )

    def _mark_customization_state(self):
        if self.is_new():
            return

        before = self.get_doc_before_save()
        if not before:
            return

        if any(before.get(fieldname) != self.get(fieldname) for fieldname in CONFIGURABLE_FIELDS):
            self.was_customized = 1


def get_default_policy_values() -> dict[str, Any]:
    return dict(DEFAULT_POLICY_VALUES)


def ensure_default_policy_for_school(
    school: str | None,
    *,
    ignore_permissions: bool = True,
) -> str | None:
    school = (school or "").strip()
    if not school:
        return None

    existing = frappe.db.get_value(
        "Academic Load Policy",
        {"school": school, "is_active": 1},
        "name",
    )
    if existing:
        return existing

    doc = frappe.get_doc(
        {
            "doctype": "Academic Load Policy",
            "school": school,
            **get_default_policy_values(),
        }
    )
    doc.flags.ignore_permissions = ignore_permissions
    doc.insert(ignore_permissions=ignore_permissions)
    return doc.name


def get_active_policy_for_school(school: str | None):
    policy_name = ensure_default_policy_for_school(school, ignore_permissions=True)
    if not policy_name:
        return None
    return frappe.get_doc("Academic Load Policy", policy_name)


def invalidate_academic_load_cache(doc=None, method=None):
    key = "ifitwala_ed:academic_load:version"
    cache = frappe.cache()
    current = cint(cache.get_value(key) or 0)
    cache.set_value(key, current + 1)


def get_academic_load_cache_version() -> int:
    return cint(frappe.cache().get_value("ifitwala_ed:academic_load:version") or 0)


def _allowed_schools_for_user(user: str) -> list[str]:
    user_school = frappe.defaults.get_user_default("school", user=user)
    if not user_school:
        return []

    try:
        return get_descendant_schools(user_school) or [user_school]
    except Exception:
        return [user_school]


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    roles = set(frappe.get_roles(user))
    if user == "Administrator" or "System Manager" in roles:
        return None

    if not roles & ALLOWED_POLICY_ROLES:
        return "1=0"

    schools = _allowed_schools_for_user(user)
    if not schools:
        return "1=0"

    escaped = ", ".join(frappe.db.escape(school, percent=False) for school in schools)
    return f"`tabAcademic Load Policy`.`school` IN ({escaped})"


def has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if user == "Administrator" or "System Manager" in roles:
        return True

    if not roles & ALLOWED_POLICY_ROLES:
        return False

    schools = _allowed_schools_for_user(user)
    return bool(schools) and getattr(doc, "school", None) in schools
