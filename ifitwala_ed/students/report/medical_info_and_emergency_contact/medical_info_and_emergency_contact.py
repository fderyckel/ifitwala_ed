# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from functools import lru_cache

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.utils import cint, cstr, escape_html, getdate, strip_html_tags, today
from frappe.utils.nestedset import get_descendants_of

from ifitwala_ed.utilities.school_tree import get_descendant_schools


def execute(filters=None):
    filters = _prepare_filters(filters or {})
    columns = _get_columns()
    data = _build_rows(filters)
    return columns, data


def _prepare_filters(filters: dict) -> frappe._dict:
    f = frappe._dict(filters or {})

    if not f.get("student_group"):
        frappe.throw(_("Please select a Student Group."))

    group = frappe.db.get_value(
        "Student Group",
        f.student_group,
        ["name", "student_group_name", "status", "program", "school", "academic_year"],
        as_dict=True,
    )

    if not group:
        frappe.throw(_("Student Group {0} was not found.").format(f.student_group))

    if (group.status or "").lower() != "active":
        frappe.throw(_("Student Group {0} is not Active.").format(group.student_group_name or group.name))

    f._student_group = group

    if f.get("school"):
        schools = get_descendant_schools(f.school) or [f.school]
        if group.school and schools and group.school not in schools:
            frappe.throw(
                _("Student Group {0} does not belong to School {1}.").format(
                    group.student_group_name or group.name, f.school
                )
            )
        f._school_scope = schools

    if f.get("program"):
        programs = _expand_program_scope(f.program)
        if group.program and programs and group.program not in programs:
            frappe.throw(
                _("Student Group {0} is not tied to Program {1}.").format(
                    group.student_group_name or group.name, f.program
                )
            )
        f._program_scope = programs

    return f


def _expand_program_scope(program: str | None) -> list[str]:
    if not program:
        return []
    descendants = get_descendants_of("Program", program) or []
    return [program, *descendants]


def _get_columns():
    return [
        {"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 130},
        {"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 180},
        {"label": _("Age"), "fieldname": "age", "fieldtype": "Data", "width": 80},
        {"label": _("Guardian Contacts"), "fieldname": "guardian_contacts", "fieldtype": "HTML", "width": 320},
        {"label": _("Primary Guardian"), "fieldname": "guardian_primary_name", "fieldtype": "Data", "width": 190},
        {"label": _("Primary Phone"), "fieldname": "guardian_primary_phone", "fieldtype": "Data", "width": 150},
        {"label": _("Secondary Guardian"), "fieldname": "guardian_secondary_name", "fieldtype": "Data", "width": 190},
        {"label": _("Secondary Phone"), "fieldname": "guardian_secondary_phone", "fieldtype": "Data", "width": 150},
        {"label": _("Medical Information"), "fieldname": "medical_summary", "fieldtype": "HTML", "width": 360},
    ]


def _build_rows(filters: frappe._dict) -> list[dict]:
    group = filters._student_group
    students = _fetch_group_students(group.name)
    if not students:
        return []

    student_ids = [row.student for row in students if row.student]
    patient_map = _fetch_patients(student_ids)
    guardian_map = _fetch_guardian_contacts(student_ids)

    program_label = frappe.db.get_value("Program", group.program, "program_name") if group.program else None
    school_label = frappe.db.get_value("School", group.school, "school_name") if group.school else None
    group_label = group.student_group_name or group.name

    rows = []
    for student in students:
        student_id = student.student
        patient = patient_map.get(student_id)
        g_info = guardian_map.get(student_id) or {}
        medical_html = _render_medical_summary(patient)
        if not medical_html:
            medical_html = f"<span class='text-muted'>{escape_html(_('No medical information provided.'))}</span>"

        guardian_html = g_info.get("html")
        if not guardian_html:
            guardian_html = f"<span class='text-muted'>{escape_html(_('No guardian contacts recorded.'))}</span>"

        rows.append(
            {
                "student": student_id,
                "student_name": student.student_name or student_id,
                "age": _format_age(student.student_date_of_birth),
                "medical_summary": medical_html,
                "guardian_contacts": guardian_html,
                "guardian_primary_name": g_info.get("primary_name"),
                "guardian_primary_phone": g_info.get("primary_phone"),
                "guardian_secondary_name": g_info.get("secondary_name"),
                "guardian_secondary_phone": g_info.get("secondary_phone"),
                "_student_image": student.student_image,
                "_group_label": group_label,
                "_program_label": program_label,
                "_school_label": school_label,
                "_student_group_name": group.name,
                "_program": group.program,
                "_school": group.school,
                "_academic_year": group.academic_year,
            }
        )
    return rows


def _fetch_group_students(group_name: str) -> list[frappe._dict]:
    return frappe.db.sql(
        """
		select
			sgs.student,
			coalesce(s.student_full_name, sgs.student_name) as student_name,
			s.student_preferred_name,
			s.student_date_of_birth,
			s.student_image
		from `tabStudent Group Student` sgs
		left join `tabStudent` s on s.name = sgs.student
		where sgs.parent = %s and sgs.active = 1
		order by coalesce(s.student_full_name, sgs.student_name)
		""",
        (group_name,),
        as_dict=True,
    )


def _fetch_patients(student_ids: list[str]) -> dict[str, frappe._dict]:
    if not student_ids:
        return {}

    fieldnames = {"student", "name"}
    fieldnames.update({df["fieldname"] for df in _medical_field_defs()})
    rows = frappe.get_all(
        "Student Patient",
        filters={"student": ["in", student_ids]},
        fields=sorted(fieldnames),
    )
    return {row.student: row for row in rows}


def _fetch_guardian_contacts(student_ids: list[str]) -> dict[str, dict]:
    if not student_ids:
        return {}

    guardian_rows = frappe.get_all(
        "Student Guardian",
        fields=["parent", "guardian", "guardian_name", "relation", "email", "phone"],
        filters={"parent": ["in", student_ids]},
        order_by="parent asc, idx asc",
    )
    if not guardian_rows:
        return {}

    guardian_ids = {row.guardian for row in guardian_rows if row.guardian}
    guardian_details = {}
    if guardian_ids:
        gd_rows = frappe.get_all(
            "Guardian",
            fields=[
                "name",
                "guardian_full_name",
                "guardian_mobile_phone",
                "guardian_email",
                "guardian_work_phone",
                "guardian_work_email",
                "work_place",
            ],
            filters={"name": ["in", list(guardian_ids)]},
        )
        guardian_details = {row.name: row for row in gd_rows}

    contacts_by_student: dict[str, dict] = {}
    for row in guardian_rows:
        guardian_doc = guardian_details.get(row.guardian)
        block = _render_guardian_block(row, guardian_doc)
        if not block:
            continue
        entry = contacts_by_student.setdefault(
            row.parent,
            {
                "blocks": [],
                "primary_name": None,
                "primary_phone": None,
                "secondary_name": None,
                "secondary_phone": None,
            },
        )
        entry["blocks"].append(block)
        label = _primary_guardian_label(row, guardian_doc)
        phone = _pick_primary_phone(row, guardian_doc)
        if label and not entry["primary_name"]:
            entry["primary_name"] = label
        elif label and not entry["secondary_name"]:
            entry["secondary_name"] = label
        if phone and not entry["primary_phone"]:
            entry["primary_phone"] = phone
        elif phone and not entry["secondary_phone"]:
            entry["secondary_phone"] = phone

    return {
        student: {
            "html": "<hr class='guardian-divider'>".join(info["blocks"]),
            "primary_name": info.get("primary_name"),
            "primary_phone": info.get("primary_phone"),
            "secondary_name": info.get("secondary_name"),
            "secondary_phone": info.get("secondary_phone"),
        }
        for student, info in contacts_by_student.items()
    }


def _render_guardian_block(child_row: frappe._dict, guardian_doc: frappe._dict | None) -> str:
    name = (
        (guardian_doc.guardian_full_name if guardian_doc else None)
        or child_row.guardian_name
        or child_row.guardian
        or ""
    ).strip()
    if not name:
        return ""

    relation = (child_row.relation or "").strip()
    header = f"<div class='gc-head'><strong>{escape_html(name)}</strong>"
    if relation:
        header += f" <span class='gc-relation'>({escape_html(relation)})</span>"
    header += "</div>"

    phones = _unique_sequence(
        [
            child_row.phone,
            guardian_doc.guardian_mobile_phone if guardian_doc else None,
            guardian_doc.guardian_work_phone if guardian_doc else None,
        ]
    )
    emails = _unique_sequence(
        [
            child_row.email,
            guardian_doc.guardian_email if guardian_doc else None,
            guardian_doc.guardian_work_email if guardian_doc else None,
        ]
    )

    details = []
    if phones:
        details.append(
            f"<div class='gc-line'><span class='gc-label'>{escape_html(_('Phone'))}:</span> {escape_html('; '.join(phones))}</div>"
        )
    if emails:
        details.append(
            f"<div class='gc-line'><span class='gc-label'>{escape_html(_('Email'))}:</span> {escape_html('; '.join(emails))}</div>"
        )
    if guardian_doc and guardian_doc.work_place:
        details.append(
            f"<div class='gc-line'><span class='gc-label'>{escape_html(_('Work'))}:</span> {escape_html(guardian_doc.work_place)}</div>"
        )

    body = "".join(details) or f"<div class='gc-line text-muted'>{escape_html(_('No contact info provided.'))}</div>"
    return f"<div class='guardian-block'>{header}{body}</div>"


def _primary_guardian_label(child_row: frappe._dict, guardian_doc: frappe._dict | None) -> str | None:
    name = (
        (guardian_doc.guardian_full_name if guardian_doc else None)
        or child_row.guardian_name
        or child_row.guardian
        or ""
    ).strip()
    if not name:
        return None

    relation = (child_row.relation or "").strip()
    return f"{name} ({relation})" if relation else name


def _pick_primary_phone(child_row: frappe._dict, guardian_doc: frappe._dict | None) -> str | None:
    candidates = [
        child_row.phone,
        guardian_doc.guardian_mobile_phone if guardian_doc else None,
        guardian_doc.guardian_work_phone if guardian_doc else None,
    ]
    for raw in candidates:
        normalized = (raw or "").strip()
        if normalized:
            return normalized
    return None


def _unique_sequence(values: list[str | None]) -> list[str]:
    seen = set()
    result = []
    for val in values:
        normalized = (val or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _render_medical_summary(patient: frappe._dict | None) -> str:
    if not patient:
        return ""

    lines = []
    for df in _medical_field_defs():
        raw_value = patient.get(df["fieldname"])
        rendered = _format_field_value(raw_value, df["fieldtype"])
        if not rendered:
            continue
        label = escape_html(df["label"])
        lines.append(f"<div class='med-line'><span class='med-label'>{label}:</span> {rendered}</div>")

    return "".join(lines)


@lru_cache(maxsize=1)
def _medical_field_defs() -> list[dict]:
    meta = frappe.get_meta("Student Patient")
    allowed_types = {"Data", "Select", "Small Text", "Long Text", "Text", "Text Editor", "Check"}
    excluded_fields = {
        "student",
        "student_name",
        "preferred_name",
        "status",
        "completion_state",
        "student_info",
        "photo",
        "medical_info_section",
        "note_to_staff_section",
        "section_break_7",
        "section_break_14",
        "section_break_g004",
        "others_section",
        "diet_data_section",
        "medical_history_section",
        "vaccination_data_section",
        "column_break_3",
        "column_break_11",
        "column_break_20",
        "column_break_27",
        "column_break_xbbr",
        "section_break_gg04",
        "student_age",
    }

    field_defs = []
    for df in meta.fields:
        if df.fieldtype not in allowed_types:
            continue
        if df.fieldname in excluded_fields:
            continue
        field_defs.append(
            {
                "fieldname": df.fieldname,
                "label": df.label or df.fieldname.replace("_", " ").title(),
                "fieldtype": df.fieldtype,
                "idx": df.idx or 0,
            }
        )

    field_defs.sort(key=lambda d: d["idx"])
    return field_defs


def _format_field_value(value, fieldtype: str) -> str:
    if value in (None, "", 0, "0"):
        return ""

    if fieldtype == "Check":
        return escape_html(_("Yes")) if cint(value) else ""

    text = cstr(value).strip()
    if not text:
        return ""

    if fieldtype == "Text Editor":
        text = strip_html_tags(text)

    text = escape_html(text).replace("\n", "<br>")
    return text


def _format_age(dob) -> str:
    if not dob:
        return ""
    birthdate = getdate(dob)
    today_date = getdate(today())
    if birthdate > today_date:
        return ""
    delta = relativedelta(today_date, birthdate)
    parts = []
    if delta.years:
        parts.append(f"{delta.years}y")
    if delta.months:
        parts.append(f"{delta.months}m")
    if not parts and delta.days:
        parts.append(f"{delta.days}d")
    return " ".join(parts)
