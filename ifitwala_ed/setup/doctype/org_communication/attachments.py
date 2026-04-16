from __future__ import annotations

import re
from typing import Any

import frappe
from frappe import _

ORG_COMMUNICATION_ATTACHMENT_BINDING_ROLE = "communication_attachment"
ORG_COMMUNICATION_ATTACHMENT_DATA_CLASS = "administrative"
ORG_COMMUNICATION_ATTACHMENT_PURPOSE = "administrative"
ORG_COMMUNICATION_ATTACHMENT_RETENTION_POLICY = "fixed_7y"
ORG_COMMUNICATION_ATTACHMENT_SLOT_PREFIX = "communication_attachment__"
ORG_COMMUNICATION_ATTACHMENT_CLASS_CATEGORY = "Class Communication Attachment"
ORG_COMMUNICATION_ATTACHMENT_SCHOOL_CATEGORY = "School Communication Attachment"
ORG_COMMUNICATION_ATTACHMENT_ORGANIZATION_CATEGORY = "Organization Communication Attachment"


def _field_value(source, fieldname: str):
    getter = getattr(source, "get", None)
    if callable(getter):
        return getter(fieldname)
    return getattr(source, fieldname, None)


def _normalize_row_key(value: str | None) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip()).strip("-_")
    if normalized:
        return normalized
    return frappe.generate_hash(length=10)


def parse_org_communication_attachment_row_key(slot: str | None) -> str | None:
    resolved_slot = str(slot or "").strip()
    if not resolved_slot.startswith(ORG_COMMUNICATION_ATTACHMENT_SLOT_PREFIX):
        return None
    row_key = resolved_slot.split(ORG_COMMUNICATION_ATTACHMENT_SLOT_PREFIX, 1)[1].strip()
    return row_key or None


def _clean_link_value(value: str | None) -> str | None:
    resolved = str(value or "").strip()
    return resolved or None


def _get_doc(name: str, *, permission_type: str | None = None):
    if not frappe.db.exists("Org Communication", name):
        frappe.throw(_("Org Communication does not exist: {0}").format(name))

    doc = frappe.get_doc("Org Communication", name)
    if permission_type:
        doc.check_permission(permission_type)
    return doc


def assert_org_communication_attachment_upload_access(
    org_communication: str,
    *,
    permission_type: str = "write",
):
    return _get_doc(org_communication, permission_type=permission_type)


def _resolve_student_group_for_attachments(doc) -> str | None:
    activity_student_group = _clean_link_value(_field_value(doc, "activity_student_group"))
    if activity_student_group:
        return activity_student_group

    for row in _field_value(doc, "audiences") or []:
        if str(_field_value(row, "target_mode") or "").strip() != "Student Group":
            continue
        student_group = _clean_link_value(_field_value(row, "student_group"))
        if student_group:
            return student_group

    return None


def _get_unique_audience_link_value(doc, *, target_mode: str, fieldname: str) -> str | None:
    values: list[str] = []
    for row in _field_value(doc, "audiences") or []:
        if str(_field_value(row, "target_mode") or "").strip() != target_mode:
            continue
        value = _clean_link_value(_field_value(row, fieldname))
        if value and value not in values:
            values.append(value)
    if len(values) == 1:
        return values[0]
    return None


def _resolve_team_attachment_context(doc) -> dict[str, str | None]:
    team = _get_unique_audience_link_value(doc, target_mode="Team", fieldname="team")
    if not team:
        return {"team": None, "school": None, "organization": None}

    team_row = frappe.db.get_value(
        "Team",
        team,
        ["school", "organization"],
        as_dict=True,
    )
    if not team_row:
        frappe.throw(_("Selected Team does not exist: {0}").format(team))

    return {
        "team": team,
        "school": _clean_link_value(team_row.get("school")),
        "organization": _clean_link_value(team_row.get("organization")),
    }


def resolve_org_communication_attachment_context(doc) -> dict[str, str | None]:
    student_group = _resolve_student_group_for_attachments(doc)
    if student_group:
        student_group_row = frappe.db.get_value(
            "Student Group",
            student_group,
            ["course", "school"],
            as_dict=True,
        )
        if not student_group_row:
            course = frappe.db.get_value("Student Group", student_group, "course")
            school = frappe.db.get_value("Student Group", student_group, "school")
            if course or school:
                student_group_row = {"course": course, "school": school}
        if not student_group_row:
            frappe.throw(_("Student Group does not exist: {0}").format(student_group))

        course = _clean_link_value(student_group_row.get("course"))
        if not course:
            frappe.throw(_("Student Group is missing its authoritative Course context."))

        school = _clean_link_value(student_group_row.get("school")) or _clean_link_value(_field_value(doc, "school"))
        if not school:
            frappe.throw(_("Org Communication attachments require an issuing school."))

        organization = _clean_link_value(_field_value(doc, "organization"))
        if not organization:
            organization = _clean_link_value(frappe.db.get_value("School", school, "organization"))
        if not organization:
            frappe.throw(_("Org Communication attachments require an organization."))

        return {
            "context_kind": "student_group",
            "organization": organization,
            "school": school,
            "course": course,
            "student_group": student_group,
        }

    team_context = _resolve_team_attachment_context(doc)
    school = (
        _clean_link_value(_field_value(doc, "school"))
        or _get_unique_audience_link_value(doc, target_mode="School Scope", fieldname="school")
        or team_context.get("school")
    )
    organization = _clean_link_value(_field_value(doc, "organization")) or team_context.get("organization")
    if not organization and school:
        organization = _clean_link_value(frappe.db.get_value("School", school, "organization"))
    if not organization:
        frappe.throw(_("Org Communication attachments require an organization."))

    return {
        "context_kind": "school" if school else "organization",
        "organization": organization,
        "school": school,
        "course": None,
        "student_group": None,
    }


def _assert_attachment_row_exists(doc, row_key: str) -> None:
    if not row_key:
        frappe.throw(_("Org Communication attachment row key is required."))
    for row in doc.get("attachments") or []:
        if str(getattr(row, "name", "") or "").strip() == row_key:
            return
    frappe.throw(_("Org Communication attachment row was not found: {0}.").format(row_key))


def build_org_communication_attachment_upload_contract(
    doc,
    *,
    row_name: str | None = None,
    require_existing_row: bool = False,
) -> dict[str, Any]:
    if getattr(doc, "is_new", lambda: False)():
        frappe.throw(_("Save the Org Communication before attaching governed files."))

    context = resolve_org_communication_attachment_context(doc)
    row_key = _normalize_row_key(row_name)
    if row_name and require_existing_row:
        _assert_attachment_row_exists(doc, row_key)

    return {
        "owner_doctype": "Org Communication",
        "owner_name": doc.name,
        "attached_doctype": "Org Communication",
        "attached_name": doc.name,
        "organization": context["organization"],
        "school": context["school"],
        "primary_subject_type": "Organization",
        "primary_subject_id": context["organization"],
        "data_class": ORG_COMMUNICATION_ATTACHMENT_DATA_CLASS,
        "purpose": ORG_COMMUNICATION_ATTACHMENT_PURPOSE,
        "retention_policy": ORG_COMMUNICATION_ATTACHMENT_RETENTION_POLICY,
        "slot": f"{ORG_COMMUNICATION_ATTACHMENT_SLOT_PREFIX}{row_key}",
        "row_name": row_key,
        "course": context["course"],
        "student_group": context["student_group"],
    }


def validate_org_communication_attachment_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != "Org Communication":
        return None

    row_key = parse_org_communication_attachment_row_key(getattr(upload_session_doc, "intended_slot", None))
    if not row_key:
        frappe.throw(_("Org Communication upload sessions require a communication-attachment slot."))

    doc = assert_org_communication_attachment_upload_access(upload_session_doc.owner_name, permission_type="write")
    authoritative = build_org_communication_attachment_upload_contract(
        doc,
        row_name=row_key,
        require_existing_row=False,
    )

    field_map = {
        "owner_doctype": "owner_doctype",
        "owner_name": "owner_name",
        "attached_doctype": "attached_doctype",
        "attached_name": "attached_name",
        "organization": "organization",
        "school": "school",
        "intended_primary_subject_type": "primary_subject_type",
        "intended_primary_subject_id": "primary_subject_id",
        "intended_data_class": "data_class",
        "intended_purpose": "purpose",
        "intended_retention_policy": "retention_policy",
        "intended_slot": "slot",
    }

    for session_field, authoritative_field in field_map.items():
        if getattr(upload_session_doc, session_field, None) != authoritative[authoritative_field]:
            frappe.throw(
                _(
                    "Upload session no longer matches the authoritative Org Communication attachment context for field '{0}'."
                ).format(session_field)
            )

    return authoritative


def get_org_communication_context_override(owner_name: str | None, slot: str | None) -> dict[str, Any] | None:
    if not owner_name or not frappe.db.exists("Org Communication", owner_name):
        return None

    doc = _get_doc(owner_name)
    context = resolve_org_communication_attachment_context(doc)
    if context["context_kind"] == "student_group":
        return {
            "root_folder": "Home/Courses",
            "subfolder": (f"{context['course']}/Communications/{context['student_group']}/{doc.name}/Attachments"),
            "file_category": ORG_COMMUNICATION_ATTACHMENT_CLASS_CATEGORY,
            "logical_key": str(slot or "").strip() or f"org_communication_attachment_{doc.name}",
        }

    if context["school"]:
        return {
            "root_folder": "Home/Organizations",
            "subfolder": f"{context['organization']}/Schools/{context['school']}/Communications/{doc.name}/Attachments",
            "file_category": ORG_COMMUNICATION_ATTACHMENT_SCHOOL_CATEGORY,
            "logical_key": str(slot or "").strip() or f"org_communication_attachment_{doc.name}",
        }

    return {
        "root_folder": "Home/Organizations",
        "subfolder": f"{context['organization']}/Communications/{doc.name}/Attachments",
        "file_category": ORG_COMMUNICATION_ATTACHMENT_ORGANIZATION_CATEGORY,
        "logical_key": str(slot or "").strip() or f"org_communication_attachment_{doc.name}",
    }


def run_org_communication_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Org Communication":
        return {}

    row_key = parse_org_communication_attachment_row_key(getattr(upload_session_doc, "intended_slot", None))
    if not row_key:
        return {}

    doc = frappe.get_doc("Org Communication", upload_session_doc.owner_name)
    target_row = None
    for row in doc.get("attachments") or []:
        if str(getattr(row, "name", "") or "").strip() == row_key:
            target_row = row
            break

    if not target_row:
        target_row = doc.append("attachments", {})
        target_row.name = row_key

    file_url = getattr(created_file, "file_url", None) or frappe.db.get_value("File", created_file.name, "file_url")
    file_name = getattr(created_file, "file_name", None) or frappe.db.get_value("File", created_file.name, "file_name")
    file_size = getattr(created_file, "file_size", None) or frappe.db.get_value("File", created_file.name, "file_size")

    if not getattr(target_row, "section_break_sbex", None):
        target_row.section_break_sbex = file_name
    target_row.file = file_url
    target_row.file_name = file_name
    target_row.file_size = file_size
    target_row.external_url = None
    target_row.public = 0
    doc.save(ignore_permissions=True)

    return {
        "row_name": row_key,
        "file_url": file_url,
    }
