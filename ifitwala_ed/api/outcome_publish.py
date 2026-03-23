# Copyright (c) 2026
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist()
def publish_outcomes(payload=None, **kwargs):
    data = _normalize_payload(payload, kwargs)
    outcome_ids = _extract_outcome_ids(data)
    if not outcome_ids:
        frappe.throw(_("Outcome IDs are required."))

    if not _can_write_gradebook() and not _is_academic_adminish():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    now = now_datetime()
    _bulk_update_publish(
        outcome_ids,
        {"is_published": 1, "published_on": now, "published_by": frappe.session.user},
    )
    return {"outcomes": _get_publish_summaries(outcome_ids)}


@frappe.whitelist()
def unpublish_outcomes(payload=None, **kwargs):
    data = _normalize_payload(payload, kwargs)
    outcome_ids = _extract_outcome_ids(data)
    if not outcome_ids:
        frappe.throw(_("Outcome IDs are required."))

    if not _is_academic_adminish():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    _bulk_update_publish(
        outcome_ids,
        {"is_published": 0, "published_on": None, "published_by": None},
    )
    return {"outcomes": _get_publish_summaries(outcome_ids)}


def _bulk_update_publish(outcome_ids, values):
    ordered_ids = []
    seen = set()
    for outcome_id in outcome_ids or []:
        if not outcome_id or outcome_id in seen:
            continue
        seen.add(outcome_id)
        ordered_ids.append(outcome_id)

    if not ordered_ids:
        return

    existing_ids = set(
        frappe.get_all(
            "Task Outcome",
            filters={"name": ["in", ordered_ids]},
            pluck="name",
            ignore_permissions=True,
        )
        or []
    )

    # Publish state is business state on Task Outcome, so updates must flow
    # through the document lifecycle rather than a table-level UPDATE.
    for outcome_id in ordered_ids:
        if outcome_id not in existing_ids:
            continue

        outcome_doc = frappe.get_doc("Task Outcome", outcome_id)
        outcome_doc.is_published = values.get("is_published")
        outcome_doc.published_on = values.get("published_on")
        outcome_doc.published_by = values.get("published_by")
        outcome_doc.save(ignore_permissions=True)


def _get_publish_summaries(outcome_ids):
    rows = frappe.db.get_values(
        "Task Outcome",
        {"name": ["in", list(outcome_ids)]},
        ["name", "is_published", "published_on", "published_by"],
        as_dict=True,
    )
    return [
        {
            "outcome_id": row.get("name"),
            "is_published": bool(int(row.get("is_published") or 0)),
            "published_on": row.get("published_on"),
            "published_by": row.get("published_by"),
        }
        for row in rows
    ]


def _normalize_payload(payload, kwargs):
    data = payload if payload is not None else kwargs
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw(_("Payload must be a dict."))
    return data


def _extract_outcome_ids(data):
    outcome_ids = data.get("outcome_ids") or data.get("outcomes") or []
    if isinstance(outcome_ids, str):
        outcome_ids = [outcome_ids]
    return [oid for oid in outcome_ids if oid]


def _has_role(*roles):
    user_roles = set(frappe.get_roles(frappe.session.user))
    return any(role in user_roles for role in roles)


def _is_academic_adminish():
    return _has_role("System Manager", "Academic Admin", "Academic Assistant", "Curriculum Coordinator")


def _can_write_gradebook():
    return _has_role("System Manager", "Academic Admin", "Curriculum Coordinator", "Instructor")
