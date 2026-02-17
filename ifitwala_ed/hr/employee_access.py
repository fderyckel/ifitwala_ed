# Copyright (c) 2025, François de Ryckel
# For license information, please see license.txt

# ifitwala_ed/hr/employee_access.py

import frappe
from frappe.utils import getdate, nowdate
from frappe.utils.caching import redis_cache

MANAGED_FLAG = "managed_by_ifitwala"  # provenance flag on User.roles children


@redis_cache(ttl=86400)
def _roles_from_role_name(role_name: str) -> set[str]:
    if not role_name:
        return set()
    if not frappe.db.exists("Role", role_name):
        return set()
    return {role_name}


@redis_cache(ttl=86400)
def _designation_defaults(designation: str) -> dict:
    if not designation:
        return {}
    row = (
        frappe.db.get_value(
            "Designation",
            designation,
            ["default_role_profile", "default_workspace", "workspace_priority"],
            as_dict=True,
        )
        or {}
    )
    return {
        "role_profile": row.get("default_role_profile"),
        "workspace": row.get("default_workspace"),
        "priority": int(row.get("workspace_priority") or 0),
        "roles": _roles_from_role_name(row.get("default_role_profile")),
    }


def _resolve_row_access(h) -> dict:
    """
    h is a child row (dict-like) of Employee History.
    Resolves roles/workspace/priority based on access_mode + designation defaults.
    """
    mode = (h.get("access_mode") or "Follow Designation").strip()
    if mode == "Override":
        return {
            "roles": _roles_from_role_name(h.get("role_profile")),
            "workspace": h.get("workspace_override"),
            "priority": int(h.get("priority") or 0),
        }
    if mode == "Snapshot":
        # If row already has stored values, use them; otherwise seed from designation.
        if h.get("role_profile") or h.get("workspace_override") or h.get("priority"):
            return {
                "roles": _roles_from_role_name(h.get("role_profile")),
                "workspace": h.get("workspace_override"),
                "priority": int(h.get("priority") or 0),
            }
        # fallthrough to Follow Designation seeding
        mode = "Follow Designation"

    # Follow Designation (live)
    d = _designation_defaults(h.get("designation"))
    return {"roles": d.get("roles", set()), "workspace": d.get("workspace"), "priority": int(d.get("priority") or 0)}


def _active_history_rows(emp) -> list[dict]:
    # You already compute is_current server-side; we trust that.
    rows = []
    for h in emp.employee_history or []:
        if not h.get("designation"):
            continue
        if not h.get("is_current"):
            continue
        # Optionally enforce strict date window here if you prefer
        rows.append(h)
    return rows


def _prejoin_access_from_designation(emp) -> tuple[set[str], str | None]:
    """
    Provision baseline role before joining date so newly created users are usable
    for onboarding, but do not set workspace until active history exists.
    """
    if not getattr(emp, "designation", None) or not getattr(emp, "date_of_joining", None):
        return set(), None

    try:
        join_date = getdate(emp.date_of_joining)
        today = getdate(nowdate())
    except Exception:
        return set(), None

    if join_date <= today:
        return set(), None

    d = _designation_defaults(emp.designation)
    return set(d.get("roles", set())), None


def compute_effective_access_from_employee(emp) -> tuple[set[str], str | None]:
    """Union roles from all active rows; pick workspace from highest priority."""
    chunks = [_resolve_row_access(h) for h in _active_history_rows(emp)]
    if not chunks:
        return _prejoin_access_from_designation(emp)
    target_roles = set().union(*(c["roles"] for c in chunks))
    best = max(chunks, key=lambda c: int(c.get("priority") or 0))
    return target_roles, best.get("workspace")


def _diff_user_roles(user_doc, target_roles: set[str]):
    current_all = {r.role for r in user_doc.roles}
    to_add = target_roles - current_all
    to_remove = [ch for ch in list(user_doc.roles) if ch.get(MANAGED_FLAG) and ch.role not in target_roles]
    return to_add, to_remove


def sync_user_access_from_employee(emp):
    """
    Called from Employee.after_save.
    - Adds/removes only managed roles.
    - Updates default workspace if effective workspace changed.
    """
    if not emp.user_id:
        return

    target_roles, target_ws = compute_effective_access_from_employee(emp)
    user = frappe.get_doc("User", emp.user_id)

    to_add, to_remove = _diff_user_roles(user, target_roles)
    for role in to_add:
        user.append("roles", {"role": role, MANAGED_FLAG: 1})
    for ch in to_remove:
        user.remove(ch)

    changed = bool(to_add or to_remove)
    if target_ws and user.default_workspace != target_ws and user.user_type == "System User":
        user.default_workspace = target_ws
        changed = True

    if changed:
        user.save(ignore_permissions=True)
        if target_ws:
            try:
                from ifitwala_ed.hr.workspace_utils import send_workspace_notification

                send_workspace_notification(user.name, target_ws)
            except Exception:
                pass


def effective_workspace_for_user(user: str) -> str | None:
    """
    Safety helper used by workspace_utils to suggest a workspace
    even when we're running from User.validate (no Employee.after_save context).
    """
    emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not emp:
        return None
    emp_doc = frappe.get_doc("Employee", emp)
    _, ws = compute_effective_access_from_employee(emp_doc)
    return ws
