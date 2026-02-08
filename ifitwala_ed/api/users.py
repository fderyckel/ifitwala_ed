# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/users.py

import frappe
from frappe.utils import getdate, nowdate

BLOCKED_EMPLOYMENT_STATUSES = frozenset(["Left", "Suspended"])
STAFF_PORTAL_EMPLOYMENT_STATUSES = frozenset(["Active", "Temporary Leave"])
POST_LOGIN_REDIRECT_CACHE_PREFIX = "ifitwala_ed:post_login_redirect_once"
POST_LOGIN_REDIRECT_TTL_SECONDS = 120


def _get_session_sid() -> str | None:
	"""Return current session id when available."""
	session = getattr(frappe, "session", None)
	sid = getattr(session, "sid", None)
	if sid:
		return str(sid)

	session_obj = getattr(frappe.local, "session_obj", None)
	sid = getattr(session_obj, "sid", None)
	if sid:
		return str(sid)

	return None


def _post_login_redirect_cache_key(sid: str) -> str:
	return f"{POST_LOGIN_REDIRECT_CACHE_PREFIX}:{sid}"


def _set_post_login_portal_redirect(path: str):
	"""Store one-time post-login target to override /app first-hop redirects."""
	sid = _get_session_sid()
	if not sid:
		return
	frappe.cache().set_value(
		_post_login_redirect_cache_key(sid),
		path,
		expires_in_sec=POST_LOGIN_REDIRECT_TTL_SECONDS,
	)


def _consume_post_login_portal_redirect() -> str | None:
	"""Consume and clear one-time post-login portal target for current session."""
	sid = _get_session_sid()
	if not sid:
		return None
	cache_key = _post_login_redirect_cache_key(sid)
	path = frappe.cache().get_value(cache_key)
	if not path:
		return None
	frappe.cache().delete_value(cache_key)
	return path.decode("utf-8") if isinstance(path, bytes) else str(path)


def _clear_post_login_portal_redirect():
	"""Clear one-time post-login target for current session."""
	sid = _get_session_sid()
	if not sid:
		return
	frappe.cache().delete_value(_post_login_redirect_cache_key(sid))


def _get_employee_access_state(user: str) -> dict:
	"""Resolve employee-linked access state from a single DB round-trip."""
	row = frappe.db.get_value(
		"Employee",
		{"user_id": user},
		["name", "employment_status", "relieving_date"],
		as_dict=True,
	)
	if not row:
		return {
			"has_employee_record": False,
			"is_blocked": False,
			"can_access_staff_portal": False,
			"employment_status": None,
			"relieving_date": None,
		}

	status = row.get("employment_status")
	relieving_date = row.get("relieving_date")
	today = getdate(nowdate())
	is_relieved = bool(relieving_date and getdate(relieving_date) <= today)
	is_blocked = bool(status in BLOCKED_EMPLOYMENT_STATUSES or is_relieved)
	can_access_staff_portal = bool(
		not is_blocked and status in STAFF_PORTAL_EMPLOYMENT_STATUSES
	)

	return {
		"has_employee_record": True,
		"is_blocked": is_blocked,
		"can_access_staff_portal": can_access_staff_portal,
		"employment_status": status,
		"relieving_date": relieving_date,
	}


def _resolve_login_redirect_path(user: str, roles: set[str]) -> str:
	"""
	Server-owned role routing after login.
	Priority is locked: Staff > Student > Guardian.
	"""
	if "Admissions Applicant" in roles:
		return "/admissions"
	if _get_employee_access_state(user).get("can_access_staff_portal"):
		return "/portal/staff"
	if "Student" in roles:
		return "/portal/student"
	if "Guardian" in roles:
		return "/portal/guardian"
	return "/portal"


def redirect_user_to_entry_portal(login_manager=None):
	"""
	Role-based login routing with explicit server-owned target resolution.
	For login APIs, return JSON-friendly fields only (no HTTP redirect response).
	Priority is locked: Staff > Student > Guardian.
	"""
	user = getattr(login_manager, "user", None) or frappe.session.user
	if not user or user == "Guest":
		return

	def _set_login_target(path: str, persist_home_page: bool = True):
		if persist_home_page:
			try:
				frappe.db.set_value("User", user, "home_page", path, update_modified=False)
			except Exception:
				# Login should remain functional even if home_page persistence fails.
				frappe.log_error(
					title="Login Home Page Update Failed",
					message=f"user={user}\npath={path}",
				)

		# Login endpoint returns JSON payload (home_page/message), not HTTP redirects.
		frappe.local.response["home_page"] = path
		frappe.local.response["redirect_to"] = path

	employee_state = _get_employee_access_state(user)
	if employee_state.get("is_blocked"):
		# Trigger canonical logout endpoint for blocked employees.
		_set_login_target("/?cmd=web_logout", persist_home_page=False)
		return

	roles = set(frappe.get_roles(user))
	path = _resolve_login_redirect_path(user, roles)
	_set_post_login_portal_redirect(path)
	_set_login_target(path, persist_home_page=True)


@frappe.whitelist()
def get_users_with_role(doctype, txt, searchfield, start, page_len, filters):
	"""Return enabled users matching the provided role for link-field queries."""
	role = filters.get("role") if filters else None
	if not role:
		return []

	query = """
		SELECT u.name, u.full_name
		FROM `tabUser` u
		JOIN `tabHas Role` r ON u.name = r.parent
		WHERE r.role = %(role)s
			AND u.enabled = 1
			AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.name
		LIMIT %(start)s, %(page_len)s
	"""

	return frappe.db.sql(
		query,
		{
			"role": role,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)
