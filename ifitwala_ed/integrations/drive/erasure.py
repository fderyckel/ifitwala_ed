from __future__ import annotations

from importlib import import_module
from typing import Any, Iterable

import frappe
from frappe import _

_ALLOWED_DECISIONS = {"erase", "retain", "anonymize", "skip"}
_DECISION_ALIASES = {"delete": "erase", "deleted": "erase", "erased": "erase"}
_METADATA_FILTER_FIELDS = (
    "owner_doctype",
    "owner_name",
    "attached_doctype",
    "attached_name",
    "slot",
    "purpose",
    "retention_policy",
    "organization",
    "school",
    "data_class",
)
_POLICY_LIST_FIELDS = (
    "erase_retention_policies",
    "retain_retention_policies",
    "anonymize_retention_policies",
    "erase_purposes",
    "retain_purposes",
    "anonymize_purposes",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_list(value: Any) -> set[str]:
    if value in (None, ""):
        return set()
    if isinstance(value, str):
        return {_clean_text(value)} if _clean_text(value) else set()
    if isinstance(value, Iterable):
        return {_clean_text(item) for item in value if _clean_text(item)}
    return {_clean_text(value)} if _clean_text(value) else set()


def _normalize_decision(value: Any) -> str:
    decision = _clean_text(value).lower()
    decision = _DECISION_ALIASES.get(decision, decision)
    if decision not in _ALLOWED_DECISIONS:
        frappe.throw(_("Invalid erasure decision: {0}").format(decision or "<empty>"))
    return decision


def _normalize_metadata_filters(metadata_filters: dict[str, Any] | None) -> dict[str, str]:
    return {
        fieldname: _clean_text((metadata_filters or {}).get(fieldname))
        for fieldname in _METADATA_FILTER_FIELDS
        if _clean_text((metadata_filters or {}).get(fieldname))
    }


def normalize_erasure_decision_items(decision_items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in decision_items or []:
        if not isinstance(row, dict):
            frappe.throw(_("Erasure decision items must be mappings."))
        decision = _normalize_decision(row.get("decision"))
        item = {
            fieldname: _clean_text(row.get(fieldname))
            for fieldname in ("drive_file_id", "name", *_METADATA_FILTER_FIELDS)
            if _clean_text(row.get(fieldname))
        }
        if not item:
            frappe.throw(_("Erasure decision items must include drive_file_id or metadata selectors."))
        item["decision"] = decision
        item["reason"] = _clean_text(row.get("reason")) or f"ed_decision_{decision}"
        normalized.append(item)
    return normalized


def _normalize_school_policy(school_policy: dict[str, Any] | None) -> dict[str, set[str]]:
    policy = school_policy or {}
    return {fieldname: _clean_list(policy.get(fieldname)) for fieldname in _POLICY_LIST_FIELDS}


def decide_file_erasure_action(
    file_metadata: dict[str, Any],
    *,
    school_policy: dict[str, Any] | None = None,
) -> dict[str, str]:
    policy = _normalize_school_policy(school_policy)
    retention_policy = _clean_text(file_metadata.get("retention_policy"))
    purpose = _clean_text(file_metadata.get("purpose"))

    if int(file_metadata.get("legal_hold") or 0):
        return {"decision": "retain", "reason": "legal_hold"}

    if retention_policy in policy["retain_retention_policies"]:
        return {"decision": "retain", "reason": f"retention_policy:{retention_policy}"}
    if purpose in policy["retain_purposes"]:
        return {"decision": "retain", "reason": f"purpose:{purpose}"}

    if retention_policy in policy["anonymize_retention_policies"]:
        return {"decision": "anonymize", "reason": f"retention_policy:{retention_policy}"}
    if purpose in policy["anonymize_purposes"]:
        return {"decision": "anonymize", "reason": f"purpose:{purpose}"}

    if retention_policy in policy["erase_retention_policies"]:
        return {"decision": "erase", "reason": f"retention_policy:{retention_policy}"}
    if purpose in policy["erase_purposes"]:
        return {"decision": "erase", "reason": f"purpose:{purpose}"}

    return {"decision": "retain", "reason": "no_school_policy_rule"}


def build_subject_file_erasure_decision_plan(
    file_rows: list[dict[str, Any]],
    *,
    school_policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    decision_items: list[dict[str, Any]] = []
    for row in file_rows or []:
        drive_file_id = _clean_text(row.get("drive_file_id") or row.get("name"))
        if not drive_file_id:
            frappe.throw(_("File erasure decision rows must include drive_file_id or name."))
        decision = decide_file_erasure_action(row, school_policy=school_policy)
        decision_items.append(
            {
                "drive_file_id": drive_file_id,
                "decision": decision["decision"],
                "reason": decision["reason"],
            }
        )
    return decision_items


def _load_drive_erasure_api():
    try:
        return import_module("ifitwala_drive.api.erasure")
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed erasure execution: {0}").format(exc))


def create_subject_file_erasure_request(
    *,
    data_subject_type: str,
    data_subject_id: str,
    request_reason: str | None = None,
) -> dict[str, Any]:
    resolved_subject_type = _clean_text(data_subject_type)
    resolved_subject_id = _clean_text(data_subject_id)
    if not resolved_subject_type or not resolved_subject_id:
        frappe.throw(_("data_subject_type and data_subject_id are required."))

    drive_erasure_api = _load_drive_erasure_api()
    return drive_erasure_api.create_drive_erasure_request(
        data_subject_type=resolved_subject_type,
        data_subject_id=resolved_subject_id,
        scope="files_only",
        request_reason=request_reason,
    )


def execute_subject_file_erasure_request(
    *,
    erasure_request_id: str,
    decision_items: list[dict[str, Any]],
    metadata_filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_request_id = _clean_text(erasure_request_id)
    if not resolved_request_id:
        frappe.throw(_("erasure_request_id is required."))

    normalized_decisions = normalize_erasure_decision_items(decision_items)
    if not normalized_decisions:
        frappe.throw(_("At least one Ed erasure decision item is required."))

    drive_erasure_api = _load_drive_erasure_api()
    return drive_erasure_api.execute_drive_erasure_request(
        erasure_request_id=resolved_request_id,
        metadata_filters=_normalize_metadata_filters(metadata_filters),
        decision_items=normalized_decisions,
    )
