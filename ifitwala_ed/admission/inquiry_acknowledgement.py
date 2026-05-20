# ifitwala_ed/admission/inquiry_acknowledgement.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, now_datetime, validate_email_address

from ifitwala_ed.admission.admission_utils import normalize_email_value
from ifitwala_ed.api.file_access import resolve_public_website_media_url
from ifitwala_ed.governance.policy_scope_utils import get_organization_ancestors_including_self
from ifitwala_ed.website.public_brand import get_public_brand_identity
from ifitwala_ed.website.utils import validate_cta_link

ACK_PROFILE_DOCTYPE = "Admission Acknowledgement Profile"
INQUIRY_DOCTYPE = "Inquiry"
AUTHENTICATED_ADMISSIONS_PORTAL_ROUTE = "/admissions"
INQUIRY_TYPE_ADMISSION = "Admission"
INQUIRY_TYPE_CURRENT_FAMILY = "Current Family"
INQUIRY_TYPE_GENERAL = "General Inquiry"
INQUIRY_TYPE_PARTNERSHIP = "Partnership / Agent"
INQUIRY_TYPE_OTHER = "Other"
PUBLIC_ACKNOWLEDGEMENT_INQUIRY_TYPES = {
    INQUIRY_TYPE_ADMISSION,
    INQUIRY_TYPE_CURRENT_FAMILY,
    INQUIRY_TYPE_GENERAL,
    INQUIRY_TYPE_PARTNERSHIP,
    INQUIRY_TYPE_OTHER,
}

PROFILE_FIELDS = [
    "name",
    "profile_name",
    "organization",
    "school",
    "email_template",
    "thank_you_title",
    "thank_you_message",
    "timeline_intro",
    "footer_note",
    "show_visit_cta",
    "visit_cta_label",
    "visit_cta_route",
    "show_application_cta",
    "application_cta_label",
    "application_cta_route",
]

SCHOOL_CONTEXT_FIELDS = [
    "name",
    "school_name",
    "organization",
    "school_logo",
    "school_logo_file",
    "admissions_visit_route",
]

ORGANIZATION_CONTEXT_FIELDS = [
    "name",
    "organization_name",
    "organization_logo",
    "organization_logo_file",
]


def queue_inquiry_family_acknowledgement(doc) -> None:
    if not getattr(frappe.flags, "in_web_form", False):
        return
    if getattr(doc, "doctype", "") != INQUIRY_DOCTYPE:
        return
    if not normalize_email_value(getattr(doc, "email", None)):
        return

    frappe.enqueue(
        "ifitwala_ed.admission.inquiry_acknowledgement.send_inquiry_family_acknowledgement",
        queue="short",
        enqueue_after_commit=True,
        inquiry_name=doc.name,
    )


def send_inquiry_family_acknowledgement(inquiry_name: str) -> dict:
    inquiry_name = (inquiry_name or "").strip()
    if not inquiry_name:
        return {"sent": False, "reason": "missing_inquiry"}

    inquiry = frappe.get_doc(INQUIRY_DOCTYPE, inquiry_name)
    recipient = normalize_email_value(inquiry.get("email"))
    if not recipient:
        return {"sent": False, "reason": "missing_email"}

    try:
        validate_email_address(recipient, True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Inquiry acknowledgement invalid recipient")
        return {"sent": False, "reason": "invalid_email"}

    profile = resolve_acknowledgement_profile(
        organization=inquiry.get("organization"),
        school=inquiry.get("school"),
    )
    acknowledgement = build_public_acknowledgement_context(
        organization=inquiry.get("organization"),
        school=inquiry.get("school"),
        type_of_inquiry=inquiry.get("type_of_inquiry"),
    )
    profile_for_email = profile if _is_admission_inquiry_type(inquiry.get("type_of_inquiry")) else None

    try:
        subject, message = _render_acknowledgement_email(
            inquiry=inquiry,
            profile=profile_for_email,
            acknowledgement=acknowledgement,
        )
        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
            reference_doctype=INQUIRY_DOCTYPE,
            reference_name=inquiry.name,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Inquiry acknowledgement email failed")
        return {"sent": False, "reason": "send_failed"}

    return {"sent": True, "sent_at": now_datetime()}


def build_public_acknowledgement_context(
    *,
    organization: str | None = None,
    school: str | None = None,
    type_of_inquiry: str | None = None,
) -> dict:
    profile = resolve_acknowledgement_profile(organization=organization, school=school)
    school_row = _get_school_row(school)
    organization_row = _get_organization_row(_resolve_organization(organization=organization, school_row=school_row))
    brand = _build_brand_context(school_row=school_row, organization_row=organization_row)
    variant = _build_acknowledgement_variant(type_of_inquiry=type_of_inquiry)
    allow_profile_copy = _is_admission_inquiry_type(type_of_inquiry)

    ctas = []
    if variant["allow_admission_ctas"]:
        visit_cta = _build_visit_cta(profile=profile, school_row=school_row)
        if visit_cta:
            ctas.append(visit_cta)

        application_cta = _build_application_cta(profile=profile)
        if application_cta:
            ctas.append(application_cta)

    return {
        "brand": brand,
        "title": _profile_value(profile, "thank_you_title", variant["title"], allow_profile=allow_profile_copy),
        "message": _profile_value(profile, "thank_you_message", variant["message"], allow_profile=allow_profile_copy),
        "timeline_intro": _profile_value(
            profile,
            "timeline_intro",
            _("What happens next"),
            allow_profile=allow_profile_copy,
        ),
        "timeline": variant["timeline"],
        "footer_note": _profile_value(profile, "footer_note", "", allow_profile=allow_profile_copy),
        "ctas": ctas,
    }


def resolve_acknowledgement_profile(*, organization: str | None = None, school: str | None = None) -> dict | None:
    if not _profile_doctype_available():
        return None

    school_row = _get_school_row(school)
    school_name = (school_row.get("name") or "").strip()
    if school_name:
        profile = _get_school_profile(school_name)
        if profile:
            return profile

    resolved_organization = _resolve_organization(organization=organization, school_row=school_row)
    if not resolved_organization:
        return None

    return _get_organization_profile(resolved_organization)


def _profile_doctype_available() -> bool:
    try:
        return bool(frappe.db.exists("DocType", ACK_PROFILE_DOCTYPE))
    except Exception:
        return False


def _get_school_profile(school: str) -> dict | None:
    rows = frappe.get_all(
        ACK_PROFILE_DOCTYPE,
        filters={"is_active": 1, "school": school},
        fields=PROFILE_FIELDS,
        order_by="modified desc",
        limit=1,
    )
    return rows[0] if rows else None


def _get_organization_profile(organization: str) -> dict | None:
    organization_chain = get_organization_ancestors_including_self(organization)
    if not organization_chain:
        return None

    rows = frappe.db.sql(
        """
        SELECT
            name,
            profile_name,
            organization,
            school,
            email_template,
            thank_you_title,
            thank_you_message,
            timeline_intro,
            footer_note,
            show_visit_cta,
            visit_cta_label,
            visit_cta_route,
            show_application_cta,
            application_cta_label,
            application_cta_route
        FROM `tabAdmission Acknowledgement Profile`
        WHERE is_active = 1
            AND organization IN %(organizations)s
            AND (school IS NULL OR school = '')
        ORDER BY modified DESC
        """,
        {"organizations": tuple(organization_chain)},
        as_dict=True,
    )
    by_organization = {(row.get("organization") or "").strip(): row for row in rows}
    for organization_name in organization_chain:
        profile = by_organization.get(organization_name)
        if profile:
            return profile
    return None


def _get_school_row(school: str | None) -> dict:
    school = (school or "").strip()
    if not school:
        return {}
    row = frappe.db.get_value("School", school, SCHOOL_CONTEXT_FIELDS, as_dict=True)
    return dict(row or {})


def _get_organization_row(organization: str | None) -> dict:
    organization = (organization or "").strip()
    if not organization:
        return {}
    row = frappe.db.get_value("Organization", organization, ORGANIZATION_CONTEXT_FIELDS, as_dict=True)
    return dict(row or {})


def _resolve_organization(*, organization: str | None, school_row: dict) -> str:
    explicit = (organization or "").strip()
    if explicit:
        return explicit
    return (school_row.get("organization") or "").strip()


def _build_brand_context(*, school_row: dict, organization_row: dict) -> dict:
    if school_row:
        brand_name = (school_row.get("school_name") or school_row.get("name") or "").strip()
        logo_url = _resolve_public_logo(
            file_name=school_row.get("school_logo_file"),
            file_url=school_row.get("school_logo"),
        )
        return {
            "name": brand_name,
            "logo": logo_url or "",
            "scope": "School",
        }

    if organization_row:
        brand_name = (organization_row.get("organization_name") or organization_row.get("name") or "").strip()
        logo_url = _resolve_public_logo(
            file_name=organization_row.get("organization_logo_file"),
            file_url=organization_row.get("organization_logo"),
        )
        return {
            "name": brand_name,
            "logo": logo_url or "",
            "scope": "Organization",
        }

    public_brand = get_public_brand_identity()
    return {
        "name": (public_brand.get("brand_name") or _("Ifitwala Ed")).strip(),
        "logo": (public_brand.get("brand_logo") or "").strip(),
        "scope": "Site",
    }


def _resolve_public_logo(*, file_name: str | None, file_url: str | None) -> str:
    try:
        return (
            resolve_public_website_media_url(
                file_name=(file_name or "").strip() or None,
                file_url=(file_url or "").strip() or None,
            )
            or ""
        )
    except Exception:
        return ""


def _profile_value(profile: dict | None, fieldname: str, fallback: str, *, allow_profile: bool = True) -> str:
    if not allow_profile:
        return fallback

    value = ""
    if profile:
        value = (profile.get(fieldname) or "").strip()
    return value or fallback


def _normalize_public_inquiry_type(type_of_inquiry: str | None) -> str:
    value = (type_of_inquiry or "").strip()
    if value in PUBLIC_ACKNOWLEDGEMENT_INQUIRY_TYPES:
        return value
    return INQUIRY_TYPE_GENERAL


def _is_admission_inquiry_type(type_of_inquiry: str | None) -> bool:
    return _normalize_public_inquiry_type(type_of_inquiry) == INQUIRY_TYPE_ADMISSION


def _build_acknowledgement_variant(*, type_of_inquiry: str | None) -> dict:
    normalized_type = _normalize_public_inquiry_type(type_of_inquiry)

    if normalized_type == INQUIRY_TYPE_ADMISSION:
        return {
            "type_of_inquiry": normalized_type,
            "allow_admission_ctas": True,
            "title": _("Inquiry received"),
            "message": _(
                "Thank you for contacting us. Our admissions team will review your inquiry and get back to you soon."
            ),
            "email_followup": _("A member of the admissions team will contact you with the next practical step."),
            "timeline": [
                {
                    "label": _("Inquiry received"),
                    "description": _("Your message is now in the admissions inbox."),
                },
                {
                    "label": _("Admissions review"),
                    "description": _(
                        "The team checks the school context, student details, and preferred contact channel."
                    ),
                },
                {
                    "label": _("Family follow-up"),
                    "description": _("A staff member replies with the next practical action."),
                },
                {
                    "label": _("Next step"),
                    "description": _(
                        "If the next step is an application, admissions staff will send the correct application path."
                    ),
                },
            ],
        }

    if normalized_type == INQUIRY_TYPE_CURRENT_FAMILY:
        return {
            "type_of_inquiry": normalized_type,
            "allow_admission_ctas": False,
            "title": _("Inquiry received"),
            "message": _(
                "Thank you for contacting us. We will route your message to the appropriate school team and they will follow up through your preferred contact channel."
            ),
            "email_followup": _(
                "The appropriate school team will review your message and follow up through your preferred contact channel."
            ),
            "timeline": [
                {
                    "label": _("Message received"),
                    "description": _("Your message has been received by the school team."),
                },
                {
                    "label": _("School context checked"),
                    "description": _("The team checks the school context and any student details you shared."),
                },
                {
                    "label": _("Routed to the right team"),
                    "description": _("Your message is forwarded to the staff member or office best placed to help."),
                },
                {
                    "label": _("Team follow-up"),
                    "description": _("The appropriate team follows up through your preferred contact channel."),
                },
            ],
        }

    if normalized_type == INQUIRY_TYPE_PARTNERSHIP:
        return {
            "type_of_inquiry": normalized_type,
            "allow_admission_ctas": False,
            "title": _("Inquiry received"),
            "message": _(
                "Thank you for contacting us. We will review the organization and partnership details, then route the inquiry to the appropriate person."
            ),
            "email_followup": _(
                "The appropriate person will review the partnership context and follow up when there is a practical next step."
            ),
            "timeline": [
                {
                    "label": _("Partnership inquiry received"),
                    "description": _("Your partnership or agent inquiry has been received."),
                },
                {
                    "label": _("Context reviewed"),
                    "description": _("The team reviews the organization details and partnership context you shared."),
                },
                {
                    "label": _("Routed to the right owner"),
                    "description": _("The inquiry is forwarded to the person best placed to assess the request."),
                },
                {
                    "label": _("Next conversation"),
                    "description": _(
                        "The appropriate person follows up if there is a fit or a useful next discussion."
                    ),
                },
            ],
        }

    if normalized_type == INQUIRY_TYPE_OTHER:
        return {
            "type_of_inquiry": normalized_type,
            "allow_admission_ctas": False,
            "title": _("Inquiry received"),
            "message": _(
                "Thank you for contacting us. We will review your message and forward it to the appropriate team or person."
            ),
            "email_followup": _("The appropriate team or person will follow up if a response is needed."),
            "timeline": [
                {
                    "label": _("Message received"),
                    "description": _("Your message has been received."),
                },
                {
                    "label": _("Triage review"),
                    "description": _("The team reviews your message to understand who should handle it."),
                },
                {
                    "label": _("Routed internally"),
                    "description": _("Your message is forwarded to the appropriate team or person."),
                },
                {
                    "label": _("Appropriate follow-up"),
                    "description": _("The right team follows up if a response is needed."),
                },
            ],
        }

    return {
        "type_of_inquiry": normalized_type,
        "allow_admission_ctas": False,
        "title": _("Inquiry received"),
        "message": _(
            "Thank you for contacting us. We will review your question and forward it to the team best placed to respond."
        ),
        "email_followup": _("The team best placed to respond will follow up if a response is needed."),
        "timeline": [
            {
                "label": _("Inquiry received"),
                "description": _("Your question has been received."),
            },
            {
                "label": _("Request reviewed"),
                "description": _("The team reviews your question and the context you shared."),
            },
            {
                "label": _("Forwarded internally"),
                "description": _("Your inquiry is forwarded to the team best placed to respond."),
            },
            {
                "label": _("Follow-up if needed"),
                "description": _("The right team follows up when there is a useful next step or response."),
            },
        ],
    }


def _safe_cta_link(route: str | None) -> str:
    route = (route or "").strip()
    if not route:
        return ""
    try:
        return validate_cta_link(route)
    except Exception:
        return ""


def _build_visit_cta(*, profile: dict | None, school_row: dict) -> dict | None:
    if profile and not cint(profile.get("show_visit_cta")):
        return None

    route = ""
    label = _("Book a tour or open day")
    if profile:
        route = (profile.get("visit_cta_route") or "").strip()
        label = (profile.get("visit_cta_label") or "").strip() or label
    if not route and school_row:
        route = (school_row.get("admissions_visit_route") or "").strip()

    route = _safe_cta_link(route)
    if not route:
        return None
    return {"kind": "visit", "label": label, "url": route}


def _build_application_cta(*, profile: dict | None) -> dict | None:
    if not profile or not cint(profile.get("show_application_cta")):
        return None

    route = _safe_cta_link(profile.get("application_cta_route"))
    if not route or route == AUTHENTICATED_ADMISSIONS_PORTAL_ROUTE:
        return None

    label = (profile.get("application_cta_label") or "").strip() or _("Start an application")
    return {"kind": "application", "label": label, "url": route}


def _render_acknowledgement_email(*, inquiry, profile: dict | None, acknowledgement: dict) -> tuple[str, str]:
    if profile and (profile.get("email_template") or "").strip():
        email_template = frappe.get_doc("Email Template", profile.get("email_template"))
        context = _email_template_context(inquiry=inquiry, profile=profile, acknowledgement=acknowledgement)
        subject = frappe.render_template(email_template.subject or "", context)
        template_body = (
            (
                email_template.get("response_html")
                if cint(email_template.get("use_html"))
                else email_template.get("response")
            )
            or email_template.get("response")
            or email_template.get("response_html")
            or ""
        )
        message = frappe.render_template(template_body, context)
        if message:
            return subject or _("We received your inquiry"), message
        fallback_subject, fallback_message = _render_acknowledgement_email(
            inquiry=inquiry,
            profile=None,
            acknowledgement=acknowledgement,
        )
        return subject or fallback_subject, fallback_message

    brand_name = ((acknowledgement.get("brand") or {}).get("name") or _("us")).strip()
    first_name = (inquiry.get("first_name") or "").strip()
    greeting = _("Hello {first_name},").format(first_name=first_name) if first_name else _("Hello,")
    variant = _build_acknowledgement_variant(type_of_inquiry=inquiry.get("type_of_inquiry"))
    subject = _("We received your inquiry")
    message = "\n\n".join(
        [
            greeting,
            _("Thank you for contacting {brand_name}. We received your inquiry and will review it shortly.").format(
                brand_name=brand_name
            ),
            variant["email_followup"],
        ]
    )
    return subject, message


def _email_template_context(*, inquiry, profile: dict, acknowledgement: dict) -> dict[str, Any]:
    return {
        "doc": inquiry.as_dict(),
        "inquiry": inquiry.as_dict(),
        "profile": profile,
        "acknowledgement": acknowledgement,
        "brand": acknowledgement.get("brand") or {},
        "timeline": acknowledgement.get("timeline") or [],
        "ctas": acknowledgement.get("ctas") or [],
    }
