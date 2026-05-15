from __future__ import annotations

import hashlib
from typing import Any

import frappe
from frappe import _

STUDENT_REFERRAL_ATTACHMENT_BINDING_ROLE = "student_referral_attachment"
STUDENT_REFERRAL_ATTACHMENT_DATA_CLASS = "safeguarding"
STUDENT_REFERRAL_ATTACHMENT_PURPOSE = "safeguarding_evidence"
STUDENT_REFERRAL_ATTACHMENT_RETENTION_POLICY = "fixed_7y"
STUDENT_REFERRAL_ATTACHMENT_SLOT_PREFIX = "student_referral_attachment__"
STUDENT_REFERRAL_ATTACHMENT_CATEGORY = "Student Referral Attachment"
STUDENT_REFERRAL_DOCTYPE = "Student Referral"


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _linked_student_for(user: str) -> str | None:
    return _clean_text(frappe.db.get_value("Student", {"student_email": user}, "name"))


def _get_referral_doc(referral: str):
    referral_name = _clean_text(referral)
    if not referral_name:
        frappe.throw(_("Student Referral is required."))
    if not frappe.db.exists(STUDENT_REFERRAL_DOCTYPE, referral_name):
        frappe.throw(
            _("Student Referral does not exist: {referral}").format(referral=referral_name),
            frappe.DoesNotExistError,
        )
    return frappe.get_doc(STUDENT_REFERRAL_DOCTYPE, referral_name)


def _is_current_student_self_referral(doc, user: str) -> bool:
    if _clean_text(getattr(doc, "referral_source", None)) != "Student (Self)":
        return False
    if _clean_text(getattr(doc, "owner", None)) != user and _clean_text(getattr(doc, "referrer", None)) != user:
        return False
    return _linked_student_for(user) == _clean_text(getattr(doc, "student", None))


def assert_self_referral_attachment_upload_access(referral: str):
    user = _clean_text(getattr(frappe.session, "user", None))
    if not user or user == "Guest":
        frappe.throw(_("You must be signed in to attach files to a self-referral."), frappe.PermissionError)
    if "Student" not in set(frappe.get_roles(user) or []):
        frappe.throw(_("Only logged-in students can attach files to a self-referral."), frappe.PermissionError)

    doc = _get_referral_doc(referral)
    if getattr(doc, "docstatus", 0) == 2:
        frappe.throw(_("Cancelled Student Referrals cannot accept attachments."))
    if not _is_current_student_self_referral(doc, user):
        frappe.throw(_("You cannot attach files to this referral."), frappe.PermissionError)
    return doc


def build_student_referral_attachment_slot(*, referral_name: str, filename: str, content: bytes) -> str:
    content_hash = hashlib.sha256(content or b"").hexdigest()
    seed = "|".join(
        [
            _clean_text(referral_name) or "",
            _clean_text(filename) or "upload.bin",
            content_hash,
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"{STUDENT_REFERRAL_ATTACHMENT_SLOT_PREFIX}{digest}"


def parse_student_referral_attachment_slot(slot: str | None) -> str | None:
    resolved_slot = str(slot or "").strip().lower()
    if not resolved_slot.startswith(STUDENT_REFERRAL_ATTACHMENT_SLOT_PREFIX):
        return None
    row_key = resolved_slot.split(STUDENT_REFERRAL_ATTACHMENT_SLOT_PREFIX, 1)[1].strip()
    return row_key or None


def build_student_referral_attachment_upload_contract(doc, *, slot: str | None = None) -> dict[str, Any]:
    if getattr(doc, "is_new", lambda: False)():
        frappe.throw(_("Save the Student Referral before attaching governed files."))

    student = _clean_text(getattr(doc, "student", None))
    school = _clean_text(getattr(doc, "school", None))
    if not student:
        frappe.throw(_("Student Referral attachments require a student."))
    if not school:
        frappe.throw(_("Student Referral attachments require a school."))

    organization = _clean_text(frappe.db.get_value("School", school, "organization"))
    if not organization:
        frappe.throw(_("Student Referral attachments require an organization."))

    resolved_slot = str(slot or "").strip().lower()
    if not parse_student_referral_attachment_slot(resolved_slot):
        frappe.throw(_("Student Referral attachment uploads require a referral attachment slot."))

    return {
        "owner_doctype": STUDENT_REFERRAL_DOCTYPE,
        "owner_name": doc.name,
        "attached_doctype": STUDENT_REFERRAL_DOCTYPE,
        "attached_name": doc.name,
        "organization": organization,
        "school": school,
        "primary_subject_type": "Student",
        "primary_subject_id": student,
        "data_class": STUDENT_REFERRAL_ATTACHMENT_DATA_CLASS,
        "purpose": STUDENT_REFERRAL_ATTACHMENT_PURPOSE,
        "retention_policy": STUDENT_REFERRAL_ATTACHMENT_RETENTION_POLICY,
        "slot": resolved_slot,
    }


def validate_student_referral_attachment_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != STUDENT_REFERRAL_DOCTYPE:
        return None

    slot = str(getattr(upload_session_doc, "intended_slot", None) or "").strip()
    if not parse_student_referral_attachment_slot(slot):
        frappe.throw(_("Student Referral upload sessions require a referral attachment slot."))

    doc = assert_self_referral_attachment_upload_access(upload_session_doc.owner_name)
    authoritative = build_student_referral_attachment_upload_contract(doc, slot=slot)
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
                    "Upload session no longer matches the authoritative Student Referral attachment context for field '{fieldname}'."
                ).format(fieldname=session_field)
            )

    return authoritative


def get_student_referral_attachment_context_override(
    owner_name: str | None,
    slot: str | None,
) -> dict[str, Any] | None:
    if not owner_name or not frappe.db.exists(STUDENT_REFERRAL_DOCTYPE, owner_name):
        return None
    if not parse_student_referral_attachment_slot(slot):
        return None

    doc = _get_referral_doc(owner_name)
    student = _clean_text(getattr(doc, "student", None))
    if not student:
        return None

    return {
        "root_folder": "Home/Students",
        "subfolder": f"{student}/Student Referrals/{doc.name}/Attachments",
        "file_category": STUDENT_REFERRAL_ATTACHMENT_CATEGORY,
        "logical_key": str(slot or "").strip(),
    }


def run_student_referral_attachment_post_finalize(upload_session_doc, _created_file) -> dict[str, Any]:
    if getattr(upload_session_doc, "owner_doctype", None) != STUDENT_REFERRAL_DOCTYPE:
        return {}
    return {
        "student_referral": getattr(upload_session_doc, "owner_name", None),
        "slot": getattr(upload_session_doc, "intended_slot", None),
    }
