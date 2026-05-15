from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.admission.admission_utils import _school_belongs_to_organization_scope


def clean(value: str | None) -> str:
    return (value or "").strip()


def get_school_organization(school: str | None) -> str:
    school_name = clean(school)
    if not school_name:
        return ""
    return clean(frappe.db.get_value("School", school_name, "organization"))


def assert_school_in_organization_scope(*, school: str | None, organization: str | None) -> None:
    school_name = clean(school)
    organization_name = clean(organization)
    if not school_name:
        return
    if not organization_name:
        frappe.throw(_("Organization is required when School is set."))
    if not _school_belongs_to_organization_scope(school_name, organization_name):
        frappe.throw(_("Selected School does not belong to the selected Organization."))


def get_inquiry_context(inquiry: str | None) -> dict:
    inquiry_name = clean(inquiry)
    if not inquiry_name:
        return {}
    row = frappe.db.get_value(
        "Inquiry",
        inquiry_name,
        ["name", "organization", "school", "first_name", "last_name", "email", "phone_number", "student_applicant"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Inquiry not found: {inquiry}").format(inquiry=inquiry_name))
    return dict(row)


def get_student_applicant_context(student_applicant: str | None) -> dict:
    applicant_name = clean(student_applicant)
    if not applicant_name:
        return {}
    row = frappe.db.get_value(
        "Student Applicant",
        applicant_name,
        ["name", "organization", "school", "applicant_name", "applicant_email", "inquiry"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Student Applicant not found: {student_applicant}").format(student_applicant=applicant_name))
    return dict(row)


def get_channel_account_context(channel_account: str | None) -> dict:
    account_name = clean(channel_account)
    if not account_name:
        return {}
    row = frappe.db.get_value(
        "Admission Channel Account",
        account_name,
        ["name", "organization", "school", "channel_type", "display_name", "enabled"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Admission Channel Account not found: {channel_account}").format(channel_account=account_name))
    return dict(row)


def apply_scope_value(doc, *, organization: str | None, school: str | None, source_label: str) -> None:
    organization_name = clean(organization)
    school_name = clean(school)

    if organization_name:
        if clean(doc.organization) and clean(doc.organization) != organization_name:
            frappe.throw(_("Organization does not match {source_label}.").format(source_label=source_label))
        doc.organization = organization_name

    if school_name:
        if clean(doc.school) and clean(doc.school) != school_name:
            frappe.throw(_("School does not match {source_label}.").format(source_label=source_label))
        doc.school = school_name


def apply_conversation_scope(doc) -> None:
    applicant_context = get_student_applicant_context(doc.student_applicant)
    inquiry_context = get_inquiry_context(doc.inquiry)
    account_context = get_channel_account_context(doc.channel_account)

    if applicant_context:
        apply_scope_value(
            doc,
            organization=applicant_context.get("organization"),
            school=applicant_context.get("school"),
            source_label=_("Student Applicant"),
        )
        applicant_inquiry = clean(applicant_context.get("inquiry"))
        if applicant_inquiry and doc.inquiry and doc.inquiry != applicant_inquiry:
            frappe.throw(_("Inquiry does not match the linked Student Applicant."))
        if applicant_inquiry and not doc.inquiry:
            doc.inquiry = applicant_inquiry

    if inquiry_context:
        apply_scope_value(
            doc,
            organization=inquiry_context.get("organization"),
            school=inquiry_context.get("school"),
            source_label=_("Inquiry"),
        )

    if account_context:
        apply_scope_value(
            doc,
            organization=account_context.get("organization"),
            school=account_context.get("school"),
            source_label=_("Admission Channel Account"),
        )

    assert_school_in_organization_scope(school=doc.school, organization=doc.organization)

    if not clean(doc.organization):
        frappe.throw(_("Organization is required for an admissions CRM conversation."))


def set_conversation_title(doc) -> None:
    if clean(doc.title):
        return

    if clean(doc.inquiry):
        inquiry = get_inquiry_context(doc.inquiry)
        name_parts = [clean(inquiry.get("first_name")), clean(inquiry.get("last_name"))]
        display_name = " ".join(part for part in name_parts if part)
        doc.title = display_name or clean(inquiry.get("email")) or clean(inquiry.get("phone_number")) or doc.inquiry
        return

    if clean(doc.student_applicant):
        applicant = get_student_applicant_context(doc.student_applicant)
        doc.title = clean(applicant.get("applicant_name")) or doc.student_applicant
        return

    if clean(doc.external_identity):
        identity_name = frappe.db.get_value("Admission External Identity", doc.external_identity, "display_name")
        doc.title = clean(identity_name) or doc.external_identity
        return

    doc.title = _("Admissions Conversation")


def message_preview(body: str | None, *, limit: int = 180) -> str:
    text = " ".join(clean(body).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def update_conversation_from_message(message_doc) -> None:
    conversation = clean(message_doc.conversation)
    if not conversation:
        return

    message_at = message_doc.message_at or now_datetime()
    direction = clean(message_doc.direction)
    updates = {
        "latest_message_at": message_at,
        "last_activity_at": message_at,
        "last_message_preview": message_preview(message_doc.body),
    }

    if direction == "Inbound":
        updates["latest_inbound_message_at"] = message_at
        updates["needs_reply"] = 1
    elif direction == "Outbound":
        updates["latest_outbound_message_at"] = message_at
        latest_inbound = frappe.db.get_value("Admission Conversation", conversation, "latest_inbound_message_at")
        if not latest_inbound or message_at >= latest_inbound:
            updates["needs_reply"] = 0

    frappe.db.set_value("Admission Conversation", conversation, updates, update_modified=False)


def update_conversation_from_activity(activity_doc) -> None:
    conversation = clean(activity_doc.conversation)
    if not conversation:
        return

    updates = {
        "last_activity_at": activity_doc.activity_at or now_datetime(),
    }
    if activity_doc.next_action_on:
        updates["next_action_on"] = activity_doc.next_action_on
    frappe.db.set_value("Admission Conversation", conversation, updates, update_modified=False)
