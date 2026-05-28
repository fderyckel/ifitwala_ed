from __future__ import annotations

from contextlib import contextmanager

import frappe

from ifitwala_ed.admission.api.communication.constants import (
    _LOCAL_ATTRS_RESET_BY_SET_USER,
    _MISSING_LOCAL_ATTR,
)


def _snapshot_request_session() -> frappe._dict:
    session = getattr(frappe.local, "session", frappe._dict())
    snapshot = frappe._dict(session.copy() if hasattr(session, "copy") else {})
    session_data = snapshot.get("data")
    if hasattr(session_data, "copy"):
        snapshot["data"] = frappe._dict(session_data.copy())
    elif session_data is None:
        snapshot["data"] = frappe._dict()
    else:
        snapshot["data"] = session_data
    return snapshot


def _restore_request_session(snapshot: frappe._dict) -> None:
    session = getattr(frappe.local, "session", None)
    if session is None:
        frappe.local.session = frappe._dict(snapshot)
        return
    session.clear()
    session.update(snapshot)


@contextmanager
def _administrator_context_preserving_request_session():
    """Validate the system-owned thread insert as Administrator without poisoning the browser session."""
    session_snapshot = _snapshot_request_session()
    local_attr_snapshot = {
        attr: getattr(frappe.local, attr, _MISSING_LOCAL_ATTR) for attr in _LOCAL_ATTRS_RESET_BY_SET_USER
    }

    frappe.set_user("Administrator")
    try:
        yield
    finally:
        _restore_request_session(session_snapshot)
        for attr, value in local_attr_snapshot.items():
            if value is _MISSING_LOCAL_ATTR:
                if hasattr(frappe.local, attr):
                    delattr(frappe.local, attr)
                continue
            setattr(frappe.local, attr, value)
