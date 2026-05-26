# ifitwala_ed/admission/api/crm/inquiry_actions.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import assign_inquiry, from_inquiry_invite, reassign_inquiry
from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import ensure_admissions_crm_permission
from ifitwala_ed.admission.api.crm.guards import _require_inquiry_write
from ifitwala_ed.admission.api.crm.idempotency import _run_idempotent
from ifitwala_ed.admission.api.crm.summaries import _applicant_summary, _inquiry_summary


def assign_inquiry_from_inbox_impl(
    *,
    inquiry: str | None = None,
    assigned_to: str | None = None,
    assignment_lane: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    assignee = clean(assigned_to)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))
    if not assignee:
        frappe.throw(_("Assigned To is required."))

    def action():
        doc = _require_inquiry_write(user, inquiry_name)
        if clean(doc.assigned_to) == assignee:
            return {"ok": True, "changed": False, "inquiry": _inquiry_summary(doc.name)}

        if clean(doc.assigned_to):
            result = reassign_inquiry("Inquiry", doc.name, assignee, assignment_lane=assignment_lane)
        else:
            result = assign_inquiry("Inquiry", doc.name, assignee, assignment_lane=assignment_lane)

        return {"ok": True, "changed": True, "result": result, "inquiry": _inquiry_summary(doc.name)}

    return _run_idempotent(
        user=user,
        action="assign_inquiry",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )


def archive_inquiry_from_inbox_impl(
    *,
    inquiry: str | None = None,
    reason: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    archive_reason = clean(reason)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))
    if not archive_reason:
        frappe.throw(_("Archive reason is required."))

    def action():
        doc = _require_inquiry_write(user, inquiry_name)
        if clean(doc.workflow_state) == "Archived" and clean(doc.archive_reason):
            return {"ok": True, "changed": False, "inquiry": _inquiry_summary(doc.name)}
        result = doc.archive(reason=archive_reason)
        return {
            "ok": True,
            "changed": bool(result.get("changed")),
            "result": result,
            "inquiry": _inquiry_summary(doc.name),
        }

    return _run_idempotent(
        user=user,
        action="archive_inquiry",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )


def mark_inquiry_contacted_from_inbox_impl(
    *,
    inquiry: str | None = None,
    complete_todo: int | str | None = 0,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))

    def action():
        doc = _require_inquiry_write(user, inquiry_name)
        if clean(doc.workflow_state) in {"Contacted", "Qualified"}:
            return {"ok": True, "changed": False, "inquiry": _inquiry_summary(doc.name)}
        result = doc.mark_contacted(complete_todo=frappe.utils.cint(complete_todo))
        return {"ok": True, "changed": True, "result": result, "inquiry": _inquiry_summary(doc.name)}

    return _run_idempotent(
        user=user,
        action="mark_inquiry_contacted",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )


def qualify_inquiry_from_inbox_impl(
    *,
    inquiry: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))

    def action():
        doc = _require_inquiry_write(user, inquiry_name)
        if clean(doc.workflow_state) == "Qualified":
            return {"ok": True, "changed": False, "inquiry": _inquiry_summary(doc.name)}
        result = doc.mark_qualified()
        return {
            "ok": True,
            "changed": bool(result.get("changed")),
            "result": result,
            "inquiry": _inquiry_summary(doc.name),
        }

    return _run_idempotent(
        user=user,
        action="qualify_inquiry",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )


def invite_inquiry_to_apply_from_inbox_impl(
    *,
    inquiry: str | None = None,
    school: str | None = None,
    organization: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    school_name = clean(school)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))
    if not school_name:
        frappe.throw(_("School is required to invite an applicant."))

    def action():
        _require_inquiry_write(user, inquiry_name)
        applicant_name = from_inquiry_invite(
            inquiry_name=inquiry_name,
            school=school_name,
            organization=clean(organization) or None,
        )
        return {
            "ok": True,
            "student_applicant": _applicant_summary(applicant_name),
            "inquiry": _inquiry_summary(inquiry_name),
        }

    return _run_idempotent(
        user=user,
        action="invite_inquiry",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )
