# ifitwala_ed/admission/api/recommendation_intake/templates.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.admission_utils import (
    ensure_admissions_permission,
    get_applicant_scope_ancestors,
    is_applicant_document_type_in_scope,
)
from ifitwala_ed.admission.api.recommendation_intake.access import _feature_ready, _require_feature_ready
from ifitwala_ed.admission.api.recommendation_intake.constants import (
    RECOMMENDATION_TEMPLATE_DOCTYPE,
    RECOMMENDATION_TEMPLATE_FIELD_DOCTYPE,
)
from ifitwala_ed.admission.api.recommendation_intake.dto import (
    _parse_template_field_options,
)


def _template_snapshot(template_name: str) -> dict:
    template = frappe.db.get_value(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        template_name,
        [
            "name",
            "template_name",
            "allow_file_upload",
            "file_upload_required",
            "otp_enforced",
            "minimum_required",
            "maximum_allowed",
            "applicant_can_view_status",
            "target_document_type",
        ],
        as_dict=True,
    )
    if not template:
        frappe.throw(_("Recommendation Template no longer exists."))

    rows = frappe.get_all(
        RECOMMENDATION_TEMPLATE_FIELD_DOCTYPE,
        filters={"parenttype": RECOMMENDATION_TEMPLATE_DOCTYPE, "parent": template_name},
        fields=["field_key", "label", "field_type", "is_required", "options_json", "help_text", "idx"],
        order_by="idx asc",
    )

    fields = []
    for row in rows:
        field_key = frappe.scrub((row.get("field_key") or "").strip())[:80]
        if not field_key:
            continue
        field_type = (row.get("field_type") or "Data").strip()
        fields.append(
            {
                "field_key": field_key,
                "label": (row.get("label") or "").strip() or field_key,
                "field_type": field_type,
                "is_required": bool(cint(row.get("is_required"))),
                "options": _parse_template_field_options(
                    field_type=field_type,
                    options_json=row.get("options_json"),
                ),
                "help_text": (row.get("help_text") or "").strip(),
            }
        )

    return {
        "template": {
            "name": template.get("name"),
            "template_name": (template.get("template_name") or "").strip() or template.get("name"),
            "allow_file_upload": bool(cint(template.get("allow_file_upload"))),
            "file_upload_required": bool(cint(template.get("file_upload_required"))),
            "otp_enforced": bool(cint(template.get("otp_enforced"))),
            "minimum_required": max(0, cint(template.get("minimum_required") or 0)),
            "maximum_allowed": max(1, cint(template.get("maximum_allowed") or 1)),
            "applicant_can_view_status": bool(cint(template.get("applicant_can_view_status"))),
            "target_document_type": (template.get("target_document_type") or "").strip(),
        },
        "fields": fields,
    }


def _request_scope_ancestors(student_applicant: str) -> tuple[dict, set[str], set[str]]:
    applicant_row = frappe.db.get_value(
        "Student Applicant",
        student_applicant,
        ["name", "organization", "school", "application_status"],
        as_dict=True,
    )
    if not applicant_row:
        frappe.throw(_("Invalid Student Applicant: {student_applicant}.").format(student_applicant=student_applicant))

    org_scope, school_scope = get_applicant_scope_ancestors(
        organization=applicant_row.get("organization"),
        school=applicant_row.get("school"),
    )
    return applicant_row, set(org_scope), set(school_scope)


def _template_in_scope(*, template_row: dict, org_scope: set[str], school_scope: set[str]) -> bool:
    template_org = (template_row.get("organization") or "").strip()
    template_school = (template_row.get("school") or "").strip()
    if template_org and template_org not in org_scope:
        return False
    if template_school and template_school not in school_scope:
        return False
    return True


def _ensure_template_scope_for_applicant(*, student_applicant: str, template_name: str) -> tuple[dict, dict]:
    applicant_row, org_scope, school_scope = _request_scope_ancestors(student_applicant)
    template_row = frappe.db.get_value(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        template_name,
        [
            "name",
            "is_active",
            "organization",
            "school",
            "target_document_type",
            "minimum_required",
            "maximum_allowed",
            "allow_file_upload",
            "file_upload_required",
            "otp_enforced",
            "applicant_can_view_status",
        ],
        as_dict=True,
    )
    if not template_row:
        frappe.throw(_("Invalid Recommendation Template: {template_name}.").format(template_name=template_name))
    if not cint(template_row.get("is_active")):
        frappe.throw(_("Recommendation Template is inactive."))
    if not _template_in_scope(template_row=template_row, org_scope=org_scope, school_scope=school_scope):
        frappe.throw(_("Recommendation Template is outside the Applicant scope."))

    target_document_type = (template_row.get("target_document_type") or "").strip()
    if not target_document_type:
        frappe.throw(_("Recommendation Template target document type is required."))
    target_row = frappe.db.get_value(
        "Applicant Document Type",
        target_document_type,
        ["name", "is_active", "organization", "school", "is_repeatable"],
        as_dict=True,
    )
    if not target_row:
        frappe.throw(_("Recommendation target document type no longer exists."))
    if not cint(target_row.get("is_active")):
        frappe.throw(_("Recommendation target document type must be active."))
    if not is_applicant_document_type_in_scope(
        document_type_organization=target_row.get("organization"),
        document_type_school=target_row.get("school"),
        applicant_org_ancestors=org_scope,
        applicant_school_ancestors=school_scope,
    ):
        frappe.throw(_("Recommendation target document type is outside the Applicant scope."))

    max_allowed = max(1, cint(template_row.get("maximum_allowed") or 1))
    if max_allowed > 1 and not cint(target_row.get("is_repeatable")):
        frappe.throw(_("Recommendation target document type must be repeatable for multiple letters."))

    return applicant_row, template_row


def get_recommendation_template_rows_for_applicant(
    *,
    student_applicant: str,
    include_confidential: bool = False,
    fields: list[str] | tuple[str, ...] | None = None,
) -> list[dict]:
    if not _feature_ready():
        return []

    student_applicant = (student_applicant or "").strip()
    if not student_applicant:
        return []

    request_scope = _request_scope_ancestors(student_applicant)
    org_scope = request_scope[1]
    school_scope = request_scope[2]

    required_fields = ["name", "organization", "school"]
    if not include_confidential:
        required_fields.append("applicant_can_view_status")
    query_fields = list(dict.fromkeys(required_fields + list(fields or [])))

    rows = frappe.get_all(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        filters={"is_active": 1},
        fields=query_fields,
    )

    template_rows = []
    for row in rows:
        if not _template_in_scope(template_row=row, org_scope=org_scope, school_scope=school_scope):
            continue
        if not include_confidential and not cint(row.get("applicant_can_view_status")):
            continue
        template_rows.append(row)
    return template_rows


def _parse_snapshot(snapshot_json: str | None, template_name: str) -> dict:
    if snapshot_json:
        try:
            parsed = frappe.parse_json(snapshot_json)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return _template_snapshot(template_name)


def list_recommendation_templates(*, student_applicant: str | None = None):
    ensure_admissions_permission()
    _require_feature_ready()

    student_applicant = (student_applicant or "").strip()
    if not student_applicant:
        frappe.throw(_("student_applicant is required."))

    applicant_row, org_scope, school_scope = _request_scope_ancestors(student_applicant)
    rows = frappe.get_all(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        filters={"is_active": 1},
        fields=[
            "name",
            "template_name",
            "organization",
            "school",
            "minimum_required",
            "maximum_allowed",
            "allow_file_upload",
            "file_upload_required",
            "otp_enforced",
            "applicant_can_view_status",
            "target_document_type",
        ],
        order_by="template_name asc",
    )

    payload = []
    for row in rows:
        if not _template_in_scope(template_row=row, org_scope=org_scope, school_scope=school_scope):
            continue
        payload.append(
            {
                "name": row.get("name"),
                "template_name": row.get("template_name") or row.get("name"),
                "minimum_required": max(0, cint(row.get("minimum_required") or 0)),
                "maximum_allowed": max(1, cint(row.get("maximum_allowed") or 1)),
                "allow_file_upload": bool(cint(row.get("allow_file_upload"))),
                "file_upload_required": bool(cint(row.get("file_upload_required"))),
                "otp_enforced": bool(cint(row.get("otp_enforced"))),
                "applicant_can_view_status": bool(cint(row.get("applicant_can_view_status"))),
                "target_document_type": row.get("target_document_type"),
                "organization": applicant_row.get("organization"),
                "school": applicant_row.get("school"),
            }
        )

    return {"templates": payload}
