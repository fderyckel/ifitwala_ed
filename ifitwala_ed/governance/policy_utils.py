# ifitwala_ed/governance/policy_utils.py

import frappe
from frappe import _

SYSTEM_MANAGER_ROLE = "System Manager"
ORG_ADMIN_ROLE = "Organization Admin"
SCHOOL_ADMIN_ROLE = "School Admin"
ACADEMIC_ADMIN_ROLE = "Academic Admin"
ACADEMIC_STAFF_ROLE = "Academic Staff"
GUARDIAN_ROLE = "Guardian"
STUDENT_ROLE = "Student"
ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"


def _user_roles(user: str | None = None) -> set[str]:
	user = user or frappe.session.user
	return set(frappe.get_roles(user))


def is_system_manager(user: str | None = None) -> bool:
	return SYSTEM_MANAGER_ROLE in _user_roles(user)


def ensure_policy_admin(user: str | None = None) -> None:
	roles = _user_roles(user)
	if SYSTEM_MANAGER_ROLE in roles or ORG_ADMIN_ROLE in roles:
		return
	frappe.throw(_("You do not have permission to manage policies."), frappe.PermissionError)


def is_policy_admin(user: str | None = None) -> bool:
	roles = _user_roles(user)
	return SYSTEM_MANAGER_ROLE in roles or ORG_ADMIN_ROLE in roles


def is_academic_admin(user: str | None = None) -> bool:
	return ACADEMIC_ADMIN_ROLE in _user_roles(user)


def has_guardian_role(user: str | None = None) -> bool:
	return GUARDIAN_ROLE in _user_roles(user)


def has_student_role(user: str | None = None) -> bool:
	return STUDENT_ROLE in _user_roles(user)


def has_admissions_applicant_role(user: str | None = None) -> bool:
	return ADMISSIONS_APPLICANT_ROLE in _user_roles(user)


def has_staff_role(user: str | None = None) -> bool:
	roles = _user_roles(user)
	return bool(
		roles
		& {
			ACADEMIC_STAFF_ROLE,
		}
	)
