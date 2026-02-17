# ifitwala_ed/governance/policy_utils.py

import frappe
from frappe import _

from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)

SYSTEM_MANAGER_ROLE = "System Manager"
ORG_ADMIN_ROLE = "Organization Admin"
SCHOOL_ADMIN_ROLE = "School Admin"
ACADEMIC_ADMIN_ROLE = "Academic Admin"
ACADEMIC_STAFF_ROLE = "Academic Staff"
GUARDIAN_ROLE = "Guardian"
STUDENT_ROLE = "Student"
ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
MEDIA_CONSENT_POLICY_KEY = "media_consent"
POLICY_CATEGORIES = (
    "Safeguarding",
    "Privacy & Data Protection",
    "Admissions",
    "Academic",
    "Conduct & Behaviour",
    "Health & Safety",
    "Operations",
    "Handbooks",
    "Employment",
)


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


def ensure_policy_applies_to_column(*, throw: bool = False, caller: str | None = None) -> dict:
    if frappe.db.has_column("Institutional Policy", "applies_to"):
        return {"ok": True}

    debug_payload = {
        "doctype": "Institutional Policy",
        "missing_column": "applies_to",
        "caller": caller,
        "site": getattr(frappe.local, "site", None),
    }
    frappe.log_error(message=frappe.as_json(debug_payload), title="Policy schema mismatch")

    message = _("Institutional Policy is missing the applies_to field. Run migrations or reload the DocType.")
    if throw:
        frappe.throw(message)
    return {"ok": False, "message": message}


def has_applicant_policy_acknowledgement(
    *,
    policy_key: str,
    student_applicant: str,
    organization: str | None = None,
    school: str | None = None,
) -> bool:
    if not policy_key or not student_applicant:
        return False

    if not organization or not school:
        row = frappe.db.get_value(
            "Student Applicant",
            student_applicant,
            ["organization", "school"],
            as_dict=True,
        )
        if not row:
            return False
        organization = organization or row.get("organization")
        school = school or row.get("school")

    if not organization:
        return False

    ancestor_orgs = get_organization_ancestors_including_self(organization)
    if not ancestor_orgs:
        return False

    schema_check = ensure_policy_applies_to_column(
        caller="has_applicant_policy_acknowledgement",
    )
    if not schema_check.get("ok"):
        return False

    org_placeholders = ", ".join(["%s"] * len(ancestor_orgs))
    rows = frappe.db.sql(
        f"""
		SELECT pv.name AS policy_version
		     , ip.policy_key AS policy_key
		     , ip.organization AS policy_organization
		  FROM `tabInstitutional Policy` ip
		  JOIN `tabPolicy Version` pv
		    ON pv.institutional_policy = ip.name
		 WHERE ip.is_active = 1
		   AND pv.is_active = 1
		   AND ip.organization IN ({org_placeholders})
		   AND (ip.school IS NULL OR ip.school = '' OR ip.school = %s)
		   AND ip.policy_key = %s
		   AND ip.applies_to LIKE %s
		""",
        (*ancestor_orgs, school, policy_key, "%Applicant%"),
        as_dict=True,
    )

    candidate_rows = select_nearest_policy_rows_by_key(
        rows=rows,
        context_organization=organization,
        policy_key_field="policy_key",
        policy_organization_field="policy_organization",
    )
    if not candidate_rows:
        return False

    versions = [row["policy_version"] for row in candidate_rows]
    return bool(
        frappe.db.exists(
            "Policy Acknowledgement",
            {
                "policy_version": ["in", versions],
                "acknowledged_for": "Applicant",
                "context_doctype": "Student Applicant",
                "context_name": student_applicant,
            },
        )
    )
