# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import Iterable

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate

from ifitwala_ed.students.doctype.student.student import get_permission_query_conditions as get_student_scope_condition

INSIGHT_CATEGORIES = {
    "Learning Support",
    "Access",
    "Wellbeing",
    "Strength",
    "Interest",
    "Achievement",
    "Relationship Starter",
}
INSIGHT_SOURCES = {
    "Family",
    "Admissions",
    "Teacher",
    "Counselor",
    "Learning Support",
    "System",
}
INSIGHT_STATUSES = {"Active", "Needs Review", "Archived"}
INSIGHT_VISIBILITIES = {"Teachers", "Learning Support", "Counselor", "Admissions/Admin"}

SYSTEM_WIDE_USERS = {"Administrator"}
SYSTEM_WIDE_ROLE_NAMES = {"System Manager"}
ADMIN_VISIBILITY_ROLES = {
    "Academic Admin",
    "Academic Assistant",
    "Admission Manager",
    "Admission Officer",
}
TEACHER_VISIBILITY_ROLES = {"Instructor", "Academic Staff", "Curriculum Coordinator", "Pastoral Lead"}
LEARNING_SUPPORT_VISIBILITY_ROLES = {"Learning Support"}
COUNSELOR_VISIBILITY_ROLES = {"Counselor"}
CREATE_ROLES = (
    ADMIN_VISIBILITY_ROLES
    | TEACHER_VISIBILITY_ROLES
    | LEARNING_SUPPORT_VISIBILITY_ROLES
    | COUNSELOR_VISIBILITY_ROLES
    | {"System Manager"}
)
WRITE_ROLES = CREATE_ROLES
READ_LIKE_PTYPES = {None, "read", "select", "report", "print", "email"}


APPLICANT_NOTE_SPECS = (
    {
        "key": "learning-support",
        "category": "Learning Support",
        "visibility": "Learning Support",
        "fields": (
            ("learning_support_status", "Learning support status"),
            ("learning_needs", "Learning needs"),
            ("existing_support_plans", "Existing support plans or reports"),
            ("family_support_priorities", "Family support priorities"),
        ),
    },
    {
        "key": "access-support",
        "category": "Access",
        "visibility": "Teachers",
        "fields": (
            ("effective_supports", "Supports that help"),
            ("physical_access_needs", "Physical or access needs"),
        ),
    },
    {
        "key": "wellbeing",
        "category": "Wellbeing",
        "visibility": "Counselor",
        "fields": (("social_emotional_needs", "Social / emotional needs"),),
    },
    {
        "key": "strengths",
        "category": "Strength",
        "visibility": "Teachers",
        "fields": (
            ("student_strengths", "Strengths and qualities"),
            ("student_motivators", "Motivation and engagement"),
            ("student_voice_notes", "Student voice notes"),
        ),
    },
    {
        "key": "relationship-starter",
        "category": "Relationship Starter",
        "visibility": "Teachers",
        "fields": (
            ("student_interests", "Hobbies and interests"),
            ("student_activities", "Activities and service"),
            ("student_relationship_notes", "Relationship notes"),
        ),
    },
    {
        "key": "achievement",
        "category": "Achievement",
        "visibility": "Teachers",
        "fields": (("student_achievements", "Achievements and recognition"),),
    },
)


class StudentInsightNote(Document):
    def validate(self):
        self._normalize_values()
        self._validate_enum_values()
        self._validate_dates()
        self._set_student_scope()
        self._validate_writer_visibility()

    def _normalize_values(self):
        self.student = _clean_value(self.student)
        self.category = _clean_value(self.category)
        self.source = _clean_value(self.source) or "System"
        self.status = _clean_value(self.status) or "Active"
        self.visibility = _clean_value(self.visibility) or "Teachers"
        self.summary = _clean_text(self.summary)
        self.source_student_applicant = _clean_value(self.source_student_applicant)
        self.source_key = _clean_value(self.source_key)
        if not self.effective_from:
            self.effective_from = nowdate()

    def _validate_enum_values(self):
        if not self.student:
            frappe.throw(_("Student is required."))
        if not self.summary:
            frappe.throw(_("Summary is required."))
        if self.category not in INSIGHT_CATEGORIES:
            frappe.throw(_("Invalid insight category: {category}.").format(category=self.category or ""))
        if self.source not in INSIGHT_SOURCES:
            frappe.throw(_("Invalid insight source: {source}.").format(source=self.source or ""))
        if self.status not in INSIGHT_STATUSES:
            frappe.throw(_("Invalid insight status: {status}.").format(status=self.status or ""))
        if self.visibility not in INSIGHT_VISIBILITIES:
            frappe.throw(_("Invalid insight visibility: {visibility}.").format(visibility=self.visibility or ""))

    def _validate_dates(self):
        if self.effective_from and self.review_on:
            if getdate(self.review_on) < getdate(self.effective_from):
                frappe.throw(_("Review On cannot be before Effective From."))

    def _set_student_scope(self):
        student_row = frappe.db.get_value(
            "Student",
            self.student,
            ["name", "anchor_school"],
            as_dict=True,
        )
        if not student_row:
            frappe.throw(_("Student {student} was not found.").format(student=self.student))

        self.school = student_row.get("anchor_school")
        self.organization = None
        if self.school:
            self.organization = frappe.db.get_value("School", self.school, "organization")

    def _validate_writer_visibility(self):
        if getattr(frappe.flags, "in_migration", False) or getattr(frappe.flags, "in_patch", False):
            return
        roles = set(frappe.get_roles(frappe.session.user) or [])
        if frappe.session.user in SYSTEM_WIDE_USERS or roles & SYSTEM_WIDE_ROLE_NAMES:
            return

        if roles & ADMIN_VISIBILITY_ROLES:
            return

        allowed = _allowed_visibility_values(frappe.session.user)
        if self.visibility in allowed:
            return

        frappe.throw(
            _("You cannot save Student Insight Notes with visibility {visibility}.").format(visibility=self.visibility),
            frappe.PermissionError,
        )


def _clean_value(value) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _clean_text(value) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _dedupe(values: Iterable[str | None]) -> list[str]:
    out = []
    seen = set()
    for value in values or []:
        cleaned = _clean_value(value)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out


def _allowed_visibility_values(user: str | None = None) -> set[str]:
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user) or [])
    if user in SYSTEM_WIDE_USERS or roles & (SYSTEM_WIDE_ROLE_NAMES | ADMIN_VISIBILITY_ROLES):
        return set(INSIGHT_VISIBILITIES)

    allowed: set[str] = set()
    if roles & TEACHER_VISIBILITY_ROLES:
        allowed.add("Teachers")
    if roles & LEARNING_SUPPORT_VISIBILITY_ROLES:
        allowed.update({"Teachers", "Learning Support"})
    if roles & COUNSELOR_VISIBILITY_ROLES:
        allowed.update({"Teachers", "Counselor"})
    return allowed


def _can_create_or_write(user: str | None = None) -> bool:
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user) or [])
    if user in SYSTEM_WIDE_USERS or roles & SYSTEM_WIDE_ROLE_NAMES:
        return True
    return bool(roles & WRITE_ROLES)


def _interpolate_sql_params(sql: str, params: dict) -> str:
    out = sql
    for key, value in (params or {}).items():
        placeholder = f"%({key})s"
        if isinstance(value, (list, tuple, set)):
            escaped = [frappe.db.escape(item) for item in value]
            replacement = f"({', '.join(escaped)})" if escaped else "(NULL)"
        else:
            replacement = frappe.db.escape(value)
        out = out.replace(placeholder, replacement)
    return out


def get_student_insight_visibility_predicate(
    user: str | None = None,
    *,
    table_alias: str = "`tabStudent Insight Note`",
) -> tuple[str, dict]:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "0=1", {}

    roles = set(frappe.get_roles(user) or [])
    if user in SYSTEM_WIDE_USERS or roles & (SYSTEM_WIDE_ROLE_NAMES | ADMIN_VISIBILITY_ROLES):
        visibility_sql = "1=1"
        params: dict = {}
    else:
        allowed_visibilities = sorted(_allowed_visibility_values(user))
        if not allowed_visibilities:
            return "0=1", {}
        visibility_sql = f"{table_alias}.visibility IN %(visibilities)s"
        params = {"visibilities": tuple(allowed_visibilities)}

    student_scope = get_student_scope_condition(user)
    if not student_scope:
        return visibility_sql, params

    scoped_sql = f"""
        EXISTS (
            SELECT 1
            FROM `tabStudent`
            WHERE `tabStudent`.name = {table_alias}.student
              AND {student_scope}
        )
    """
    return f"({visibility_sql}) AND ({scoped_sql})", params


def get_permission_query_conditions(user: str | None = None) -> str | None:
    sql, params = get_student_insight_visibility_predicate(user)
    return _interpolate_sql_params(sql, params)


def has_permission(doc, ptype: str | None = "read", user: str | None = None) -> bool:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    roles = set(frappe.get_roles(user) or [])
    if user in SYSTEM_WIDE_USERS or roles & SYSTEM_WIDE_ROLE_NAMES:
        return True

    if ptype == "create":
        return _can_create_or_write(user)

    if ptype in READ_LIKE_PTYPES or ptype == "write":
        if ptype == "write" and not _can_create_or_write(user):
            return False
        note_name = doc if isinstance(doc, str) else getattr(doc, "name", None)
        if not note_name:
            return False
        sql, params = get_student_insight_visibility_predicate(user=user, table_alias="sin")
        if sql == "1=1":
            return True
        row = frappe.db.sql(
            f"""
            SELECT 1
            FROM `tabStudent Insight Note` sin
            WHERE sin.name = %(note_name)s
              AND {sql}
            LIMIT 1
            """,
            {**params, "note_name": note_name},
        )
        return bool(row)

    return False


def _filter_visible_students(student_names: list[str], user: str | None = None) -> list[str]:
    names = _dedupe(student_names)
    if not names:
        return []

    user = user or frappe.session.user
    student_scope = get_student_scope_condition(user)
    if not student_scope:
        return names

    rows = frappe.db.sql(
        f"""
        SELECT `tabStudent`.name
        FROM `tabStudent`
        WHERE `tabStudent`.name IN %(students)s
          AND {student_scope}
        """,
        {"students": tuple(names)},
        as_dict=True,
    )
    return [row.get("name") for row in rows if row.get("name")]


def _serialize_note(row) -> dict:
    return {
        "name": row.get("name"),
        "category": row.get("category"),
        "summary": row.get("summary"),
        "source": row.get("source"),
        "effective_from": str(row.get("effective_from") or "") or None,
        "review_on": str(row.get("review_on") or "") or None,
        "status": row.get("status"),
        "visibility": row.get("visibility"),
    }


def _build_note_summary(rows: list[dict]) -> dict | None:
    if not rows:
        return None

    today = getdate(nowdate())
    needs_review_count = 0
    categories = []
    for row in rows:
        if row.get("category") and row.get("category") not in categories:
            categories.append(row.get("category"))
        review_on = row.get("review_on")
        if row.get("status") == "Needs Review" or (review_on and getdate(review_on) <= today):
            needs_review_count += 1

    notes = [_serialize_note(row) for row in rows[:5]]
    latest_summary = notes[0].get("summary") if notes else None
    return {
        "active_count": len(rows),
        "needs_review_count": needs_review_count,
        "categories": categories,
        "latest_summary": latest_summary,
        "notes": notes,
    }


def build_student_insight_summaries(student_names, user: str | None = None) -> dict[str, dict]:
    user = user or frappe.session.user
    visible_students = _filter_visible_students(student_names, user=user)
    if not visible_students:
        return {}

    allowed_visibilities = sorted(_allowed_visibility_values(user))
    roles = set(frappe.get_roles(user) or [])
    if not (user in SYSTEM_WIDE_USERS or roles & (SYSTEM_WIDE_ROLE_NAMES | ADMIN_VISIBILITY_ROLES)):
        if not allowed_visibilities:
            return {}
        visibility_filter = "AND visibility IN %(visibilities)s"
        params: dict = {"visibilities": tuple(allowed_visibilities)}
    else:
        visibility_filter = ""
        params = {}

    rows = frappe.db.sql(
        f"""
        SELECT
            name,
            student,
            category,
            summary,
            source,
            effective_from,
            review_on,
            status,
            visibility,
            modified
        FROM `tabStudent Insight Note`
        WHERE student IN %(students)s
          AND status IN ('Active', 'Needs Review')
          AND (effective_from IS NULL OR effective_from <= %(today)s)
          {visibility_filter}
        ORDER BY
            student ASC,
            CASE WHEN status = 'Needs Review' THEN 0 ELSE 1 END ASC,
            CASE WHEN review_on IS NULL THEN 1 ELSE 0 END ASC,
            review_on ASC,
            modified DESC
        """,
        {**params, "students": tuple(visible_students), "today": nowdate()},
        as_dict=True,
    )

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        student = row.get("student")
        if student:
            grouped.setdefault(student, []).append(row)

    return {student: _build_note_summary(student_rows) for student, student_rows in grouped.items()}


@frappe.whitelist()
def get_student_insight_summaries(students=None):
    if isinstance(students, str):
        try:
            students = json.loads(students)
        except Exception:
            students = frappe.parse_json(students)
    if not isinstance(students, list):
        frappe.throw(_("Students must be a list."))
    return build_student_insight_summaries(students)


def _applicant_field_lines(applicant, fields: tuple[tuple[str, str], ...]) -> list[str]:
    lines = []
    for fieldname, label in fields:
        value = _clean_text(applicant.get(fieldname))
        if value:
            lines.append(f"{label}: {value}")
    return lines


def create_student_insight_notes_from_applicant(applicant, student_name: str) -> int:
    if not applicant or not student_name:
        return 0

    effective_from = applicant.get("student_joining_date") or nowdate()
    review_on = add_days(effective_from, 90)
    created_or_updated = 0

    for spec in APPLICANT_NOTE_SPECS:
        lines = _applicant_field_lines(applicant, spec["fields"])
        if not lines:
            continue

        summary = "\n".join(lines)
        source_key = f"Student Applicant:{applicant.name}:{spec['key']}"
        existing = frappe.db.get_value("Student Insight Note", {"source_key": source_key}, "name")
        if existing:
            note = frappe.get_doc("Student Insight Note", existing)
            if note.status == "Archived":
                continue
            note.update(
                {
                    "student": student_name,
                    "category": spec["category"],
                    "summary": summary,
                    "source": "Family",
                    "effective_from": effective_from,
                    "review_on": review_on,
                    "visibility": spec["visibility"],
                    "source_student_applicant": applicant.name,
                }
            )
            note.save(ignore_permissions=True)
            created_or_updated += 1
            continue

        frappe.get_doc(
            {
                "doctype": "Student Insight Note",
                "student": student_name,
                "category": spec["category"],
                "summary": summary,
                "source": "Family",
                "effective_from": effective_from,
                "review_on": review_on,
                "status": "Active",
                "visibility": spec["visibility"],
                "source_student_applicant": applicant.name,
                "source_key": source_key,
            }
        ).insert(ignore_permissions=True)
        created_or_updated += 1

    return created_or_updated


def on_doctype_update():
    frappe.db.add_index("Student Insight Note", ["student", "status", "visibility"])
    frappe.db.add_index("Student Insight Note", ["school", "status"])
    frappe.db.add_index("Student Insight Note", ["review_on"])
