# ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py
# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType

from ifitwala_ed.utilities.school_tree import get_descendant_schools, is_leaf_school

ADMIN_ROLE = "Academic Admin"
SYSTEM_MANAGER_ROLE = "System Manager"


class EndofYearChecklist(Document):
    def validate(self):
        self._validate_scope_selection()
        self._validate_academic_year_school_match()

    def _validate_scope_selection(self):
        if not self.school:
            return
        _validate_school_selection(self.school)

    def _validate_academic_year_school_match(self):
        if not self.school or not self.academic_year:
            return
        ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school")
        if ay_school and ay_school != self.school:
            frappe.throw(
                _("Academic Year must belong to the selected School."),
                title=_("Invalid Academic Year"),
            )

    def _ensure_action_state(self):
        if self.status == "Completed":
            frappe.throw(_("Checklist is completed and actions are locked."))
        if self.status != "In Progress":
            frappe.throw(_("Set status to In Progress before running actions."))

    def _resolve_scope(self):
        self._ensure_action_state()
        if not self.school or not self.academic_year:
            frappe.throw(_("School and Academic Year are required."))

        _validate_school_selection(self.school)
        self._validate_academic_year_school_match()

        ay_name = frappe.db.get_value("Academic Year", self.academic_year, "academic_year_name")
        if not ay_name:
            frappe.throw(_("Academic Year is invalid or missing a name."))

        scope = get_descendant_schools(self.school) or [self.school]
        rows = frappe.get_all(
            "Academic Year",
            filters={"academic_year_name": ay_name, "school": ["in", scope]},
            fields=["name", "school"],
        )
        ay_names = [row.name for row in rows]
        return {"scope": scope, "ay_names": ay_names}

    @frappe.whitelist()
    def archive_academic_year(self):
        scope = self._resolve_scope()
        ay_names = scope.get("ay_names") or []
        if not ay_names:
            return {"processed": 0}

        AY = DocType("Academic Year")
        frappe.qb.update(AY).set(AY.archived, 1).set(AY.visible_to_admission, 0).where(AY.name.isin(ay_names)).run()
        return {"processed": len(ay_names)}

    @frappe.whitelist()
    def archive_terms(self):
        scope = self._resolve_scope()
        ay_names = scope.get("ay_names") or []
        if not ay_names:
            return {"processed": 0}

        Term = DocType("Term")
        frappe.qb.update(Term).set(Term.archived, 1).where(Term.academic_year.isin(ay_names)).run()
        return {"processed": len(ay_names)}

    @frappe.whitelist()
    def archive_program_enrollment(self):
        scope = self._resolve_scope()
        ay_names = scope.get("ay_names") or []
        schools = scope.get("scope") or []
        if not ay_names or not schools:
            return {"processed": 0}

        ProgramEnrollment = DocType("Program Enrollment")
        frappe.qb.update(ProgramEnrollment).set(ProgramEnrollment.archived, 1).where(
            (ProgramEnrollment.academic_year.isin(ay_names)) & (ProgramEnrollment.school.isin(schools))
        ).run()
        return {"processed": len(ay_names)}

    @frappe.whitelist()
    def archive_student_groups(self):
        scope = self._resolve_scope()
        ay_names = scope.get("ay_names") or []
        schools = scope.get("scope") or []
        if not ay_names or not schools:
            return {"processed": 0}

        StudentGroup = DocType("Student Group")
        frappe.qb.update(StudentGroup).set(StudentGroup.status, "Retired").where(
            (StudentGroup.academic_year.isin(ay_names)) & (StudentGroup.school.isin(schools))
        ).run()
        return {"processed": len(ay_names)}


def _is_system_manager(user: str) -> bool:
    if user == "Administrator":
        return True
    return SYSTEM_MANAGER_ROLE in frappe.get_roles(user)


def _get_user_default_school(user: str) -> str | None:
    return frappe.defaults.get_user_default("school", user=user)


def _validate_school_selection(school: str, user: str | None = None) -> None:
    user = user or frappe.session.user
    if _is_system_manager(user):
        return

    default_school = _get_user_default_school(user)
    if not default_school:
        frappe.throw(
            _("A default School is required to use End of Year Checklist."),
            title=_("Missing Default School"),
        )

    allowed = set(get_descendant_schools(default_school) or [default_school])
    if school not in allowed:
        frappe.throw(
            _("You can only select your default School or its descendants."),
            title=_("Invalid School Selection"),
        )

    if not is_leaf_school(school):
        if default_school != school:
            frappe.throw(
                _("Parent School selection requires your default School to match the selected parent School."),
                title=_("Parent Scope Required"),
            )
        roles = set(frappe.get_roles(user))
        if ADMIN_ROLE not in roles:
            frappe.throw(
                _("Parent School selection requires the Academic Admin role."),
                title=_("Insufficient Permissions"),
            )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def school_link_query(doctype, txt, searchfield, start, page_len, filters):
    user = frappe.session.user
    search_txt = f"%{txt or ''}%"

    if _is_system_manager(user):
        return frappe.db.sql(
            """
            SELECT name, school_name
              FROM `tabSchool`
             WHERE name LIKE %s OR school_name LIKE %s
             ORDER BY school_name ASC, name ASC
             LIMIT %s, %s
            """,
            (search_txt, search_txt, start, page_len),
        )

    default_school = _get_user_default_school(user)
    if not default_school:
        return []

    allowed = get_descendant_schools(default_school) or [default_school]
    if not allowed:
        return []

    if ADMIN_ROLE not in frappe.get_roles(user) and not is_leaf_school(default_school):
        allowed = [s for s in allowed if s != default_school]
        if not allowed:
            return []

    placeholders = ", ".join(["%s"] * len(allowed))
    return frappe.db.sql(
        f"""
        SELECT name, school_name
          FROM `tabSchool`
         WHERE name IN ({placeholders})
           AND (name LIKE %s OR school_name LIKE %s)
         ORDER BY school_name ASC, name ASC
         LIMIT %s, %s
        """,
        [*allowed, search_txt, search_txt, start, page_len],
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
    filters = filters or {}
    school = filters.get("school")
    if not school:
        return []

    _validate_school_selection(school)

    search_txt = f"%{txt or ''}%"
    return frappe.db.sql(
        """
        SELECT name
          FROM `tabAcademic Year`
         WHERE school = %s
           AND name LIKE %s
         ORDER BY year_start_date DESC, name DESC
         LIMIT %s, %s
        """,
        (school, search_txt, start, page_len),
    )


@frappe.whitelist()
def get_scope_preview(school: str | None = None) -> dict:
    if not school:
        return {"schools": [], "count": 0}

    _validate_school_selection(school)
    scope = get_descendant_schools(school) or [school]
    rows = frappe.get_all(
        "School",
        filters={"name": ["in", scope]},
        fields=["name", "school_name"],
        order_by="school_name ASC, name ASC",
    )
    return {"schools": rows, "count": len(rows)}
