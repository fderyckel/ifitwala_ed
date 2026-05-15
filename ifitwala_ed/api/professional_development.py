# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt

from ifitwala_ed.hr.professional_development_utils import (
    build_my_growth_board,
    cancel_request,
    complete_record,
    decide_request,
    get_request_context_for_user,
    liquidate_record,
    submit_request,
)


def _ensure_logged_in():
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)


def _coerce_rows(value) -> list[dict]:
    if not value:
        return []
    if isinstance(value, str):
        return frappe.parse_json(value) or []
    if isinstance(value, (list, tuple)):
        return list(value)
    frappe.throw(_("Rows payload must be a JSON array."))


def _populate_request_from_payload(doc, payload: dict):
    context = get_request_context_for_user(
        frappe.session.user, budget_name=payload.get("professional_development_budget")
    )
    viewer = context.get("viewer") or {}

    doc.employee = viewer.get("employee")
    doc.organization = viewer.get("organization")
    doc.school = viewer.get("school")
    doc.academic_year = viewer.get("academic_year")
    doc.professional_development_budget = payload.get("professional_development_budget")
    doc.professional_development_theme = payload.get("professional_development_theme")
    doc.pgp_plan = payload.get("pgp_plan")
    doc.pgp_goal = payload.get("pgp_goal")
    doc.title = payload.get("title")
    doc.professional_development_type = payload.get("professional_development_type")
    doc.provider_name = payload.get("provider_name")
    doc.location = payload.get("location")
    doc.start_datetime = payload.get("start_datetime")
    doc.end_datetime = payload.get("end_datetime")
    doc.absence_days = payload.get("absence_days")
    doc.requires_substitute = cint(payload.get("requires_substitute") or 0)
    doc.sharing_commitment = cint(payload.get("sharing_commitment") or 0)
    doc.learning_outcomes = payload.get("learning_outcomes")
    doc.override_reason = payload.get("override_reason")
    doc.override_approved = cint(payload.get("override_approved") or 0)
    if doc.override_approved:
        doc.override_by = frappe.session.user
        doc.override_on = frappe.utils.now_datetime()

    doc.costs = []
    for row in _coerce_rows(payload.get("costs")):
        doc.append(
            "costs",
            {
                "cost_type": row.get("cost_type"),
                "amount": flt(row.get("amount") or 0),
                "notes": row.get("notes"),
            },
        )


@frappe.whitelist()
def get_professional_development_board():
    _ensure_logged_in()
    return build_my_growth_board(frappe.session.user)


@frappe.whitelist()
def get_professional_development_request_context(budget_name: str | None = None):
    _ensure_logged_in()
    return get_request_context_for_user(frappe.session.user, budget_name=budget_name)


@frappe.whitelist()
def submit_professional_development_request(
    request_name: str | None = None,
    professional_development_budget: str | None = None,
    professional_development_theme: str | None = None,
    pgp_plan: str | None = None,
    pgp_goal: str | None = None,
    title: str | None = None,
    professional_development_type: str | None = None,
    provider_name: str | None = None,
    location: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    absence_days: float | None = None,
    requires_substitute: int | None = None,
    sharing_commitment: int | None = None,
    learning_outcomes: str | None = None,
    costs=None,
    override_reason: str | None = None,
    override_approved: int | None = None,
):
    _ensure_logged_in()

    payload = {
        "professional_development_budget": professional_development_budget,
        "professional_development_theme": professional_development_theme,
        "pgp_plan": pgp_plan,
        "pgp_goal": pgp_goal,
        "title": title,
        "professional_development_type": professional_development_type,
        "provider_name": provider_name,
        "location": location,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "absence_days": absence_days,
        "requires_substitute": requires_substitute,
        "sharing_commitment": sharing_commitment,
        "learning_outcomes": learning_outcomes,
        "costs": costs,
        "override_reason": override_reason,
        "override_approved": override_approved,
    }

    if request_name:
        request_doc = frappe.get_doc("Professional Development Request", request_name)
        if request_doc.status != "Draft":
            frappe.throw(_("Only draft Professional Development Requests can be edited before submission."))
    else:
        request_doc = frappe.new_doc("Professional Development Request")

    _populate_request_from_payload(request_doc, payload)
    if request_doc.is_new():
        request_doc.insert(ignore_permissions=True)
    else:
        request_doc.flags.ignore_professional_development_lock = True
        request_doc.save(ignore_permissions=True)

    request_doc = submit_request(request_doc, acting_user=frappe.session.user)
    return {
        "request": frappe.get_doc("Professional Development Request", request_doc.name).as_dict(),
        "board": build_my_growth_board(frappe.session.user),
    }


@frappe.whitelist()
def decide_professional_development_request(
    request_name: str,
    decision: str,
    override_reason: str | None = None,
    override_approved: int | None = None,
    notes: str | None = None,
):
    _ensure_logged_in()
    request_doc = frappe.get_doc("Professional Development Request", request_name)
    request_doc.flags.ignore_professional_development_lock = True
    if override_reason is not None:
        request_doc.override_reason = override_reason
    if override_approved is not None:
        request_doc.override_approved = cint(override_approved or 0)
        if request_doc.override_approved:
            request_doc.override_by = frappe.session.user
            request_doc.override_on = frappe.utils.now_datetime()
    request_doc.save(ignore_permissions=True)
    request_doc = decide_request(request_doc, decision=decision, acting_user=frappe.session.user, notes=notes)
    return {
        "request": frappe.get_doc("Professional Development Request", request_doc.name).as_dict(),
        "board": build_my_growth_board(frappe.session.user),
    }


@frappe.whitelist()
def cancel_professional_development_request(request_name: str, notes: str | None = None):
    _ensure_logged_in()
    request_doc = frappe.get_doc("Professional Development Request", request_name)
    request_doc = cancel_request(request_doc, acting_user=frappe.session.user, notes=notes)
    return {
        "request": frappe.get_doc("Professional Development Request", request_doc.name).as_dict(),
        "board": build_my_growth_board(frappe.session.user),
    }


@frappe.whitelist()
def complete_professional_development_record(
    record_name: str,
    actual_total: float,
    completion_date: str,
    reflection: str | None = None,
    evidence=None,
    liquidation_ready: int | None = 1,
):
    _ensure_logged_in()
    record_doc = frappe.get_doc("Professional Development Record", record_name)
    outcome = complete_record(
        record_doc,
        actual_total=actual_total,
        completion_date=completion_date,
        reflection=reflection,
        evidence_rows=_coerce_rows(evidence),
        liquidation_ready=cint(liquidation_ready or 0),
        acting_user=frappe.session.user,
    )
    return {
        "outcome": frappe.get_doc("Professional Development Outcome", outcome.name).as_dict(),
        "board": build_my_growth_board(frappe.session.user),
    }


@frappe.whitelist()
def liquidate_professional_development_record(
    record_name: str,
    actual_total: float | None = None,
    liquidation_date: str | None = None,
):
    _ensure_logged_in()
    record_doc = frappe.get_doc("Professional Development Record", record_name)
    record_doc = liquidate_record(
        record_doc,
        actual_total=actual_total,
        liquidation_date=liquidation_date,
        acting_user=frappe.session.user,
    )
    return {
        "record": frappe.get_doc("Professional Development Record", record_doc.name).as_dict(),
        "board": build_my_growth_board(frappe.session.user),
    }
