from __future__ import annotations

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES

ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
ADMISSIONS_FAMILY_ROLE = "Admissions Family"
ALLOWED_STAFF_ROLES = ADMISSIONS_ROLES | {
    "Academic Admin",
    "Academic Staff",
    "Administrator",
    "Academic Assistant",
    "Employee",
    "System Manager",
}
SUPPORTED_CONTEXT_DOCTYPES = {"Student Applicant"}
MESSAGE_LIMIT = 300
THREAD_COMMUNICATION_TYPE = "Information"
THREAD_INTERACTION_MODE = "Structured Feedback"
THREAD_STATUS = "Draft"
THREAD_PORTAL_SURFACE = "Portal Feed"
INVALID_SESSION_USERS = {"guest", "none", "null", "undefined"}
READ_RECEIPT_REFERENCE_DOCTYPE = "Org Communication"
_LOCAL_ATTRS_RESET_BY_SET_USER = (
    "cache",
    "form_dict",
    "jenv",
    "role_permissions",
    "new_doc_templates",
    "user_perms",
)
_MISSING_LOCAL_ATTR = object()
