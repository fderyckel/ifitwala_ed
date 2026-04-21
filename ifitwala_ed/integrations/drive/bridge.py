from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

from ifitwala_ed.integrations.drive.workflow_specs import (
    build_upload_session_context,
    get_upload_spec,
    iter_upload_specs,
    normalize_workflow_id,
)

_EMPTY_FINALIZE_CONTRACT = {
    "workflow": None,
    "workflow_id": None,
    "contract_version": None,
    "authoritative_context": None,
    "attached_field_override": None,
    "context_override": None,
    "binding_role": None,
}


def _load_session_workflow_metadata(upload_session_doc) -> dict[str, Any]:
    raw = getattr(upload_session_doc, "upload_contract_json", None)
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}

    workflow = parsed.get("workflow")
    if not isinstance(workflow, dict):
        return {}

    workflow_id = normalize_workflow_id(workflow.get("workflow_id"))
    contract_version = str(workflow.get("contract_version") or "").strip() or None
    if not workflow_id:
        return {}

    return {
        "workflow_id": workflow_id,
        "contract_version": contract_version,
    }


def _validate_provided_authoritative_fields(
    provided_payload: dict[str, Any],
    authoritative_payload: dict[str, Any],
) -> None:
    for fieldname, authoritative_value in authoritative_payload.items():
        if fieldname in {"workflow_id", "contract_version"}:
            continue
        provided_value = provided_payload.get(fieldname)
        if provided_value not in (None, "", authoritative_value):
            frappe.throw(
                _("Workflow upload field '{field_name}' does not match the authoritative owner context.").format(
                    field_name=fieldname
                )
            )


def _normalize_workflow_payload(workflow_payload: Any) -> dict[str, Any]:
    if workflow_payload in (None, ""):
        return {}
    if isinstance(workflow_payload, dict):
        return workflow_payload
    if isinstance(workflow_payload, str):
        try:
            parsed = json.loads(workflow_payload)
        except Exception:
            frappe.throw(_("workflow_payload must be valid JSON."))
        if isinstance(parsed, dict):
            return parsed
    frappe.throw(_("workflow_payload must be a dict."))
    return {}


def resolve_upload_session_context(workflow_id: str, workflow_payload: dict[str, Any]) -> dict[str, Any]:
    return build_upload_session_context(workflow_id, _normalize_workflow_payload(workflow_payload))


def _build_finalize_contract(upload_session_doc, workflow_id: str) -> dict[str, Any]:
    spec = get_upload_spec(workflow_id)
    metadata = _load_session_workflow_metadata(upload_session_doc)
    contract_version = metadata.get("contract_version")
    if contract_version and contract_version != spec.contract_version:
        frappe.throw(
            _("Unsupported governed upload contract version '{0}' for workflow '{1}'.").format(
                contract_version,
                spec.workflow_id,
            )
        )

    authoritative = spec.validate_finalize_context(upload_session_doc)
    if authoritative is None:
        frappe.throw(
            _("Upload session no longer matches the authoritative workflow contract: {0}.").format(spec.workflow_id)
        )

    return {
        "workflow": spec.workflow_id,
        "workflow_id": spec.workflow_id,
        "contract_version": spec.contract_version,
        "authoritative_context": authoritative,
        "attached_field_override": spec.resolve_attached_field_override(upload_session_doc),
        "context_override": spec.resolve_context_override(upload_session_doc, authoritative),
        "binding_role": spec.resolve_binding_role(upload_session_doc, authoritative),
    }


def reconcile_upload_session_payload(payload: dict[str, Any]) -> dict[str, Any]:
    workflow_id = normalize_workflow_id(payload.get("workflow_id"))
    if workflow_id:
        workflow_payload = _normalize_workflow_payload(payload.get("workflow_payload"))
        authoritative = resolve_upload_session_context(workflow_id, workflow_payload)
        _validate_provided_authoritative_fields(payload, authoritative)
        return {
            **payload,
            **authoritative,
            "workflow_id": authoritative["workflow_id"],
            "contract_version": authoritative["contract_version"],
            "workflow_payload": workflow_payload,
        }

    frappe.throw(_("workflow_id is required."))
    return {}


def resolve_finalize_contract(upload_session_doc) -> dict[str, Any]:
    metadata = _load_session_workflow_metadata(upload_session_doc)
    workflow_id = metadata.get("workflow_id")
    if workflow_id:
        return _build_finalize_contract(upload_session_doc, workflow_id)

    for spec in iter_upload_specs():
        authoritative = spec.validate_finalize_context(upload_session_doc)
        if authoritative is None:
            continue
        return {
            "workflow": spec.workflow_id,
            "workflow_id": spec.workflow_id,
            "contract_version": spec.contract_version,
            "authoritative_context": authoritative,
            "attached_field_override": spec.resolve_attached_field_override(upload_session_doc),
            "context_override": spec.resolve_context_override(upload_session_doc, authoritative),
            "binding_role": spec.resolve_binding_role(upload_session_doc, authoritative),
        }

    return dict(_EMPTY_FINALIZE_CONTRACT)


def run_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    metadata = _load_session_workflow_metadata(upload_session_doc)
    workflow_id = metadata.get("workflow_id")
    if not workflow_id:
        workflow_id = normalize_workflow_id(resolve_finalize_contract(upload_session_doc).get("workflow_id"))
    if workflow_id:
        return get_upload_spec(workflow_id).run_post_finalize(upload_session_doc, created_file)

    return {}
