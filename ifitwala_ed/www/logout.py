# ifitwala_ed/www/logout.py

from urllib.parse import urlsplit

import frappe

DEFAULT_LOGOUT_REDIRECT = "/"


def _safe_redirect_target(raw_target: str | None) -> str:
    target = str(raw_target or "").strip() or DEFAULT_LOGOUT_REDIRECT
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return DEFAULT_LOGOUT_REDIRECT
    if not target.startswith("/"):
        return DEFAULT_LOGOUT_REDIRECT
    return target


def _redirect(to: str):
    frappe.local.flags.redirect_location = to
    raise frappe.Redirect


def _logout_current_session():
    login_manager = getattr(frappe.local, "login_manager", None)
    if not login_manager or not hasattr(login_manager, "logout"):
        frappe.log_error(
            title="LOGOUT LOGIN_MANAGER MISSING",
            message=frappe.as_json({"path": "/logout", "session_user": frappe.session.user}),
        )
        return
    login_manager.logout()


def get_context(context):
    context.no_cache = 1
    form = getattr(frappe, "form_dict", frappe._dict()) or frappe._dict()
    target = _safe_redirect_target(form.get("redirect-to") or form.get("redirect_to"))
    _logout_current_session()
    _redirect(target)
