# ifitwala_ed/routing/policy.py

from __future__ import annotations

from urllib.parse import quote

import frappe

ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
CANONICAL_PORTAL_PREFIX = "/portal"
LEGACY_TOP_LEVEL_SECTION_PATHS = {
    "staff": "/staff",
    "student": "/student",
    "guardian": "/guardian",
}

PORTAL_SECTION_PRIORITY = ("staff", "student", "guardian")
PORTAL_SECTION_LABELS = {
    "staff": "Staff",
    "student": "Student",
    "guardian": "Guardian",
}
PORTAL_SECTION_PATHS = {
    "staff": f"{CANONICAL_PORTAL_PREFIX}/staff",
    "student": f"{CANONICAL_PORTAL_PREFIX}/student",
    "guardian": f"{CANONICAL_PORTAL_PREFIX}/guardian",
}

STAFF_PORTAL_ROLES = frozenset(
    {
        "Academic User",
        "System Manager",
        "Teacher",
        "Administrator",
        "Finance User",
        "HR User",
        "HR Manager",
    }
)

LEGACY_PORTAL_ROOT_REDIRECT = f"{CANONICAL_PORTAL_PREFIX}/student"
RESERVED_WEBSITE_PREFIXES = frozenset(
    {
        "admissions",
        "apply",
        "schools",
        "student",
        "staff",
        "guardian",
        "portal",
        "app",
        "api",
        "files",
        "login",
        "logout",
    }
)

WEBSITE_ROUTE_RULES = [
    {"from_route": "/", "to_route": "index"},
    {"from_route": "/admissions", "to_route": "admissions"},
    {"from_route": "/admissions/<path:subpath>", "to_route": "admissions"},
    # Legacy top-level compatibility ingress. Controller redirects to canonical /portal/* routes.
    {"from_route": "/student", "to_route": "portal"},
    {"from_route": "/student/<path:subpath>", "to_route": "portal"},
    {"from_route": "/staff", "to_route": "portal"},
    {"from_route": "/staff/<path:subpath>", "to_route": "portal"},
    {"from_route": "/guardian", "to_route": "portal"},
    {"from_route": "/guardian/<path:subpath>", "to_route": "portal"},
    # Canonical portal namespace ingress.
    {"from_route": "/portal", "to_route": "portal"},
    {"from_route": "/portal/<path:subpath>", "to_route": "portal"},
    {"from_route": "/portfolio/share/<path:token>", "to_route": "portfolio/share"},
    {"from_route": "/schools", "to_route": "index"},
    {"from_route": "/schools/<path:route>", "to_route": "website"},
    {"from_route": "/home", "to_route": "index"},
    {"from_route": "/index.html", "to_route": "index"},
]

WEBSITE_REDIRECTS = [
    {"source": "/inquiry", "target": "/apply/inquiry", "redirect_http_status": 301},
    {
        "source": "/registration-of-interest",
        "target": "/apply/registration-of-interest",
        "redirect_http_status": 301,
    },
    {"source": "/student", "target": "/portal/student", "redirect_http_status": 301},
    {"source": "/staff", "target": "/portal/staff", "redirect_http_status": 301},
    {"source": "/guardian", "target": "/portal/guardian", "redirect_http_status": 301},
]


def canonical_path_for_section(section: str) -> str:
    return PORTAL_SECTION_PATHS.get(section, LEGACY_PORTAL_ROOT_REDIRECT)


def normalize_path(path: str | None, *, default: str = "/") -> str:
    text = (path or "").strip() or default
    if not text.startswith("/"):
        text = f"/{text}"
    if len(text) > 1 and text.endswith("/"):
        text = text[:-1]
    return text


def _split_path(path: str | None) -> list[str]:
    normalized = normalize_path(path)
    return [segment for segment in normalized.split("/") if segment]


def resolve_section_from_path(path: str | None) -> str | None:
    segments = _split_path(path)
    if not segments:
        return None

    first = segments[0]
    if first in LEGACY_TOP_LEVEL_SECTION_PATHS:
        return first

    if first != "portal":
        return None

    if len(segments) < 2:
        return None

    second = segments[1]
    if second in PORTAL_SECTION_PATHS:
        return second
    return None


def translate_legacy_portal_path(path: str | None, *, default_section: str) -> str | None:
    # Keep signature stable for existing callers/tests.
    _ = default_section
    normalized = normalize_path(path)
    if normalized.startswith(CANONICAL_PORTAL_PREFIX):
        return None

    segments = _split_path(normalized)
    if not segments:
        return None

    section = segments[0]
    if section not in LEGACY_TOP_LEVEL_SECTION_PATHS:
        return None

    base = canonical_path_for_section(section)
    remaining = "/".join(segments[1:])
    return f"{base}/{remaining}" if remaining else base


def _active_employee_status_from_login_email(*, user: str) -> tuple[bool, str]:
    login_email = (frappe.db.get_value("User", user, "email") or user or "").strip()
    if not login_email:
        return False, ""

    matches = frappe.get_all(
        "Employee",
        filters={
            "employment_status": "Active",
            "employee_professional_email": login_email,
        },
        fields=["name", "user_id"],
        limit_page_length=2,
    )
    if len(matches) != 1:
        return False, ""

    current_user_id = str(matches[0].get("user_id") or "").strip()
    if current_user_id and current_user_id != user:
        return False, ""

    return True, "active"


def _linked_employee_status(*, user: str) -> tuple[bool, str]:
    if frappe.db.exists("Employee", {"user_id": user, "employment_status": "Active"}):
        return True, "active"

    row = frappe.db.get_value("Employee", {"user_id": user}, ["name", "employment_status"], as_dict=True)
    if row:
        status = str(row.get("employment_status") or "").strip().lower()
        if status == "active":
            return True, "active"

        has_unlinked_active, unlinked_active_status = _active_employee_status_from_login_email(user=user)
        if has_unlinked_active:
            return True, unlinked_active_status
        return True, status

    has_unlinked_active, unlinked_active_status = _active_employee_status_from_login_email(user=user)
    if has_unlinked_active:
        return True, unlinked_active_status
    return False, ""


def has_active_employee_profile(*, user: str, roles: set[str]) -> bool:
    _ = roles
    has_employee, status = _linked_employee_status(user=user)
    if not has_employee:
        return False
    return status == "active"


def has_staff_portal_access(*, user: str, roles: set[str]) -> bool:
    has_employee, status = _linked_employee_status(user=user)
    if has_employee:
        return status == "active"
    return bool(roles & STAFF_PORTAL_ROLES)


def resolve_portal_sections(*, user: str, roles: set[str]) -> set[str]:
    sections: set[str] = set()
    if has_staff_portal_access(user=user, roles=roles):
        sections.add("staff")
    if "Student" in roles:
        sections.add("student")
    if "Guardian" in roles:
        sections.add("guardian")
    return sections


def resolve_default_portal_section(*, allowed_sections: set[str], requested_section: str | None = None) -> str:
    if requested_section and requested_section in allowed_sections:
        return requested_section
    for section in PORTAL_SECTION_PRIORITY:
        if section in allowed_sections:
            return section
    return "student"


def resolve_login_redirect_path(*, user: str, roles: set[str]) -> str:
    if ADMISSIONS_APPLICANT_ROLE in roles:
        return "/admissions"

    sections = resolve_portal_sections(user=user, roles=roles)
    default_section = resolve_default_portal_section(allowed_sections=sections)
    return canonical_path_for_section(default_section)


def portal_roles_for_client(sections: set[str]) -> list[str]:
    ordered = [section for section in PORTAL_SECTION_PRIORITY if section in sections]
    return [PORTAL_SECTION_LABELS[section] for section in ordered]


def is_portal_home_page(path: str | None) -> bool:
    normalized = normalize_path(path, default="")
    if normalized.startswith(f"{CANONICAL_PORTAL_PREFIX}/"):
        return True
    return normalized in PORTAL_SECTION_PATHS.values() or normalized in LEGACY_TOP_LEVEL_SECTION_PATHS.values()


def build_login_redirect(path: str) -> str:
    return f"/login?redirect-to={path}"


def build_logout_then_login_redirect(path: str) -> str:
    login_path = build_login_redirect(path)
    return f"/logout?redirect-to={quote(login_path, safe='')}"


def log_legacy_portal_hit(*, path: str | None, user: str | None):
    normalized = normalize_path(path)
    if normalized.startswith(CANONICAL_PORTAL_PREFIX):
        return

    segments = _split_path(normalized)
    if not segments or segments[0] not in LEGACY_TOP_LEVEL_SECTION_PATHS:
        return

    frappe.logger("ifitwala_ed.routing").info(
        "legacy_portal_path_hit path=%s user=%s",
        normalized,
        user or "Guest",
    )
