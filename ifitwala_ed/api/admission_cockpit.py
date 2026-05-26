# ifitwala_ed/api/admission_cockpit.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.admission.api.cockpit.access import (
    ALLOWED_COCKPIT_ROLES,
    INVALID_SESSION_USERS,
    _ensure_cockpit_access,
    _get_roles_for_user,
    _to_text,
)
from ifitwala_ed.admission.api.cockpit.actions import (
    _require_applicant_enrollment_plan_name,
    _require_cockpit_applicant_enrollment_plan_name,
    _require_cockpit_student_applicant_name,
    generate_admissions_cockpit_deposit_invoice_impl,
    get_or_create_admissions_cockpit_offer_plan_impl,
    hydrate_admissions_cockpit_request_impl,
    invalidate_admissions_cockpit_cache,
    promote_admissions_cockpit_applicant_impl,
    send_admissions_cockpit_offer_impl,
)
from ifitwala_ed.admission.api.cockpit.blockers import BLOCKER_LABELS, _build_blockers
from ifitwala_ed.admission.api.cockpit.cache import (
    COCKPIT_CACHE_PREFIX,
    COCKPIT_CACHE_TTL_SECONDS,
    _cache_key_for_payload,
)
from ifitwala_ed.admission.api.cockpit.data import (
    KANBAN_COLUMNS,
    TERMINAL_STATUSES,
    _as_str_list,
    _build_interview_state,
    _display_name,
    _empty_payload,
    _get_descendant_organizations,
    _interview_feedback_status_label,
    _interview_sort_key,
    _resolve_stage,
    _to_int,
    get_admissions_cockpit_data_impl,
)
from ifitwala_ed.admission.api.cockpit.enrollment_plan import (
    _build_applicant_enrollment_plan_state,
    _deposit_state_from_plan_row,
    _empty_deposit_state,
)
from ifitwala_ed.admission.api.cockpit.readiness import (
    _build_documents_state,
    _build_health_requirement_by_school,
    _build_health_state,
    _build_issues,
    _build_policy_state,
    _build_profile_state,
    _build_readiness_batch,
    _empty_readiness_snapshot,
    _value_present,
)
from ifitwala_ed.admission.api.cockpit.urls import (
    _applicant_workspace_target,
    _desk_route_slug,
    _doc_url,
    _new_doc_url,
    _target,
)

_COCKPIT_COMPAT_EXPORTS = (
    ADMISSIONS_ROLES,
    ALLOWED_COCKPIT_ROLES,
    INVALID_SESSION_USERS,
    COCKPIT_CACHE_PREFIX,
    COCKPIT_CACHE_TTL_SECONDS,
    TERMINAL_STATUSES,
    KANBAN_COLUMNS,
    BLOCKER_LABELS,
    _ensure_cockpit_access,
    _get_roles_for_user,
    _to_text,
    _to_int,
    _as_str_list,
    _value_present,
    _display_name,
    _get_descendant_organizations,
    _resolve_stage,
    _desk_route_slug,
    _doc_url,
    _new_doc_url,
    _target,
    _applicant_workspace_target,
    _empty_readiness_snapshot,
    _build_profile_state,
    _build_health_state,
    _interview_sort_key,
    _interview_feedback_status_label,
    _build_interview_state,
    _build_documents_state,
    _build_policy_state,
    _build_applicant_enrollment_plan_state,
    _empty_deposit_state,
    _deposit_state_from_plan_row,
    _build_health_requirement_by_school,
    _build_issues,
    _build_readiness_batch,
    _build_blockers,
    _empty_payload,
    _cache_key_for_payload,
    _require_applicant_enrollment_plan_name,
    _require_cockpit_student_applicant_name,
    _require_cockpit_applicant_enrollment_plan_name,
    invalidate_admissions_cockpit_cache,
)


@frappe.whitelist()
def get_or_create_admissions_cockpit_offer_plan(student_applicant: str):
    return get_or_create_admissions_cockpit_offer_plan_impl(student_applicant=student_applicant)


@frappe.whitelist()
def promote_admissions_cockpit_applicant(student_applicant: str):
    return promote_admissions_cockpit_applicant_impl(student_applicant=student_applicant)


@frappe.whitelist()
def send_admissions_cockpit_offer(applicant_enrollment_plan: str):
    return send_admissions_cockpit_offer_impl(applicant_enrollment_plan=applicant_enrollment_plan)


@frappe.whitelist()
def hydrate_admissions_cockpit_request(applicant_enrollment_plan: str):
    return hydrate_admissions_cockpit_request_impl(applicant_enrollment_plan=applicant_enrollment_plan)


@frappe.whitelist()
def generate_admissions_cockpit_deposit_invoice(applicant_enrollment_plan: str):
    return generate_admissions_cockpit_deposit_invoice_impl(applicant_enrollment_plan=applicant_enrollment_plan)


@frappe.whitelist()
def get_admissions_cockpit_data(filters=None):
    return get_admissions_cockpit_data_impl(filters=filters)
