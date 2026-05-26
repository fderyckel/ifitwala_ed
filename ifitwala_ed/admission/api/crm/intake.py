# ifitwala_ed/admission/api/crm/intake.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import assign_inquiry
from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import ensure_admissions_crm_permission
from ifitwala_ed.admission.api.crm.guards import (
    _assert_scope_allowed,
    _require_conversation_write,
    _validate_crm_assignee,
)
from ifitwala_ed.admission.api.crm.idempotency import _run_idempotent
from ifitwala_ed.admission.api.crm.summaries import _activity_summary, _conversation_summary, _inquiry_summary


def _valid_inquiry_option(fieldname: str, value: str | None) -> str | None:
    text = clean(value)
    if not text:
        return None
    field = frappe.get_meta("Inquiry").get_field(fieldname)
    options = {clean(option) for option in (field.options or "").splitlines() if clean(option)}
    if text not in options:
        frappe.throw(_("Invalid Inquiry {field}: {value}.").format(field=field.label or fieldname, value=text))
    return text


def _valid_activity_option(fieldname: str, value: str | None) -> str | None:
    text = clean(value)
    if not text:
        return None
    field = frappe.get_meta("Admission CRM Activity").get_field(fieldname)
    options = {clean(option) for option in (field.options or "").splitlines() if clean(option)}
    if text not in options:
        frappe.throw(
            _("Invalid Admission CRM Activity {field}: {value}.").format(
                field=field.label or fieldname,
                value=text,
            )
        )
    return text


def _source_from_channel(channel_type: str | None) -> str:
    channel = clean(channel_type)
    if channel == "WhatsApp":
        return "WhatsApp"
    if channel == "Line":
        return "Line"
    if channel in {"Facebook Messenger", "Instagram DM"}:
        return "Facebook"
    return "Other"


def _name_parts(display_name: str | None, fallback: str | None) -> tuple[str | None, str | None]:
    text = clean(display_name) or clean(fallback)
    if not text:
        return None, None
    parts = text.split()
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _append_if_clean(payload: dict, fieldname: str, value: str | None) -> None:
    text = clean(value)
    if text:
        payload[fieldname] = text


def _inquiry_payload_for_intake(
    *,
    organization: str,
    school: str | None,
    type_of_inquiry: str,
    source: str,
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    phone_number: str | None,
    student_first_name: str | None,
    student_last_name: str | None,
    intended_academic_year: str | None,
    grade_level_interest: str | None,
    program_interest: str | None,
    student_name_or_id: str | None,
    relationship_to_student: str | None,
    organization_name: str | None,
    partnership_context: str | None,
    message: str | None,
) -> dict:
    payload = {
        "doctype": "Inquiry",
        "type_of_inquiry": type_of_inquiry,
        "source": source,
        "organization": organization,
    }
    _append_if_clean(payload, "school", school)
    _append_if_clean(payload, "first_name", first_name)
    _append_if_clean(payload, "last_name", last_name)
    _append_if_clean(payload, "email", email)
    _append_if_clean(payload, "phone_number", phone_number)
    _append_if_clean(payload, "message", message)

    if type_of_inquiry == "Admission":
        _append_if_clean(payload, "student_first_name", student_first_name)
        _append_if_clean(payload, "student_last_name", student_last_name)
        _append_if_clean(payload, "intended_academic_year", intended_academic_year)
        _append_if_clean(payload, "grade_level_interest", grade_level_interest)
        _append_if_clean(payload, "program_interest", program_interest)
    elif type_of_inquiry == "Current Family":
        _append_if_clean(payload, "student_name_or_id", student_name_or_id)
        _append_if_clean(payload, "relationship_to_student", relationship_to_student)
    elif type_of_inquiry == "Partnership / Agent":
        _append_if_clean(payload, "organization_name", organization_name)
        _append_if_clean(payload, "partnership_context", partnership_context)

    return payload


def create_admissions_intake_impl(
    *,
    organization: str | None = None,
    school: str | None = None,
    type_of_inquiry: str | None = None,
    source: str | None = None,
    activity_channel: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone_number: str | None = None,
    student_first_name: str | None = None,
    student_last_name: str | None = None,
    intended_academic_year: str | None = None,
    grade_level_interest: str | None = None,
    program_interest: str | None = None,
    student_name_or_id: str | None = None,
    relationship_to_student: str | None = None,
    organization_name: str | None = None,
    partnership_context: str | None = None,
    message: str | None = None,
    activity_type: str | None = None,
    outcome: str | None = None,
    note: str | None = None,
    next_action_on: str | None = None,
    assigned_to: str | None = None,
    assignment_lane: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    scope_organization = clean(organization)
    school_name = clean(school)
    if not scope_organization:
        frappe.throw(_("Organization is required."))

    type_value = _valid_inquiry_option("type_of_inquiry", type_of_inquiry)
    source_value = _valid_inquiry_option("source", source)
    activity_type_value = _valid_activity_option("activity_type", activity_type)
    activity_channel_value = _valid_activity_option("activity_channel", activity_channel)
    if not type_value:
        frappe.throw(_("Type of Inquiry is required."))
    if not source_value:
        frappe.throw(_("Source is required."))
    if not activity_type_value:
        frappe.throw(_("Activity Type is required."))
    if not activity_channel_value:
        frappe.throw(_("Activity Channel is required."))

    if not any(
        clean(value)
        for value in (
            first_name,
            last_name,
            email,
            phone_number,
            organization_name,
            message,
            note,
        )
    ):
        frappe.throw(_("At least one contact detail, organization name, message, or intake note is required."))

    _assert_scope_allowed(user, organization=scope_organization, school=school_name)
    assignee = clean(assigned_to)
    if assignee:
        _validate_crm_assignee(user=user, assigned_to=assignee, organization=scope_organization, school=school_name)

    def action():
        inquiry_doc = frappe.get_doc(
            _inquiry_payload_for_intake(
                organization=scope_organization,
                school=school_name,
                type_of_inquiry=type_value,
                source=source_value,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                student_first_name=student_first_name,
                student_last_name=student_last_name,
                intended_academic_year=intended_academic_year,
                grade_level_interest=grade_level_interest,
                program_interest=program_interest,
                student_name_or_id=student_name_or_id,
                relationship_to_student=relationship_to_student,
                organization_name=organization_name,
                partnership_context=partnership_context,
                message=message,
            )
        )
        inquiry_doc.insert(ignore_permissions=True)

        conversation_doc = frappe.get_doc(
            {
                "doctype": "Admission Conversation",
                "inquiry": inquiry_doc.name,
            }
        )
        conversation_doc.insert(ignore_permissions=True)

        activity_doc = frappe.get_doc(
            {
                "doctype": "Admission CRM Activity",
                "conversation": conversation_doc.name,
                "activity_type": activity_type_value,
                "activity_channel": activity_channel_value,
                "outcome": clean(outcome),
                "note": clean(note),
                "next_action_on": clean(next_action_on),
            }
        )
        activity_doc.insert(ignore_permissions=True)

        assignment_result = None
        if assignee:
            conversation_doc.reload()
            conversation_doc.assigned_to = assignee
            conversation_doc.save(ignore_permissions=True)
            assignment_result = assign_inquiry(
                "Inquiry",
                inquiry_doc.name,
                assignee,
                assignment_lane=assignment_lane,
            )

        return {
            "ok": True,
            "inquiry": _inquiry_summary(inquiry_doc.name),
            "conversation": _conversation_summary(conversation_doc.name),
            "activity": _activity_summary(activity_doc.name),
            "assignment": assignment_result,
        }

    return _run_idempotent(
        user=user,
        action="create_admissions_intake",
        target=scope_organization,
        client_request_id=client_request_id,
        fn=action,
    )


def create_inquiry_from_admission_conversation_impl(
    *,
    conversation: str | None = None,
    type_of_inquiry: str | None = None,
    source: str | None = None,
    message: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    conversation_name = clean(conversation)
    if not conversation_name:
        frappe.throw(_("Admission Conversation is required."))

    def action():
        conversation_doc = _require_conversation_write(user, conversation_name)
        existing_inquiry = clean(conversation_doc.inquiry)
        if existing_inquiry:
            return {
                "ok": True,
                "changed": False,
                "conversation": _conversation_summary(conversation_doc.name),
                "inquiry": _inquiry_summary(existing_inquiry),
            }

        _assert_scope_allowed(user, organization=conversation_doc.organization, school=conversation_doc.school)
        identity = {}
        if clean(conversation_doc.external_identity):
            identity = (
                frappe.db.get_value(
                    "Admission External Identity",
                    conversation_doc.external_identity,
                    ["display_name", "email", "phone_number", "channel_type"],
                    as_dict=True,
                )
                or {}
            )

        first_name, last_name = _name_parts(identity.get("display_name"), conversation_doc.title)
        source_value = _valid_inquiry_option("source", source) or _source_from_channel(identity.get("channel_type"))
        type_value = _valid_inquiry_option("type_of_inquiry", type_of_inquiry) or "Admission"

        inquiry_doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": first_name,
                "last_name": last_name,
                "email": clean(identity.get("email")),
                "phone_number": clean(identity.get("phone_number")),
                "type_of_inquiry": type_value,
                "source": source_value,
                "organization": conversation_doc.organization,
                "school": conversation_doc.school,
                "message": clean(message) or clean(conversation_doc.last_message_preview),
            }
        )
        inquiry_doc.insert(ignore_permissions=True)

        conversation_doc.inquiry = inquiry_doc.name
        conversation_doc.save(ignore_permissions=True)
        conversation_doc.add_comment(
            "Comment",
            text=_("Inquiry {inquiry} created from this admissions conversation.").format(
                inquiry=frappe.bold(inquiry_doc.name)
            ),
        )
        return {
            "ok": True,
            "changed": True,
            "conversation": _conversation_summary(conversation_doc.name),
            "inquiry": _inquiry_summary(inquiry_doc.name),
        }

    return _run_idempotent(
        user=user,
        action="create_inquiry_from_conversation",
        target=conversation_name,
        client_request_id=client_request_id,
        fn=action,
    )
