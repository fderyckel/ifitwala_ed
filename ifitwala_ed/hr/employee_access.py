# Copyright (c) 2025, François de Ryckel
# For license information, please see license.txt

# ifitwala_ed/hr/employee_access.py

import frappe
from frappe import _
from frappe.utils import getdate, nowdate
from frappe.utils.caching import redis_cache

MANAGED_FLAG = "managed_by_ifitwala"  # provenance flag on User.roles children
BASE_EMPLOYEE_ROLE = "Employee"


def _is_active_employee_status(status: str | None) -> bool:
    return str(status or "").strip().lower() == "active"


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


def _row_is_current(h) -> bool:
    """
    Derive current-ness from the row date window first.

    Employee.sync_employee_history() mutates rows during save, after validate() has already
    recomputed `is_current`. Access sync runs in that same save cycle, so the date window is
    the reliable source when the flag is momentarily stale.
    """
    try:
        today = getdate(nowdate())
        start = getdate(h.get("from_date")) if h.get("from_date") else None
        end = getdate(h.get("to_date")) if h.get("to_date") else None
    except Exception:
        return bool(h.get("is_current"))

    if start and start > today:
        return False
    if end and end < today:
        return False
    if start or end:
        return True
    return bool(h.get("is_current"))


def _active_history_rows(emp) -> list[dict]:
    rows = []
    history_rows = []
    if hasattr(emp, "get"):
        history_rows = emp.get("employee_history") or []
    else:
        history_rows = getattr(emp, "employee_history", None) or []
    for h in history_rows:
        if not h.get("designation"):
            continue
        if not _row_is_current(h):
            continue
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
        target_roles, workspace = _prejoin_access_from_designation(emp)
        return {BASE_EMPLOYEE_ROLE, *target_roles}, workspace
    target_roles = {BASE_EMPLOYEE_ROLE, *(set().union(*(c["roles"] for c in chunks)))}
    best = max(chunks, key=lambda c: int(c.get("priority") or 0))
    return target_roles, best.get("workspace")


def _remove_all_user_roles(user_doc) -> list[str]:
    removed_roles: list[str] = []
    for role_row in list(user_doc.roles or []):
        role_name = str(role_row.role or "").strip()
        if role_name:
            removed_roles.append(role_name)
        user_doc.remove(role_row)
    return sorted(set(removed_roles))


def _diff_user_roles(user_doc, target_roles: set[str]):
    current_all = {r.role for r in user_doc.roles}
    to_add = target_roles - current_all
    to_remove = [ch for ch in list(user_doc.roles) if ch.get(MANAGED_FLAG) and ch.role not in target_roles]
    return to_add, to_remove


def sync_user_access_from_employee(emp, *, notify_role_additions: bool = False):
    """
    Called from Employee.after_save.
    - Active employees keep baseline Employee + designation/history-managed roles.
    - Non-active employees lose all roles and are disabled.
    - Updates default workspace if effective workspace changed.
    - Optionally notifies the current operator about role additions/removals.
    """
    if not emp.user_id:
        return

    user = frappe.get_doc("User", emp.user_id)
    is_active_employee = _is_active_employee_status(getattr(emp, "employment_status", None))

    # Non-active employees must lose all roles and be disabled.
    if not is_active_employee:
        removed_roles = _remove_all_user_roles(user)
        changed = bool(removed_roles)
        if int(user.enabled or 0) != 0:
            user.enabled = 0
            changed = True
        if changed:
            user.save(ignore_permissions=True)
        if notify_role_additions:
            removed_label = (
                ", ".join(frappe.bold(role) for role in removed_roles) if removed_roles else _("no assigned roles")
            )
            frappe.msgprint(
                _("Removed all user roles from {0} because the employee is not active: {1}.").format(
                    frappe.bold(emp.user_id),
                    removed_label,
                ),
                title=_("Employee Access Updated"),
                indicator="orange",
            )
        return

    target_roles, target_ws = compute_effective_access_from_employee(emp)

    to_add, to_remove = _diff_user_roles(user, target_roles)
    added_roles = sorted(to_add)
    for role in to_add:
        user.append("roles", {"role": role, MANAGED_FLAG: 1})
    for ch in to_remove:
        user.remove(ch)

    changed = bool(to_add or to_remove)
    workspace_changed = False
    if target_ws and user.default_workspace != target_ws and user.user_type == "System User":
        user.default_workspace = target_ws
        changed = True
        workspace_changed = True

    desired_enabled = 1
    current_enabled = int(user.enabled or 0)
    if current_enabled != desired_enabled:
        user.enabled = desired_enabled
        changed = True

    if changed:
        user.save(ignore_permissions=True)
        if workspace_changed and target_ws:
            try:
                from ifitwala_ed.hr.workspace_utils import send_workspace_notification

                send_workspace_notification(user.name, target_ws)
            except Exception:
                pass

    if notify_role_additions and added_roles:
        frappe.msgprint(
            _("Added default role(s) to {0}: {1}.").format(
                frappe.bold(emp.user_id),
                ", ".join(frappe.bold(role) for role in added_roles),
            ),
            title=_("Employee Access Updated"),
            indicator="green",
        )


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
