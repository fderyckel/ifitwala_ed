# ifitwala_ed/api/inquiry.py

from __future__ import annotations

import frappe

import ifitwala_ed.admission.api.inquiry.access as _access
import ifitwala_ed.admission.api.inquiry.dashboard as _dashboard
import ifitwala_ed.admission.api.inquiry.lookups as _lookups
import ifitwala_ed.admission.api.inquiry.zero_lost as _zero_lost

ALLOWED_ANALYTICS_ROLES = _access.ALLOWED_ANALYTICS_ROLES


@frappe.whitelist()
def get_dashboard_data(filters=None):
    return _dashboard.get_dashboard_data(filters=filters)


@frappe.whitelist()
def get_zero_lost_lead_context(filters=None, active_view: str | None = None, start=0, limit=25):
    return _zero_lost.get_zero_lost_lead_context(
        filters=filters,
        active_view=active_view,
        start=start,
        limit=limit,
    )


@frappe.whitelist()
def get_inquiry_organizations():
    return _lookups.get_inquiry_organizations()


@frappe.whitelist()
def get_inquiry_schools():
    return _lookups.get_inquiry_schools()


@frappe.whitelist()
def academic_year_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    return _lookups.academic_year_link_query(
        doctype=doctype,
        txt=txt,
        searchfield=searchfield,
        start=start,
        page_len=page_len,
        filters=filters,
    )


@frappe.whitelist(allow_guest=True)
@frappe.validate_and_sanitize_search_inputs
def inquiry_organization_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    return _lookups.inquiry_organization_link_query(
        doctype=doctype,
        txt=txt,
        searchfield=searchfield,
        start=start,
        page_len=page_len,
        filters=filters,
    )


inquiry_organization_link_query.allow_guest = True


@frappe.whitelist(allow_guest=True)
@frappe.validate_and_sanitize_search_inputs
def inquiry_school_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    return _lookups.inquiry_school_link_query(
        doctype=doctype,
        txt=txt,
        searchfield=searchfield,
        start=start,
        page_len=page_len,
        filters=filters,
    )


inquiry_school_link_query.allow_guest = True


@frappe.whitelist(allow_guest=True)
def get_inquiry_acknowledgement_context(organization=None, school=None, type_of_inquiry=None):
    return _lookups.get_inquiry_acknowledgement_context(
        organization=organization,
        school=school,
        type_of_inquiry=type_of_inquiry,
    )


get_inquiry_acknowledgement_context.allow_guest = True


@frappe.whitelist()
def admission_user_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    return _lookups.admission_user_link_query(
        doctype=doctype,
        txt=txt,
        searchfield=searchfield,
        start=start,
        page_len=page_len,
        filters=filters,
    )


@frappe.whitelist()
def get_inquiry_types():
    return _lookups.get_inquiry_types()


@frappe.whitelist()
def get_inquiry_sources():
    return _lookups.get_inquiry_sources()
