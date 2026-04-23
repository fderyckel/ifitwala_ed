from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime

from ifitwala_ed.governance.doctype.family_consent_request.family_consent_request import (
    COMPLETION_CHANNEL_PAPER_ONLY,
    COMPLETION_CHANNEL_PORTAL_ONLY,
)
from ifitwala_ed.governance.policy_scope_utils import get_user_policy_scope
from ifitwala_ed.governance.policy_utils import (
    ACADEMIC_STAFF_ROLE,
    POLICY_ADMIN_ROLES,
    SCHOOL_ADMIN_ROLE,
    is_system_manager,
)
from ifitwala_ed.integrations.drive.authority import is_governed_file
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org

DECISION_BY_DOCTYPES = frozenset({"Guardian", "Student"})
DECISION_STATUSES = frozenset({"Approved", "Declined", "Granted", "Denied", "Withdrawn"})
SOURCE_CHANNELS = frozenset({"Guardian Portal", "Student Portal", "Desk Paper Capture"})
PROFILE_WRITEBACK_MODES = frozenset({"", "Form Only", "Update Profile"})
STAFF_SCOPE_ROLES = frozenset(set(POLICY_ADMIN_ROLES) | {SCHOOL_ADMIN_ROLE, ACADEMIC_STAFF_ROLE})


def _clean_data(value: str | None) -> str:
    return (value or "").strip()


def _escaped_in(values: list[str] | tuple[str, ...] | set[str]) -> str:
    cleaned = [_clean_data(value) for value in (values or [])]
    cleaned = [value for value in cleaned if value]
    if not cleaned:
        return ""
    return ", ".join(frappe.db.escape(value) for value in cleaned)


def _guardian_name_for_user(user: str) -> str:
    return _clean_data(frappe.db.get_value("Guardian", {"user": user}, "name"))


def _student_name_for_user(user: str) -> str:
    return _clean_data(frappe.db.get_value("Student", {"student_email": user}, "name"))


def _request_scope_row(family_consent_request: str) -> dict[str, str]:
    row = frappe.db.get_value(
        "Family Consent Request",
        family_consent_request,
        ["organization", "school"],
        as_dict=True,
    )
    return {
        "organization": _clean_data((row or {}).get("organization")),
        "school": _clean_data((row or {}).get("school")),
    }


def _request_scope_condition(*, organizations: list[str], schools: list[str] | None = None) -> str:
    organizations_sql = _escaped_in(organizations)
    if not organizations_sql:
        return ""

    schools_sql = _escaped_in(schools or [])
    school_condition = (
        f"(ifnull(fcr.school, '') = '' OR fcr.school in ({schools_sql}))"
        if schools_sql
        else "ifnull(fcr.school, '') = ''"
    )
    return (
        "exists ("
        "select 1 from `tabFamily Consent Request` fcr "
        "where fcr.name = `tabFamily Consent Decision`.`family_consent_request` "
        f"and fcr.organization in ({organizations_sql}) "
        f"and {school_condition}"
        ")"
    )


def _request_within_staff_scope(*, family_consent_request: str, user: str, roles: set[str]) -> bool:
    scope = _request_scope_row(family_consent_request)
    organization = scope.get("organization")
    school = scope.get("school")
    if not organization:
        return False

    if roles & POLICY_ADMIN_ROLES or SCHOOL_ADMIN_ROLE in roles:
        organization_scope, school_scope = get_user_policy_scope(user)
        if organization not in set(organization_scope or []):
            return False
        if school_scope:
            return not school or school in set(school_scope)
        return True

    if ACADEMIC_STAFF_ROLE in roles:
        base_org = _clean_data(get_user_base_org(user))
        if not base_org:
            return False
        organization_scope = {
            _clean_data(value) for value in (get_descendant_organizations(base_org) or [base_org]) if _clean_data(value)
        }
        return organization in organization_scope

    return False


class FamilyConsentDecision(Document):
    def before_insert(self):
        self._normalize()
        self._validate_enums()
        self._validate_snapshot()
        self._validate_source_file()
        self._validate_request_channel_compatibility()
        self.decision_at = get_datetime(self.decision_at) if self.decision_at else now_datetime()

    def before_save(self):
        if not self.is_new():
            frappe.throw(_("Family Consent Decisions are append-only and cannot be edited."))

    def before_delete(self):
        frappe.throw(_("Family Consent Decisions cannot be deleted."))

    def _normalize(self):
        self.family_consent_request = (self.family_consent_request or "").strip()
        self.student = (self.student or "").strip()
        self.decision_by_doctype = (self.decision_by_doctype or "").strip()
        self.decision_by = " ".join((self.decision_by or "").strip().split())
        self.decision_status = (self.decision_status or "").strip()
        self.typed_signature_name = " ".join((self.typed_signature_name or "").strip().split())
        self.attestation_confirmed = 1 if cint(self.attestation_confirmed) else 0
        self.source_channel = (self.source_channel or "").strip()
        self.source_file = (self.source_file or "").strip()
        self.response_snapshot = (self.response_snapshot or "").strip()
        self.profile_writeback_mode = (self.profile_writeback_mode or "").strip()
        self.supersedes_decision = (self.supersedes_decision or "").strip()

    def _validate_enums(self):
        if self.decision_by_doctype not in DECISION_BY_DOCTYPES:
            frappe.throw(_("Decision By DocType is invalid."))
        if self.decision_status not in DECISION_STATUSES:
            frappe.throw(_("Decision Status is invalid."))
        if self.source_channel not in SOURCE_CHANNELS:
            frappe.throw(_("Source Channel is invalid."))
        if self.profile_writeback_mode not in PROFILE_WRITEBACK_MODES:
            frappe.throw(_("Profile Writeback Mode is invalid."))

    def _validate_snapshot(self):
        if not self.response_snapshot:
            frappe.throw(_("Response Snapshot is required."))

        try:
            parsed = frappe.parse_json(self.response_snapshot)
        except Exception:
            parsed = None

        if not isinstance(parsed, dict):
            frappe.throw(_("Response Snapshot must be a JSON object."))

    def _validate_source_file(self):
        if not self.source_file:
            return
        if not frappe.db.exists("File", self.source_file):
            frappe.throw(_("Source File is invalid."))
        if not is_governed_file(self.source_file):
            frappe.throw(_("Source File must be a governed file managed by Ifitwala Drive."))
        if self.source_channel != "Desk Paper Capture":
            frappe.throw(_("Source File is allowed only for Desk paper-capture evidence."))

    def _validate_request_channel_compatibility(self):
        request_row = frappe.db.get_value(
            "Family Consent Request",
            self.family_consent_request,
            ["status", "completion_channel_mode"],
            as_dict=True,
        )
        if not request_row:
            frappe.throw(_("Family Consent Request is invalid."))

        request_status = (request_row.get("status") or "").strip()
        completion_channel_mode = (request_row.get("completion_channel_mode") or "").strip()
        if request_status == "Draft":
            frappe.throw(_("Family Consent Decisions cannot be recorded for draft requests."))

        if self.source_channel == "Guardian Portal" and self.decision_by_doctype != "Guardian":
            frappe.throw(_("Guardian Portal decisions must be recorded for Guardian signers."))
        if self.source_channel == "Student Portal" and self.decision_by_doctype != "Student":
            frappe.throw(_("Student Portal decisions must be recorded for Student signers."))
        if self.source_channel == "Desk Paper Capture" and self.profile_writeback_mode:
            frappe.throw(_("Desk paper capture cannot update profile data directly."))

        if completion_channel_mode == COMPLETION_CHANNEL_PAPER_ONLY and self.source_channel != "Desk Paper Capture":
            frappe.throw(_("This request accepts paper completion only."), frappe.ValidationError)
        if completion_channel_mode == COMPLETION_CHANNEL_PORTAL_ONLY and self.source_channel == "Desk Paper Capture":
            frappe.throw(_("This request accepts portal completion only."), frappe.ValidationError)


def get_permission_query_conditions(user: str | None = None) -> str | None:
    user = user or frappe.session.user
    if user == "Administrator" or is_system_manager(user):
        return None

    roles = set(frappe.get_roles(user))
    conditions: list[str] = []

    if roles & STAFF_SCOPE_ROLES:
        if roles & POLICY_ADMIN_ROLES or SCHOOL_ADMIN_ROLE in roles:
            organization_scope, school_scope = get_user_policy_scope(user)
            condition = _request_scope_condition(
                organizations=list(organization_scope or []),
                schools=list(school_scope or []),
            )
            if condition:
                conditions.append(condition)
        elif ACADEMIC_STAFF_ROLE in roles:
            base_org = _clean_data(get_user_base_org(user))
            if base_org:
                organizations = [
                    _clean_data(value)
                    for value in (get_descendant_organizations(base_org) or [base_org])
                    if _clean_data(value)
                ]
                condition = _request_scope_condition(organizations=organizations)
                if condition:
                    conditions.append(condition)

    guardian_name = _guardian_name_for_user(user)
    if guardian_name:
        conditions.append(
            "(`tabFamily Consent Decision`.`decision_by_doctype` = 'Guardian' "
            f"and `tabFamily Consent Decision`.`decision_by` = {frappe.db.escape(guardian_name)})"
        )

    student_name = _student_name_for_user(user)
    if student_name:
        conditions.append(
            "(`tabFamily Consent Decision`.`decision_by_doctype` = 'Student' "
            f"and `tabFamily Consent Decision`.`decision_by` = {frappe.db.escape(student_name)})"
        )

    if not conditions:
        return "1=0"
    return "(" + " OR ".join(conditions) + ")"


def has_permission(
    doc: "FamilyConsentDecision" | str | None, user: str | None = None, ptype: str | None = None
) -> bool:
    user = user or frappe.session.user
    if user == "Administrator" or is_system_manager(user):
        return True

    if ptype and ptype != "read":
        return False

    roles = set(frappe.get_roles(user))
    if doc is None:
        return bool(roles & STAFF_SCOPE_ROLES or _guardian_name_for_user(user) or _student_name_for_user(user))

    if isinstance(doc, str):
        row = frappe.db.get_value(
            "Family Consent Decision",
            doc,
            ["family_consent_request", "decision_by_doctype", "decision_by"],
            as_dict=True,
        )
        if not row:
            return False
        family_consent_request = _clean_data(row.get("family_consent_request"))
        decision_by_doctype = _clean_data(row.get("decision_by_doctype"))
        decision_by = _clean_data(row.get("decision_by"))
    else:
        family_consent_request = _clean_data(getattr(doc, "family_consent_request", None))
        decision_by_doctype = _clean_data(getattr(doc, "decision_by_doctype", None))
        decision_by = _clean_data(getattr(doc, "decision_by", None))

    if family_consent_request and roles & STAFF_SCOPE_ROLES:
        if _request_within_staff_scope(family_consent_request=family_consent_request, user=user, roles=roles):
            return True

    guardian_name = _guardian_name_for_user(user)
    if guardian_name and decision_by_doctype == "Guardian" and decision_by == guardian_name:
        return True

    student_name = _student_name_for_user(user)
    if student_name and decision_by_doctype == "Student" and decision_by == student_name:
        return True

    return False
