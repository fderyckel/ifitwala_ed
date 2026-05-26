# ifitwala_ed/admission/api/crm/activities.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import ensure_admissions_crm_permission
from ifitwala_ed.admission.api.crm.guards import _require_conversation_write
from ifitwala_ed.admission.api.crm.idempotency import IDEMPOTENCY_TTL_SECONDS, _cache, _idempotency_key, _lock_key
from ifitwala_ed.admission.api.crm.summaries import _activity_summary, _conversation_summary


def record_admission_crm_activity_impl(
    *,
    conversation: str | None = None,
    activity_type: str | None = None,
    outcome: str | None = None,
    note: str | None = None,
    next_action_on: str | None = None,
    activity_at: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    conversation_name = clean(conversation)
    activity_type_value = clean(activity_type)
    if not conversation_name:
        frappe.throw(_("Admission Conversation is required."))
    if not activity_type_value:
        frappe.throw(_("Activity Type is required."))

    request_id = clean(client_request_id)
    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key("record_activity", user, conversation_name, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key("record_activity", user, conversation_name), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        _require_conversation_write(user, conversation_name)
        activity_doc = frappe.get_doc(
            {
                "doctype": "Admission CRM Activity",
                "conversation": conversation_name,
                "activity_type": activity_type_value,
                "outcome": outcome,
                "note": note,
                "next_action_on": clean(next_action_on),
                "activity_at": clean(activity_at),
            }
        )
        activity_doc.insert(ignore_permissions=True)
        response = {
            "ok": True,
            "conversation": _conversation_summary(conversation_name),
            "activity": _activity_summary(activity_doc.name),
        }
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return response
